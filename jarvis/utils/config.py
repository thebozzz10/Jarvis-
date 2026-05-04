import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_config: dict = {}
_config_path = Path(__file__).parent.parent.parent / "config.yaml"


def _load() -> dict:
    global _config
    if not _config:
        if _config_path.exists():
            with open(_config_path) as f:
                _config = yaml.safe_load(f) or {}
    return _config


def get(section: str, key: str, default=None):
    cfg = _load()
    return cfg.get(section, {}).get(key, default)


def get_section(section: str) -> dict:
    return _load().get(section, {})


# Typed accessors
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
PORCUPINE_ACCESS_KEY: str = os.getenv("PORCUPINE_ACCESS_KEY", "")
MODEL: str = os.getenv("JARVIS_MODEL") or get("jarvis", "model", "claude-sonnet-4-6")
LOG_LEVEL: str = os.getenv("JARVIS_LOG_LEVEL", "INFO")
DATA_DIR: Path = Path(os.getenv("JARVIS_DATA_DIR", "~/.jarvis")).expanduser()
TTS_VOICE: str = os.getenv("JARVIS_VOICE") or get("voice", "tts_voice", "en-US-GuyNeural")
DB_PATH: Path = Path(get("memory", "db_path", "~/.jarvis/jarvis.db")).expanduser()
