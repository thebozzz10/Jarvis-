"""Claude AI streaming tool-use loop."""
import asyncio
import base64
import json
from typing import AsyncGenerator, Callable
import anthropic
from jarvis.core.tool_registry import ToolRegistry
from jarvis.core.context_manager import build_system_prompt
from jarvis.core.event_bus import bus, TOOL_CALLED, TOOL_RESULT
from jarvis.memory.memory_store import add_message
from jarvis.utils.config import ANTHROPIC_API_KEY, MODEL, get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

MAX_TOKENS = int(get("jarvis", "max_tokens", 4096))
MAX_TOOL_ROUNDS = 10


class JarvisAgent:
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
    ) -> str:
        """Stream a response, executing tools as needed. Returns full text."""
        system = build_system_prompt(interaction_mode)

        # Build user message
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

        full_response = await self._run_loop(system, on_chunk)

        add_message(self._session_id, "assistant", full_response)
        return full_response

    async def _run_loop(self, system: str, on_chunk: Callable[[str], None] | None) -> str:
        """Run the tool-use loop until no more tool calls are requested."""
        full_text = ""
        for _ in range(MAX_TOOL_ROUNDS):
            text, tool_calls = await self._stream_once(system, on_chunk)
            full_text += text

            if not tool_calls:
                break

            # Execute all tool calls and append results
            tool_results = []
            for tc in tool_calls:
                bus.publish(TOOL_CALLED, {"name": tc["name"], "input": tc["input"]})
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._registry.dispatch, tc["name"], tc["input"]
                )
                bus.publish(TOOL_RESULT, {"name": tc["name"], "result": result[:200]})
                add_message(self._session_id, "tool", result,
                            tool_name=tc["name"], tool_input=tc["input"], tool_result=result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": result,
                })

            # Add assistant turn (with tool_use blocks) and tool results to history
            self._history.append({
                "role": "assistant",
                "content": [{"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                             for tc in tool_calls] + ([{"type": "text", "text": text}] if text else []),
            })
            self._history.append({"role": "user", "content": tool_results})

        return full_text

    async def _stream_once(
        self, system: str, on_chunk: Callable[[str], None] | None
    ) -> tuple[str, list[dict]]:
        """Make one streaming API call. Returns (text, tool_calls)."""
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        current_tool: dict | None = None
        current_json_parts: list[str] = []

        try:
            async with self._client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=self._history,
                tools=self._registry.get_schemas(),
            ) as stream:
                async for event in stream:
                    etype = event.type

                    if etype == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": {},
                            }
                            current_json_parts = []

                    elif etype == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            chunk = delta.text
                            text_parts.append(chunk)
                            if on_chunk:
                                on_chunk(chunk)
                        elif delta.type == "input_json_delta":
                            current_json_parts.append(delta.partial_json)

                    elif etype == "content_block_stop":
                        if current_tool is not None:
                            raw_json = "".join(current_json_parts)
                            try:
                                current_tool["input"] = json.loads(raw_json) if raw_json else {}
                            except json.JSONDecodeError:
                                current_tool["input"] = {}
                            tool_calls.append(current_tool)
                            current_tool = None
                            current_json_parts = []

        except anthropic.APIStatusError as e:
            log.error("Anthropic API error: %s", e)
            err = f"\n[JARVIS system error: {e.status_code}]"
            text_parts.append(err)
            if on_chunk:
                on_chunk(err)

        return "".join(text_parts), tool_calls

    def clear_history(self):
        self._history.clear()
