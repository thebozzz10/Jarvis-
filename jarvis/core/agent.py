"""Claude streaming tool-use loop with extended thinking, prompt caching, and computer use."""
import asyncio
import base64
import json
from typing import Callable
import anthropic
from jarvis.core.tool_registry import ToolRegistry
from jarvis.core.context_manager import build_system_prompt
from jarvis.core.event_bus import bus, TOOL_CALLED, TOOL_RESULT
from jarvis.memory.memory_store import add_message
from jarvis.utils.config import ANTHROPIC_API_KEY, MODEL, get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

MAX_TOKENS = int(get("jarvis", "max_tokens", 8192))
MAX_TOOL_ROUNDS = 25
THINKING_BUDGET = int(get("jarvis", "thinking_budget", 5000))
ENABLE_THINKING = bool(get("jarvis", "extended_thinking", True))
ENABLE_CACHING = bool(get("jarvis", "prompt_caching", True))
ENABLE_COMPUTER_USE = bool(get("jarvis", "computer_use", True))


class JarvisAgent:
    """The brain. Streams Claude responses while orchestrating tool use."""

    def __init__(self, registry: ToolRegistry, session_id: str):
        self._registry = registry
        self._session_id = session_id
        self._client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        self._history: list[dict] = []

    async def process(
        self,
        user_input: str,
        image_bytes: bytes | None = None,
        interaction_mode: str = "text",
        on_chunk: Callable[[str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
    ) -> str:
        system = self._build_cached_system(interaction_mode)

        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode()
            user_content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": user_input},
            ]
        else:
            user_content = user_input

        self._history.append({"role": "user", "content": user_content})
        add_message(self._session_id, "user", user_input)

        full_response = await self._run_loop(system, on_chunk, on_thinking)
        add_message(self._session_id, "assistant", full_response)
        return full_response

    def _build_cached_system(self, interaction_mode: str) -> list[dict]:
        """System prompt with cache_control on the static part."""
        prompt_text = build_system_prompt(interaction_mode)
        if ENABLE_CACHING:
            return [{
                "type": "text",
                "text": prompt_text,
                "cache_control": {"type": "ephemeral"},
            }]
        return prompt_text  # type: ignore

    async def _run_loop(self, system, on_chunk, on_thinking) -> str:
        full_text = ""
        for round_idx in range(MAX_TOOL_ROUNDS):
            text, thinking, tool_calls = await self._stream_once(system, on_chunk, on_thinking)
            full_text += text

            if not tool_calls:
                break

            # Execute tools (run blocking work off-loop)
            tool_results = []
            assistant_blocks: list[dict] = []
            if thinking:
                assistant_blocks.append({"type": "thinking", "thinking": thinking})
            for tc in tool_calls:
                bus.publish(TOOL_CALLED, {"name": tc["name"], "input": tc["input"]})
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._dispatch_tool, tc["name"], tc["input"]
                )
                bus.publish(TOOL_RESULT, {"name": tc["name"], "result": str(result)[:200]})
                add_message(self._session_id, "tool", str(result),
                            tool_name=tc["name"], tool_input=tc["input"], tool_result=str(result))
                tool_results.append(self._make_tool_result(tc, result))
                assistant_blocks.append({"type": "tool_use", "id": tc["id"],
                                          "name": tc["name"], "input": tc["input"]})
            if text:
                assistant_blocks.append({"type": "text", "text": text})

            self._history.append({"role": "assistant", "content": assistant_blocks})
            self._history.append({"role": "user", "content": tool_results})

        return full_text

    def _dispatch_tool(self, name: str, inputs: dict):
        """Special-case computer-use 'computer' tool — handled inline; otherwise dispatch."""
        if name == "computer":
            return self._handle_computer_use(inputs)
        return self._registry.dispatch(name, inputs)

    def _handle_computer_use(self, inputs: dict) -> dict:
        """Translate Anthropic computer-use action → pyautogui + return screenshot."""
        from jarvis.tools.computer_use_handler import execute_computer_action
        return execute_computer_action(inputs)

    @staticmethod
    def _make_tool_result(tc: dict, result):
        """Format tool result. If image-bearing dict, attach image."""
        content_blocks = []
        if isinstance(result, dict) and "image_base64" in result:
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png",
                           "data": result["image_base64"]},
            })
            text_part = {k: v for k, v in result.items() if k != "image_base64"}
            content_blocks.append({"type": "text", "text": json.dumps(text_part)})
            return {"type": "tool_result", "tool_use_id": tc["id"], "content": content_blocks}
        return {"type": "tool_result", "tool_use_id": tc["id"],
                "content": result if isinstance(result, str) else json.dumps(result)}

    async def _stream_once(self, system, on_chunk, on_thinking) -> tuple[str, str, list[dict]]:
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[dict] = []
        current_tool: dict | None = None
        current_json_parts: list[str] = []

        kwargs: dict = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": self._history,
            "tools": self._build_tools_list(),
        }

        if ENABLE_THINKING:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": THINKING_BUDGET}
            kwargs["temperature"] = 1.0  # required when thinking is enabled

        if ENABLE_COMPUTER_USE:
            kwargs["betas"] = ["computer-use-2025-01-24"]

        try:
            stream_method = (self._client.beta.messages.stream
                             if ENABLE_COMPUTER_USE else self._client.messages.stream)
            async with stream_method(**kwargs) as stream:
                async for event in stream:
                    etype = event.type

                    if etype == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            current_tool = {"id": block.id, "name": block.name, "input": {}}
                            current_json_parts = []

                    elif etype == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            chunk = delta.text
                            text_parts.append(chunk)
                            if on_chunk:
                                on_chunk(chunk)
                        elif delta.type == "thinking_delta":
                            thinking_parts.append(delta.thinking)
                            if on_thinking:
                                on_thinking(delta.thinking)
                        elif delta.type == "input_json_delta":
                            current_json_parts.append(delta.partial_json)

                    elif etype == "content_block_stop":
                        if current_tool is not None:
                            raw = "".join(current_json_parts)
                            try:
                                current_tool["input"] = json.loads(raw) if raw else {}
                            except json.JSONDecodeError:
                                current_tool["input"] = {}
                            tool_calls.append(current_tool)
                            current_tool = None
                            current_json_parts = []

        except anthropic.APIStatusError as e:
            log.error("Anthropic API error: %s", e)
            err = f"\n[JARVIS API error: {e.status_code} — {str(e)[:200]}]"
            text_parts.append(err)
            if on_chunk:
                on_chunk(err)
        except Exception as e:
            log.error("Stream error: %s", e, exc_info=True)
            err = f"\n[JARVIS error: {e}]"
            text_parts.append(err)
            if on_chunk:
                on_chunk(err)

        return "".join(text_parts), "".join(thinking_parts), tool_calls

    def _build_tools_list(self) -> list[dict]:
        tools = list(self._registry.get_schemas())
        if ENABLE_COMPUTER_USE:
            try:
                import pyautogui
                w, h = pyautogui.size()
            except Exception:
                w, h = 1920, 1080
            tools.append({
                "type": "computer_20250124",
                "name": "computer",
                "display_width_px": w,
                "display_height_px": h,
                "display_number": 1,
            })
        return tools

    def clear_history(self):
        self._history.clear()
