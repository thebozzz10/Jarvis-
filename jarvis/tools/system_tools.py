"""System info, shell execution, notifications, and volume control."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.logger import get_logger
from jarvis.utils.macos_utils import send_macos_notification

log = get_logger(__name__)


class GetSystemInfo(BaseTool):
    name = "get_system_info"
    description = "Get system information: CPU usage, memory, disk space, battery, network, and running processes."
    input_schema = {
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {"type": "string",
                          "enum": ["cpu", "memory", "disk", "network", "battery", "processes", "all"]},
                "default": ["all"],
            },
        },
        "required": [],
    }

    def run(self, categories: list[str] | None = None) -> str:
        import psutil, platform, datetime
        if not categories:
            categories = ["all"]
        cats = set(categories)
        info: dict = {}

        if "cpu" in cats or "all" in cats:
            info["cpu"] = {
                "percent": psutil.cpu_percent(interval=0.5),
                "count_physical": psutil.cpu_count(logical=False),
                "count_logical": psutil.cpu_count(logical=True),
                "freq_mhz": round(psutil.cpu_freq().current) if psutil.cpu_freq() else None,
            }

        if "memory" in cats or "all" in cats:
            vm = psutil.virtual_memory()
            info["memory"] = {
                "total_gb": round(vm.total / 1e9, 1),
                "used_gb": round(vm.used / 1e9, 1),
                "available_gb": round(vm.available / 1e9, 1),
                "percent": vm.percent,
            }

        if "disk" in cats or "all" in cats:
            disk = psutil.disk_usage("/")
            info["disk"] = {
                "total_gb": round(disk.total / 1e9, 1),
                "used_gb": round(disk.used / 1e9, 1),
                "free_gb": round(disk.free / 1e9, 1),
                "percent": disk.percent,
            }

        if "battery" in cats or "all" in cats:
            batt = psutil.sensors_battery()
            info["battery"] = {
                "percent": batt.percent if batt else None,
                "plugged_in": batt.power_plugged if batt else None,
            }

        if "processes" in cats or "all" in cats:
            procs = []
            for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                            key=lambda x: x.info.get("cpu_percent", 0) or 0, reverse=True)[:10]:
                procs.append(p.info)
            info["top_processes"] = procs

        info["platform"] = platform.mac_ver()[0] or platform.system()
        info["uptime_hours"] = round((datetime.datetime.now().timestamp() - psutil.boot_time()) / 3600, 1)
        return json.dumps(info)


class RunShellCommand(BaseTool):
    name = "run_shell_command"
    description = "Execute a shell command and return stdout/stderr. Use with care — destructive commands require confirmation."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {"type": "integer", "description": "Max seconds to wait", "default": 30},
            "working_dir": {"type": "string", "description": "Working directory"},
        },
        "required": ["command"],
    }

    def run(self, command: str, timeout: int = 30, working_dir: str | None = None) -> str:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=working_dir,
            )
            return json.dumps({
                "stdout": result.stdout[:4000],
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
            })
        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"Command timed out after {timeout}s"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SendNotification(BaseTool):
    name = "send_notification"
    description = "Send a macOS system notification banner."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
            "subtitle": {"type": "string", "default": ""},
        },
        "required": ["title", "message"],
    }

    def run(self, title: str, message: str, subtitle: str = "") -> str:
        try:
            send_macos_notification(title, message, subtitle)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SetVolume(BaseTool):
    name = "set_volume"
    description = "Get or set the macOS system audio volume (0-100), or mute/unmute."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["get", "set", "mute", "unmute"]},
            "level": {"type": "integer", "description": "0-100, required when action=set"},
        },
        "required": ["action"],
    }

    def run(self, action: str, level: int | None = None) -> str:
        try:
            if action == "get":
                result = subprocess.run(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    capture_output=True, text=True,
                )
                return json.dumps({"volume": int(result.stdout.strip())})
            elif action == "set" and level is not None:
                level = max(0, min(100, level))
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
                return json.dumps({"success": True, "volume": level})
            elif action == "mute":
                subprocess.run(["osascript", "-e", "set volume with output muted"], check=True)
                return json.dumps({"success": True, "muted": True})
            elif action == "unmute":
                subprocess.run(["osascript", "-e", "set volume without output muted"], check=True)
                return json.dumps({"success": True, "muted": False})
            return json.dumps({"error": "Invalid action or missing level"})
        except Exception as e:
            return json.dumps({"error": str(e)})
