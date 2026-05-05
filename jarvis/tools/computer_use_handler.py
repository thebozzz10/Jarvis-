"""Handler for Anthropic Computer Use action API.

The Claude `computer_20250124` tool sends actions like:
  - {"action": "screenshot"}
  - {"action": "left_click", "coordinate": [x, y]}
  - {"action": "type", "text": "..."}
  - {"action": "key", "text": "cmd+c"}
  - {"action": "mouse_move", "coordinate": [x, y]}
  - {"action": "scroll", "coordinate": [x, y], "scroll_direction": "down", "scroll_amount": 3}
  - {"action": "wait", "duration": 1}
  - {"action": "left_click_drag", "start_coordinate": [x,y], "coordinate": [x,y]}

This module translates them into pyautogui calls and returns a screenshot.
"""
import base64
import io
import time
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

# pynput → pyautogui key name translation
_KEY_MAP = {
    "Return": "enter", "BackSpace": "backspace", "Tab": "tab",
    "Escape": "escape", "Page_Up": "pageup", "Page_Down": "pagedown",
    "Home": "home", "End": "end", "Up": "up", "Down": "down",
    "Left": "left", "Right": "right", "space": "space",
    "ctrl": "ctrl", "alt": "option", "shift": "shift", "cmd": "command", "super": "command",
}


def _pyautogui_key(name: str) -> str:
    return _KEY_MAP.get(name, name.lower())


def _capture_screenshot() -> dict:
    try:
        import pyautogui
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return {"image_base64": base64.standard_b64encode(buf.getvalue()).decode(),
                "size": f"{img.width}x{img.height}"}
    except Exception as e:
        return {"error": f"screenshot failed: {e}"}


def execute_computer_action(action: dict) -> dict:
    """Execute the computer-use action and return a result dict."""
    try:
        import pyautogui
    except ImportError:
        return {"error": "pyautogui not installed"}

    a = action.get("action", "")
    log.info("Computer action: %s", a)

    try:
        if a == "screenshot":
            return _capture_screenshot()

        if a == "mouse_move":
            x, y = action["coordinate"]
            pyautogui.moveTo(x, y, duration=0.2)

        elif a in ("left_click", "right_click", "middle_click"):
            btn = a.replace("_click", "")
            coord = action.get("coordinate")
            if coord:
                pyautogui.click(coord[0], coord[1], button=btn)
            else:
                pyautogui.click(button=btn)

        elif a == "double_click":
            coord = action.get("coordinate")
            if coord:
                pyautogui.doubleClick(coord[0], coord[1])
            else:
                pyautogui.doubleClick()

        elif a == "triple_click":
            coord = action.get("coordinate")
            if coord:
                pyautogui.tripleClick(coord[0], coord[1])

        elif a == "left_click_drag":
            sx, sy = action["start_coordinate"]
            ex, ey = action["coordinate"]
            pyautogui.moveTo(sx, sy)
            pyautogui.dragTo(ex, ey, duration=0.4, button="left")

        elif a == "type":
            pyautogui.write(action["text"], interval=0.02)

        elif a == "key":
            keys = [_pyautogui_key(k.strip()) for k in action["text"].split("+")]
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)

        elif a == "scroll":
            coord = action.get("coordinate")
            if coord:
                pyautogui.moveTo(coord[0], coord[1])
            direction = action.get("scroll_direction", "down")
            amount = int(action.get("scroll_amount", 3))
            if direction == "up":
                pyautogui.scroll(amount)
            elif direction == "down":
                pyautogui.scroll(-amount)
            elif direction == "right":
                pyautogui.hscroll(amount)
            elif direction == "left":
                pyautogui.hscroll(-amount)

        elif a == "wait":
            time.sleep(min(float(action.get("duration", 1)), 5))

        elif a == "cursor_position":
            x, y = pyautogui.position()
            return {"x": x, "y": y}

        else:
            return {"error": f"unknown action: {a}"}

        time.sleep(0.15)
        return _capture_screenshot()

    except Exception as e:
        log.error("Computer action %s failed: %s", a, e)
        return {"error": str(e)}
