"""
Nexus AI Assistant Configuration
Centralized configuration for audio, models, Ollama, UI styling, and safety rules.
"""
from pathlib import Path
import os

# --- BASE DIRECTORIES ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database file
DB_PATH = DATA_DIR / "assistant.db"

# --- OLLAMA LOCAL LLM SETTINGS ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# Default Qwen model. Uses installed qwen2.5-coder:7b or fallback
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
SYSTEM_PROMPT = (
    "You are Nexus, a futuristic, intelligent Windows AI assistant inspired by Jarvis and HeyNixi. "
    "Keep spoken conversational answers concise, crisp, and direct (1-3 sentences maximum). "
    "If the user asks for code, explanations, or structured plans, provide clean markdown formatting. "
    "Be polite, witty, confident, and highly efficient."
)

# --- SPEECH-TO-TEXT (Faster-Whisper) ---
STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "base.en")  # 'tiny.en', 'base.en', 'small.en'
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")             # 'cpu' or 'cuda'
STT_COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8") # 'int8', 'float16', or 'default'

# --- AUDIO CAPTURE SETTINGS ---
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_DTYPE = "int16"
AUDIO_SILENCE_TIMEOUT_S = 1.8  # Automatic endpoint cut-off on trailing silence
AUDIO_VAD_THRESHOLD = 0.015    # Energy threshold for speech detection

# --- TEXT-TO-SPEECH (TTS) ---
# Piper TTS executable and ONNX model paths (optional if Piper binary is present)
PIPER_EXEC_PATH = os.getenv("PIPER_EXEC_PATH", "")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "")
USE_FALLBACK_TTS = True  # Automatically uses Windows SAPI (pyttsx3) if Piper is not installed

# --- HOTKEYS & INPUT ---
# By default, use Left Alt (or Right Ctrl) for Voice Push-To-Talk
PTT_HOTKEY = "Key.alt_l"
PTT_MODE = "hold"  # 'hold' (press to listen, release to send) or 'toggle'

# --- CYBERPUNK FUTURISTIC THEME ---
THEME = {
    "bg_dark": "#0B0D14",
    "bg_surface": "#121624",
    "bg_surface_hover": "#1B2135",
    "pill_bg": "rgba(11, 13, 20, 0.94)",
    "border_glow": "#00F0FF",
    "border_dim": "#1E293B",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "cyan_accent": "#00F0FF",
    "purple_accent": "#A855F7",
    "emerald_accent": "#10B981",
    "warning_amber": "#F59E0B",
    "danger_red": "#EF4444",
}

