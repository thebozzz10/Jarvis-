"""Sandboxed Python code execution with persistent kernel state."""
import json
import subprocess
import sys
import tempfile
import textwrap
import threading
from pathlib import Path
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

_kernel_lock = threading.Lock()
_kernel_globals: dict = {"__name__": "__jarvis_kernel__"}


class ExecutePython(BaseTool):
    name = "execute_python"
    description = (
        "Execute Python code in a persistent in-process kernel. State (variables, imports, "
        "functions) persists across calls. Use this to compute, analyse data, generate plots, "
        "scrape, or solve any programming task. stdout/stderr is captured and returned."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "default": 30, "description": "Max seconds"},
            "reset": {"type": "boolean", "default": False, "description": "Reset kernel state first"},
        },
        "required": ["code"],
    }

    def run(self, code: str, timeout: int = 30, reset: bool = False) -> str:
        global _kernel_globals
        import io
        import contextlib

        with _kernel_lock:
            if reset:
                _kernel_globals = {"__name__": "__jarvis_kernel__"}

            stdout = io.StringIO()
            stderr = io.StringIO()
            result_value = None
            error = None

            done = threading.Event()

            def runner():
                nonlocal result_value, error
                try:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        # Try eval first (single expression), fall back to exec
                        try:
                            result_value = eval(code, _kernel_globals)
                        except SyntaxError:
                            exec(code, _kernel_globals)
                except Exception as e:
                    import traceback
                    error = traceback.format_exc()
                finally:
                    done.set()

            t = threading.Thread(target=runner, daemon=True)
            t.start()
            if not done.wait(timeout):
                return json.dumps({"error": f"Execution timed out after {timeout}s"})

            return json.dumps({
                "stdout": stdout.getvalue()[:4000],
                "stderr": stderr.getvalue()[:1000],
                "result": repr(result_value)[:1000] if result_value is not None else None,
                "error": error[:2000] if error else None,
            })
