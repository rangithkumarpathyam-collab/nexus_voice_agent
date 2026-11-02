# 🌌 Nexus Voice Agent

A futuristic, completely local floating AI desktop assistant for Windows inspired by **HeyNixi**, **Dynamic Island**, and **Jarvis**.

Built with **Python 3.11+**, **PySide6 (Qt6)**, **Ollama (Qwen 2.5)**, **Faster-Whisper**, **Piper / SAPI TTS**, **Pynput**, and **SQLite WAL**.

---

## 🌟 Key Features

### 1. 👁️ HeyNixi-Inspired Dynamic Mascot
- **MouseLook Real-Time Cursor Tracking**: The mascot's dual white capsule eyes dynamically track your cursor across the screen at 50 FPS via global coordinates (`QCursor.pos()`).
- **Frequent Natural Blinking**: The eyes naturally squish and blink every 1.5 – 3.2 seconds.
- **Inactivity Sleep Mode**: If the mouse cursor stays motionless for ~3.5 seconds, the eyes smoothly close into relaxed horizontal sleeping slits (`- -`) with gentle breathing animation (`sleep_breath`). As soon as you nudge your mouse, they wake up instantly.
- **Cyberpunk Audio Headset**: An arched headband with neon cyan piping and over-ear earcups automatically snaps onto the mascot when playing music tracks (e.g. YouTube or Spotify). Outer beat wave rings pulse from the earcups and the mascot bobs rhythmically to the music.

### 2. ⚡ Three-State Dynamic Island Morphing
- **State 1: Compact Notch (112px × 44px)**: An ultra-clean, pitch-black (`#000000`) stadium capsule displaying only the mascot face with zero buttons or clutter.
- **State 2: VoiceHUD Recording Notch (146px × 96px)**: Holding **`Left Alt`** (or pressing **`F8`**) smoothly expands the notch downward into a sleek recording drawer featuring glowing eyes, a centered `Command` badge, and 4 animated blue vertical audio bars (`||||`) that bounce dynamically to your speech. Releasing `Left Alt` transcribes, executes, and smoothly tucks back into the compact notch.
- **State 3: Full Unified Window (440px × 480px)**: Double-clicking the notch expands into a continuous dark card featuring:
  - Top mascot eyes docked at the notch
  - Segmented pill switch: `[ Chat ] [ History ]`
  - Action icons: Pointer Mode `↖`, Voice Toggle `🎙️`, New Chat `✏️`, Collapse `⌃`
  - Message area with smooth user/AI bubbles and empty state placeholder (*"Say something, or type below"*)
  - Bottom input bar with *"Ask Nixi..."* and circular blue send button with white up-arrow `↑`

### 3. 🔒 100% Local Privacy & Fast Execution
- **Ultra-Fast Command Routing (< 1ms)**: Deterministic regex and prefix matching resolves common desktop tasks (launching applications, web services, playing music, system volume) instantly without blocking network or LLM calls.
- **Local Speech-to-Text**: Offline transcription via **Faster-Whisper** with peak amplitude normalization.
- **Local Neural LLM**: Streams responses directly from **Ollama** running **Qwen 2.5** (zero data leaves your machine).
- **Dual TTS Engine**: Offline speech playback via **Piper TTS** with seamless fallback to native **Windows SAPI**.
- **Interactive Safety Guardrail**: Computer-control actions require explicit user approval (`Authorize` or `Reject`).
- **Event-Sourced SQLite DB**: Sessions, messages, and action audit logs persist in embedded SQLite with WAL mode.

---

## 📁 Architecture & File Layout

```
nexus_voice_agent/
├── config.py                 # Central configurations (models, audio params, hotkeys)
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── run_assistant.bat         # One-click Windows desktop launcher
├── main.py                   # Application entrypoint & global hotkey manager
├── audio/
│   ├── __init__.py
│   ├── recorder.py           # 16kHz audio capture with RMS level visualizer callback
│   ├── stt.py                # Faster-Whisper background worker thread
│   └── tts.py                # Piper & Windows SAPI speech synthesis worker
├── automation/
│   ├── __init__.py
│   ├── app_launcher.py       # Indexed Windows application & web service launcher
│   ├── command_router.py     # Deterministic routing (< 1ms execution)
│   ├── media_player.py       # Asynchronous YouTube & Spotify media launcher
│   ├── agent_planner.py      # Multi-step task decomposition engine
│   └── safety_guard.py       # Strict explicit user confirmation guardrail
├── database/
│   ├── __init__.py
│   └── db_manager.py         # SQLite WAL persistence for conversations & audit logs
├── llm/
│   ├── __init__.py
│   └── ollama_client.py      # Asynchronous Ollama streaming worker & health checker
└── ui/
    ├── __init__.py
    ├── styles.py             # Cyberpunk dark stylesheets (QSS)
    ├── audio_visualizer.py   # CyberMascotEyes widget (gaze tracking, headset, sleep)
    └── floating_hud.py       # Frameless, morphing Dynamic Island HUD & window
```

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11 / 3.12 / 3.14 on Windows 10/11)
- **Ollama**: [Download Ollama](https://ollama.com/) and pull a model:
  ```powershell
  ollama pull qwen2.5-coder:7b
  # or lightweight:
  ollama pull qwen2.5:3b
  ```

### 2. Clone & Setup Virtual Environment
```powershell
git clone https://github.com/rangithkumarpathyam-collab/nexus_voice_agent.git
cd nexus_voice_agent

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Launch Nexus
```powershell
python main.py
# Or simply double-click:
run_assistant.bat
```

---

## 🎮 Controls & Shortcuts

| Action | Shortcut / Trigger | Description |
| :--- | :--- | :--- |
| **Push-to-Talk (Voice)** | **Hold `Left Alt`** or **`Right Ctrl`** | Drops down the **VoiceHUD**; speak your command, then release to execute. |
| **Voice Toggle** | **`F8`** or **`🎙️` Icon** | Single press to start listening; press again to finish. |
| **In-Place Dictation** | **Hold `Right Alt`** | Transcribes and types speech directly into your active window (with approval). |
| **Move Notch** | **Click & Drag** | Drag the notch anywhere across your displays (position is persisted). |
| **Open Full Card** | **Double-Click Notch** | Expands into the full 440px × 480px Unified Window (Chat & History). |
| **Collapse Card** | **`⌃` Button** | Folds the full card back into the compact top notch. |
| **Toggle Headset Mode** | **Right-Click Eyes** | Manually equips/unequips the cyberpunk headset and music dancing bob. |
| **Inactivity Sleep** | **Idle Mouse (3.5s)** | Eyes close into sleeping slits and breathe gently. Moving mouse wakes them up. |

---

## 🗣️ Voice Commands Examples

- *"Open YouTube"* (Opens browser tab **without** putting on headset)
- *"Play Interstellar on YouTube"* (Launches track and equips animated cyberpunk headset)
- *"Play Daft Punk on Spotify"* (Launches Spotify and equips headset)
- *"What time is it?"* / *"What's today's date?"*
- *"Increase volume"* / *"Mute audio"*
- *"Headset on"* / *"Headset off"*
- *"Stop music"* / *"Pause"* (Sends Windows `playpause` media key and removes headset)

---

## 📄 License
MIT License. Clean-room implementation built from scratch without proprietary dependencies.
