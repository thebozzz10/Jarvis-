"""Weather and Maps tools."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


class GetWeather(BaseTool):
    name = "get_weather"
    description = "Get current weather and forecast for a location using wttr.in (no API key required)."
    input_schema = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City or place name"},
            "format": {"type": "string", "enum": ["short", "full"], "default": "short"},
        },
        "required": ["location"],
    }

    def run(self, location: str, format: str = "short") -> str:
        try:
            import requests
            fmt_param = "?format=4" if format == "short" else "?format=j1"
            url = f"https://wttr.in/{requests.utils.quote(location)}{fmt_param}"
            resp = requests.get(url, headers={"User-Agent": "curl/8"}, timeout=10)
            if format == "short":
                return json.dumps({"location": location, "weather": resp.text.strip()})
            else:
                data = resp.json()
                current = data.get("current_condition", [{}])[0]
                area = data.get("nearest_area", [{}])[0]
                return json.dumps({
                    "location": area.get("areaName", [{}])[0].get("value", location),
                    "temp_c": current.get("temp_C"),
                    "feels_like_c": current.get("FeelsLikeC"),
                    "description": current.get("weatherDesc", [{}])[0].get("value", ""),
                    "humidity": current.get("humidity"),
                    "wind_kph": current.get("windspeedKmph"),
                })
        except Exception as e:
            return json.dumps({"error": str(e)})


class OpenInMaps(BaseTool):
    name = "open_in_maps"
    description = "Open a location, address, or directions in Apple Maps."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Place name, address, or 'from X to Y'"},
        },
        "required": ["query"],
    }

    def run(self, query: str) -> str:
        try:
            import urllib.parse
            url = f"http://maps.apple.com/?q={urllib.parse.quote(query)}"
            subprocess.run(["open", url], check=True)
            return json.dumps({"success": True, "opened": query})
        except Exception as e:
            return json.dumps({"error": str(e)})
