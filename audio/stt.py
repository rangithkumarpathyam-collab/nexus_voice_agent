"""
Faster-Whisper Speech-to-Text Worker Thread.
Runs audio decoding asynchronously on a dedicated thread to preserve smooth 60 FPS UI rendering.
"""
import numpy as np
from typing import Optional, Any
from PySide6.QtCore import QThread, Signal
from config import STT_MODEL_SIZE, STT_DEVICE, STT_COMPUTE_TYPE

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False


class SpeechToTextWorker(QThread):
    transcription_started = Signal()
    transcription_finished = Signal(str)
    transcription_error = Signal(str)

    _cached_model: Optional[Any] = None

    def __init__(self, audio_data: np.ndarray, parent=None):
        super().__init__(parent)
        self.audio_data = audio_data

    @classmethod
    def get_model(cls):
        if not HAS_WHISPER:
            raise ImportError(
                "The 'faster-whisper' package is not installed. Please run: pip install faster-whisper"
            )
        if cls._cached_model is None:
            cls._cached_model = WhisperModel(
                STT_MODEL_SIZE,
                device=STT_DEVICE,
                compute_type=STT_COMPUTE_TYPE,
                cpu_threads=4
            )
        return cls._cached_model

    def run(self):
        if self.audio_data is None or len(self.audio_data) == 0:
            self.transcription_finished.emit("")
            return

        self.transcription_started.emit()

        try:
            model = self.get_model()

            # Ensure audio is float32 16kHz
            if self.audio_data.dtype != np.float32:
                audio = self.audio_data.astype(np.float32)
            else:
                audio = self.audio_data.copy()

            # Peak amplitude normalization (boost quiet laptop microphones)
            max_amp = float(np.max(np.abs(audio)))
            if max_amp > 0.001:
                audio = audio / max_amp * 0.95

            # Transcribe with high-accuracy parameters tuned for voice commands:
            # - vad_filter=False avoids dropping first words or quiet speech
            # - language="en" eliminates language detection latency and hallucinations
            # - initial_prompt primes the decoder with common desktop assistant commands
            segments, info = model.transcribe(
                audio,
                beam_size=5,
                language="en",
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,
                initial_prompt="Open YouTube, Spotify, Chrome, Notepad, play music, search Google, type."
            )

            full_text = " ".join([segment.text.strip() for segment in segments]).strip()
            print(f"[STT] Audio length: {len(audio)/16000:.2f}s, Peak: {max_amp:.4f} -> '{full_text}'")
            self.transcription_finished.emit(full_text)

        except Exception as e:
            print(f"[STT Error] {e}")
            self.transcription_error.emit(f"Speech recognition error: {str(e)}")

