"""Mouse and keyboard automation tools."""
import json
import time
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class MouseClick(BaseTool):
    name = "mouse_click"
    description = "Click the mouse at specified coordinates or move to a named element and click it."
    input_schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            "clicks": {"type": "integer", "description": "Number of clicks (2=double-click)", "default": 1},
        },
        "required": [],
    }

    def run(self, x: int | None = None, y: int | None = None,
            button: str = "left", clicks: int = 1) -> str:
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks, interval=0.1)
            else:
                pyautogui.click(button=button, clicks=clicks, interval=0.1)
            return json.dumps({"success": True, "action": f"{button} click x{clicks} at ({x},{y})"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class TypeText(BaseTool):
    name = "type_text"
    description = "Type text at the current cursor position, simulating keyboard input."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type"},
            "interval": {"type": "number", "description": "Seconds between keystrokes", "default": 0.02},
            "clear_first": {"type": "boolean", "description": "Select-all then delete before typing", "default": False},
        },
        "required": ["text"],
    }

    def run(self, text: str, interval: float = 0.02, clear_first: bool = False) -> str:
        try:
            import pyautogui
            if clear_first:
                pyautogui.hotkey("command", "a")
                time.sleep(0.1)
                pyautogui.press("delete")
            pyautogui.write(text, interval=interval)
            return json.dumps({"success": True, "typed": len(text), "chars": text[:50]})
        except Exception as e:
            return json.dumps({"error": str(e)})


class KeyPress(BaseTool):
    name = "key_press"
    description = "Press one or more keyboard keys, including modifier combinations like Cmd+C."
    input_schema = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key names e.g. ['cmd','c'] for copy, ['enter'], ['escape'], ['cmd','space']",
            },
        },
        "required": ["keys"],
    }

    def run(self, keys: list[str]) -> str:
        try:
            import pyautogui
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            return json.dumps({"success": True, "keys": keys})
        except Exception as e:
            return json.dumps({"error": str(e)})


class MouseDrag(BaseTool):
    name = "mouse_drag"
    description = "Click and drag from one screen position to another."
    input_schema = {
        "type": "object",
        "properties": {
            "from_x": {"type": "integer"},
            "from_y": {"type": "integer"},
            "to_x": {"type": "integer"},
            "to_y": {"type": "integer"},
            "duration": {"type": "number", "description": "Drag duration in seconds", "default": 0.5},
        },
        "required": ["from_x", "from_y", "to_x", "to_y"],
    }

    def run(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5) -> str:
        try:
            import pyautogui
            pyautogui.moveTo(from_x, from_y)
            pyautogui.dragTo(to_x, to_y, duration=duration, button="left")
            return json.dumps({"success": True, "from": [from_x, from_y], "to": [to_x, to_y]})
        except Exception as e:
            return json.dumps({"error": str(e)})


class Scroll(BaseTool):
    name = "scroll"
    description = "Scroll the mouse wheel at the current position or specified coordinates."
    input_schema = {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
            "amount": {"type": "integer", "description": "Number of scroll clicks", "default": 3},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
        },
        "required": ["direction"],
    }

    def run(self, direction: str, amount: int = 3, x: int | None = None, y: int | None = None) -> str:
        try:
            import pyautogui
            if x and y:
                pyautogui.moveTo(x, y)
            clicks = amount if direction == "up" else -amount
            if direction in ("left", "right"):
                pyautogui.hscroll(amount if direction == "right" else -amount)
            else:
                pyautogui.scroll(clicks)
            return json.dumps({"success": True, "direction": direction, "amount": amount})
        except Exception as e:
            return json.dumps({"error": str(e)})
