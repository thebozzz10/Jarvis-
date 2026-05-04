# JARVIS — AI Assistant for macOS

> *"Just A Rather Very Intelligent System"*

A fully-featured Iron Man JARVIS-inspired AI assistant for macOS, powered by Claude claude-sonnet-4-6 with streaming tool use, persistent memory, voice control, and a high-tech dark-themed UI.

---

## Features

- **Claude AI Brain** — streaming tool use with vision, powered by `claude-sonnet-4-6`
- **25 Tools** — screen capture, mouse/keyboard control, app management, file system, web search, shell execution, system info, and more
- **Voice Control** — say "Hey Jarvis" (wake word) to activate, local Whisper STT, neural TTS
- **Global Hotkey** — Cmd+Space to summon the window instantly
- **macOS Menu Bar** — always accessible from the menu bar
- **Persistent Memory** — SQLite database remembers everything across sessions
- **High-Tech UI** — dark theme with cyan/blue accents, animated waveform orb

---

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/thebozzz10/Jarvis-
cd Jarvis-
python3.11 -m venv .venv && source .venv/bin/activate
python setup.py

# 2. Add API keys to .env
# ANTHROPIC_API_KEY=sk-ant-...
# PORCUPINE_ACCESS_KEY=...  (optional, for wake word)

# 3. Grant macOS permissions
# System Settings → Privacy → Accessibility
# System Settings → Privacy → Microphone
# System Settings → Privacy → Screen Recording

# 4. Run JARVIS
python -m jarvis.main

# Text-only mode (no microphone required)
python -m jarvis.main --no-voice
```

---

## Architecture

```
jarvis/
├── core/        # Claude agent, tool registry, event bus, context manager
├── voice/       # Wake word (Porcupine), STT (Whisper), TTS (edge-tts)
├── tools/       # 25 Claude tools: screen, input, apps, files, web, system, memory
├── memory/      # SQLite persistent memory with FTS5 search
├── ui/          # customtkinter chat window + rumps menu bar + HUD overlay
└── utils/       # Config, logging, hotkeys, macOS helpers
```

---

## Tools

| Category | Tools |
|----------|-------|
| Screen | `take_screenshot`, `read_screen_text`, `find_on_screen` |
| Input | `mouse_click`, `type_text`, `key_press`, `mouse_drag`, `scroll` |
| Apps | `launch_app`, `list_windows`, `focus_window` |
| Files | `read_file`, `write_file`, `list_directory`, `find_files` |
| Web | `web_search`, `fetch_webpage` |
| System | `get_system_info`, `run_shell_command`, `send_notification`, `set_volume` |
| Memory | `remember`, `recall`, `get_time_and_date`, `clipboard_control` |

---

## Requirements

- macOS 12+
- Python 3.11+
- Anthropic API key
- Picovoice access key (optional, for "Hey Jarvis" wake word)
- `brew install tesseract` (optional, for OCR)

---

## Configuration

Edit `config.yaml` to customise voice, UI colors, model, hotkeys, and more.
Copy `.env.example` → `.env` and add your API keys.
