# JARVIS — Advanced AI Assistant for macOS

> *"Just A Rather Very Intelligent System"*

A next-generation Iron Man JARVIS-inspired AI assistant for macOS — powered by Claude claude-sonnet-4-6 with computer-use, extended thinking, semantic memory, knowledge graphs, sub-agent delegation, and full integration into Calendar, Reminders, Contacts, Mail, Messages, Notes, Music, and Shortcuts.

---

## What's Inside

### Brain
- **Claude claude-sonnet-4-6** with streaming tool use
- **Extended thinking** (5K-token reasoning budget) for complex problems
- **Prompt caching** (~90% cost reduction on repeat context)
- **Anthropic Computer Use** — Claude natively controls your Mac with screenshot feedback
- **Sub-agent delegation** — spawn parallel sub-agents for compound tasks

### Memory
- **SQLite persistent store** with WAL + FTS5 full-text search
- **Vector embeddings** (sentence-transformers) for semantic recall
- **Knowledge graph** with entities and relationships
- **Auto-embedding** on every memory write

### Voice
- **"Hey Jarvis" wake word** via Picovoice Porcupine
- **faster-whisper** local speech-to-text (private, no cloud)
- **edge-tts** neural voice (or ElevenLabs ready)
- **Real-time barge-in** — interrupt while Jarvis is speaking

### Proactive Intelligence
- Background monitor watches calendar, battery, app context
- Speaks up unprompted for upcoming events, low battery, etc.

### UI
- **ARC Reactor visualization** — particle field, concentric rotating rings, pulsing core
- High-tech dark theme (`#0A0E1A` bg, `#00D4FF` cyan accent)
- Streaming chat, animated state transitions
- macOS menu bar + Cmd+Space global hotkey + floating HUD overlay

---

## All 47 Tools

### Original 25
| Category | Tools |
|---|---|
| Screen | `take_screenshot`, `read_screen_text`, `find_on_screen` |
| Input | `mouse_click`, `type_text`, `key_press`, `mouse_drag`, `scroll` |
| Apps | `launch_app`, `list_windows`, `focus_window` |
| Files | `read_file`, `write_file`, `list_directory`, `find_files` |
| Web | `web_search`, `fetch_webpage` |
| System | `get_system_info`, `run_shell_command`, `send_notification`, `set_volume` |
| Memory | `remember`, `recall`, `get_time_and_date`, `clipboard_control` |

### Phase 2 — Personal Data
| Category | Tools |
|---|---|
| Calendar | `get_calendar_events`, `create_calendar_event` |
| Reminders | `get_reminders`, `create_reminder` |
| Contacts | `search_contacts` |
| Mail | `get_unread_mail`, `send_mail` |
| Messages | `send_message` (iMessage) |
| Notes | `create_note`, `search_notes` |
| Music | `control_music` (Apple Music + Spotify) |
| Shortcuts | `run_shortcut`, `list_shortcuts` |

### Phase 2 — Advanced Capabilities
| Category | Tools |
|---|---|
| Code | `execute_python` (persistent kernel) |
| Delegation | `delegate_task` (sub-agents) |
| Maps/Weather | `get_weather`, `open_in_maps` |
| Semantic Memory | `semantic_recall`, `add_knowledge_relation`, `query_knowledge_graph` |
| Computer Use | Native Anthropic `computer` tool — auto-included |

---

## Quick Start

```bash
# 1. Install
git clone https://github.com/thebozzz10/Jarvis-
cd Jarvis-
git checkout claude/jarvis-ai-assistant-N53Hk
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. API keys
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY (required) and PORCUPINE_ACCESS_KEY (optional)

# 3. macOS permissions: Accessibility, Microphone, Screen Recording, Automation

# 4. Run
python -m jarvis.main             # full system with voice
python -m jarvis.main --no-voice  # text only
```

---

## Architecture

```
jarvis/
├── core/         # Agent (streaming + thinking + caching), tool registry, event bus
├── voice/        # Wake word, STT, TTS, real-time barge-in
├── tools/        # 47 tools across 13 modules
├── memory/       # SQLite + FTS5 + vector embeddings + knowledge graph
├── proactive/    # Background monitor — speaks up unprompted
├── ui/           # ARC reactor, chat, status bar, menu bar, HUD overlay
└── utils/        # Config, logger, macOS helpers, hotkeys
```

---

## Configuration

Edit `config.yaml`:

```yaml
jarvis:
  model: claude-sonnet-4-6
  extended_thinking: true
  thinking_budget: 5000
  prompt_caching: true
  computer_use: true
```

---

## Requirements

- macOS 12+ (Shortcuts CLI, EventKit)
- Python 3.11+
- Anthropic API key
- Picovoice access key (optional)
- `brew install tesseract` (optional, for OCR)
- ~500 MB disk for sentence-transformers model on first use
