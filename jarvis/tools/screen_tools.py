"""Screen capture, OCR, and element-finding tools."""
import base64
import io
import json
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.config import get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)
QUALITY = int(get("tools", "screenshot_quality", 85))


class TakeScreenshot(BaseTool):
    name = "take_screenshot"
    description = "Capture the current screen or a specific region. Returns a base64-encoded PNG image that you can analyse."
    input_schema = {
        "type": "object",
        "properties": {
            "region": {
                "type": "object",
                "description": "Optional bounding box {x, y, width, height}. Omit for full screen.",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
            },
            "monitor": {"type": "integer", "description": "Monitor index (0=primary)", "default": 0},
        },
        "required": [],
    }

    def run(self, region: dict | None = None, monitor: int = 0) -> str:
        try:
            import pyautogui
            from PIL import Image

            if region:
                img = pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
            else:
                img = pyautogui.screenshot()

            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            b64 = base64.standard_b64encode(buf.getvalue()).decode()
            size = f"{img.width}x{img.height}"
            return json.dumps({"image_base64": b64, "size": size, "format": "png"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class ReadScreenText(BaseTool):
    name = "read_screen_text"
    description = "Extract all visible text from the screen using OCR. Useful for reading content you can see."
    input_schema = {
        "type": "object",
        "properties": {
            "region": {
                "type": "object",
                "description": "Optional {x, y, width, height} bounding box",
                "properties": {
                    "x": {"type": "integer"}, "y": {"type": "integer"},
                    "width": {"type": "integer"}, "height": {"type": "integer"},
                },
            },
        },
        "required": [],
    }

    def run(self, region: dict | None = None) -> str:
        try:
            import pyautogui
            import pytesseract
            from PIL import Image

            if region:
                img = pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
            else:
                img = pyautogui.screenshot()

            text = pytesseract.image_to_string(img)
            return json.dumps({"text": text.strip(), "char_count": len(text)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class FindOnScreen(BaseTool):
    name = "find_on_screen"
    description = "Locate a UI element or text string on screen. Returns coordinates you can click."
    input_schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Text or description of element to find"},
            "method": {
                "type": "string",
                "enum": ["text", "image_template"],
                "default": "text",
                "description": "Search method",
            },
        },
        "required": ["target"],
    }

    def run(self, target: str, method: str = "text") -> str:
        try:
            import pyautogui
            import pytesseract
            from PIL import Image

            img = pyautogui.screenshot()

            if method == "text":
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                for i, word in enumerate(data["text"]):
                    if target.lower() in word.lower():
                        x = data["left"][i] + data["width"][i] // 2
                        y = data["top"][i] + data["height"][i] // 2
                        return json.dumps({"found": True, "x": x, "y": y, "text": word})
                return json.dumps({"found": False, "message": f"'{target}' not found on screen"})
            else:
                return json.dumps({"error": "image_template method requires a template file path"})
        except Exception as e:
            return json.dumps({"error": str(e)})
