"""
Local Text-to-Speech Engine with Dual Providers:
1. Piper TTS (Ultra-fast neural local speech via ONNX)
2. Windows SAPI5 / pyttsx3 fallback (Instant native Windows speech, zero downloads needed)
"""
import re
import os
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from config import PIPER_EXEC_PATH, PIPER_MODEL_PATH, USE_FALLBACK_TTS

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


def clean_text_for_speech(text: str) -> str:
    """Strip markdown symbols, URLs, and code blocks before speaking."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', 'code block omitted', text)
    # Remove inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove markdown headers and emphasis
    text = re.sub(r'[*_#~>]', '', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', 'link', text)
    return text.strip()


class TextToSpeechWorker(QThread):
    speech_started = Signal()
    speech_finished = Signal()
    speech_error = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.raw_text = text

    def run(self):
        cleaned_text = clean_text_for_speech(self.raw_text)
        if not cleaned_text:
            self.speech_finished.emit()
            return

        self.speech_started.emit()

        # Try Piper TTS first if configured
        if PIPER_EXEC_PATH and Path(PIPER_EXEC_PATH).is_file() and PIPER_MODEL_PATH and Path(PIPER_MODEL_PATH).is_file():
            try:
                self._speak_with_piper(cleaned_text)
                self.speech_finished.emit()
                return
            except Exception as e:
                if not USE_FALLBACK_TTS:
                    self.speech_error.emit(f"Piper TTS failed: {e}")
                    return

        # Fallback to Windows SAPI (pyttsx3)
        if HAS_PYTTSX3:
            try:
                self._speak_with_pyttsx3(cleaned_text)
                self.speech_finished.emit()
                return
            except Exception as e:
                self.speech_error.emit(f"TTS Fallback failed: {e}")
                return

        self.speech_error.emit("No TTS provider available. Install 'pyttsx3' or configure Piper TTS.")

    def _speak_with_piper(self, text: str):
        """Invoke piper executable via pipe to playback."""
        cmd = [
            str(PIPER_EXEC_PATH),
            "--model", str(PIPER_MODEL_PATH),
            "--output_raw"
        ]
        # Run piper and stream to sounddevice or temporary wave
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(input=text.encode("utf-8"))
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="ignore"))

        import sounddevice as sd
        import numpy as np
        audio_array = np.frombuffer(stdout, dtype=np.int16)
        sd.play(audio_array, samplerate=22050)
        sd.wait()

    def _speak_with_pyttsx3(self, text: str):
        """Native Windows SAPI5 speech generation."""
        engine = pyttsx3.init()
        # Set speech rate and volume
        engine.setProperty('rate', 185)
        engine.setProperty('volume', 0.95)

        # Select a modern Windows voice if available
        voices = engine.getProperty('voices')
        for voice in voices:
            if "david" in voice.name.lower() or "zira" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        engine.say(text)
        engine.runAndWait()
        engine.stop()

