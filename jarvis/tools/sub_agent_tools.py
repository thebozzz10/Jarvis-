"""Sub-agent delegation: spawn fresh JarvisAgent instances for complex sub-tasks."""
import asyncio
import json
import threading
from jarvis.core.tool_registry import BaseTool
from jarvis.memory.memory_store import create_session
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class DelegateTask(BaseTool):
    name = "delegate_task"
    description = (
        "Delegate a complex sub-task to a fresh sub-agent that runs independently. "
        "The sub-agent has access to all the same tools and returns a final answer. "
        "Use this for compound tasks that benefit from focused context, or to run "
        "multiple tasks in parallel."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Detailed task description for the sub-agent"},
            "expected_output": {"type": "string", "description": "What the sub-agent should return"},
        },
        "required": ["task"],
    }

    def run(self, task: str, expected_output: str = "") -> str:
        try:
            from jarvis.core.agent import JarvisAgent
            from jarvis.core.tool_registry import build_registry

            registry = build_registry()
            sid = create_session()
            agent = JarvisAgent(registry, sid)

            prompt = task
            if expected_output:
                prompt += f"\n\nExpected output: {expected_output}"

            log.info("Sub-agent dispatched: %.80s", task)
            result_box: dict = {}

            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(agent.process(prompt, interaction_mode="text"))
                    result_box["result"] = result
                except Exception as e:
                    result_box["error"] = str(e)
                finally:
                    loop.close()

            t = threading.Thread(target=run_in_thread, daemon=True)
            t.start()
            t.join(timeout=120)

            if "error" in result_box:
                return json.dumps({"error": result_box["error"]})
            if "result" in result_box:
                return json.dumps({"sub_agent_response": result_box["result"][:8000],
                                   "session": sid})
            return json.dumps({"error": "Sub-agent timed out"})
        except Exception as e:
            return json.dumps({"error": str(e)})
