"""
High-Performance Audio Ingestion & Level Monitoring.
Streams 16kHz mono audio from the system microphone using sounddevice.
Computes real-time RMS energy levels for reactive UI animations.
"""
import threading
import numpy as np
from typing import Optional, Callable, Any
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


class AudioRecorder:
    def __init__(self, sample_rate: int = AUDIO_SAMPLE_RATE, channels: int = AUDIO_CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self._lock = threading.Lock()
        self._frames = []
        self._stream: Optional[Any] = None
        self.level_callback: Optional[Callable[[float], None]] = None

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_recording:
            return

        with self._lock:
            # indata is numpy array float32 in range [-1.0, 1.0]
            data_copy = indata.copy()
            self._frames.append(data_copy)

        # Calculate RMS energy for visualizer
        if self.level_callback:
            rms = float(np.sqrt(np.mean(data_copy ** 2)))
            self.level_callback(rms)

    def start_recording(self) -> bool:
        if not HAS_SOUNDDEVICE:
            raise RuntimeError("The 'sounddevice' package is required for audio recording.")

        if self.is_recording:
            return True

        with self._lock:
            self._frames = []
            self.is_recording = True

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=1024
            )
            self._stream.start()
            return True
        except Exception as e:
            self.is_recording = False
            raise RuntimeError(f"Failed to open microphone input stream: {e}")

    def stop_recording(self) -> np.ndarray:
        if not self.is_recording:
            return np.array([], dtype=np.float32)

        self.is_recording = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            audio_data = np.concatenate(self._frames, axis=0).flatten()
            self._frames = []

        return audio_data

