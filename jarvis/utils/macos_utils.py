"""macOS permission checks and native helpers."""
import subprocess
import platform
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


def is_macos() -> bool:
    return platform.system() == "Darwin"


def macos_version() -> str:
    if is_macos():
        return platform.mac_ver()[0]
    return "unknown"


def check_accessibility_permission() -> bool:
    """Returns True if the process has macOS Accessibility permission."""
    if not is_macos():
        return True
    try:
        import Cocoa  # noqa: F401
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def request_accessibility_permission():
    """Prompt macOS to show the Accessibility permission dialog."""
    if not is_macos():
        return
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions
        from Foundation import NSDictionary
        opts = NSDictionary.dictionaryWithObject_forKey_(True, "AXTrustedCheckOptionPrompt")
        AXIsProcessTrustedWithOptions(opts)
    except Exception as e:
        log.warning("Could not request accessibility permission: %s", e)


def send_macos_notification(title: str, message: str, subtitle: str = ""):
    """Send a macOS notification via osascript."""
    subtitle_part = f'subtitle "{subtitle}"' if subtitle else ""
    script = f'display notification "{message}" with title "{title}" {subtitle_part}'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    except Exception as e:
        log.warning("Notification failed: %s", e)


def get_frontmost_app() -> str:
    """Return name of currently frontmost macOS application."""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return ""
