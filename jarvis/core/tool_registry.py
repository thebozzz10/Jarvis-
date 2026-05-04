"""Registers and dispatches all Jarvis tools."""
import json
from typing import Any
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class BaseTool:
    name: str = ""
    description: str = ""
    input_schema: dict = {}

    def run(self, **kwargs) -> str:
        raise NotImplementedError

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        log.debug("Registered tool: %s", tool.name)

    def get_schemas(self) -> list[dict]:
        return [t.to_claude_schema() for t in self._tools.values()]

    def dispatch(self, name: str, inputs: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            log.info("Tool call: %s(%s)", name, str(inputs)[:120])
            result = tool.run(**inputs)
            if not isinstance(result, str):
                result = json.dumps(result)
            return result
        except Exception as e:
            log.error("Tool %s failed: %s", name, e, exc_info=True)
            return json.dumps({"error": str(e)})


def build_registry() -> ToolRegistry:
    """Import and register all tool implementations."""
    from jarvis.tools.screen_tools import TakeScreenshot, ReadScreenText, FindOnScreen
    from jarvis.tools.input_tools import MouseClick, TypeText, KeyPress, MouseDrag, Scroll
    from jarvis.tools.app_tools import LaunchApp, ListWindows, FocusWindow
    from jarvis.tools.file_tools import ReadFile, WriteFile, ListDirectory, FindFiles
    from jarvis.tools.web_tools import WebSearch, FetchWebpage
    from jarvis.tools.system_tools import GetSystemInfo, RunShellCommand, SendNotification, SetVolume
    from jarvis.tools.memory_tools import Remember, Recall, GetTimeAndDate, ClipboardControl

    registry = ToolRegistry()
    for tool_cls in [
        TakeScreenshot, ReadScreenText, FindOnScreen,
        MouseClick, TypeText, KeyPress, MouseDrag, Scroll,
        LaunchApp, ListWindows, FocusWindow,
        ReadFile, WriteFile, ListDirectory, FindFiles,
        WebSearch, FetchWebpage,
        GetSystemInfo, RunShellCommand, SendNotification, SetVolume,
        Remember, Recall, GetTimeAndDate, ClipboardControl,
    ]:
        registry.register(tool_cls())
    return registry
