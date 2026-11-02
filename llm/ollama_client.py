"""
Asynchronous Ollama Streaming Client.
Communicates with the local Ollama instance on http://127.0.0.1:11434.
Streams tokens to the UI via Qt signals without locking the main thread.
"""
import json
import requests
from typing import List, Dict, Optional
from PySide6.QtCore import QThread, Signal
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYSTEM_PROMPT


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> bool:
        """Verify that Ollama server daemon is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_installed_models(self) -> List[str]:
        """Return list of model tags available in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []


class OllamaStreamWorker(QThread):
    chunk_received = Signal(str)
    generation_finished = Signal(str)
    generation_error = Signal(str)

    def __init__(
        self,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        model: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        parent=None
    ):
        super().__init__(parent)
        self.user_prompt = user_prompt
        self.history = history or []
        self.model = model
        self.base_url = base_url.rstrip("/")

    def run(self):
        url = f"{self.base_url}/api/chat"

        # Build message context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": self.user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": 4096
            }
        }

        try:
            response = requests.post(url, json=payload, stream=True, timeout=(3.0, 60.0))
            if response.status_code != 200:
                self.generation_error.emit(
                    f"Ollama returned HTTP {response.status_code}: {response.text}"
                )
                return

            accumulated_text = []

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk_json = json.loads(line.decode("utf-8"))
                    message_obj = chunk_json.get("message", {})
                    token = message_obj.get("content", "")
                    if token:
                        accumulated_text.append(token)
                        self.chunk_received.emit(token)

                    if chunk_json.get("done", False):
                        break
                except Exception:
                    continue

            full_text = "".join(accumulated_text).strip()
            self.generation_finished.emit(full_text)

        except requests.exceptions.ConnectionError:
            self.generation_error.emit(
                f"Cannot connect to Ollama at {self.base_url}. Please ensure 'ollama serve' is running."
            )
        except requests.exceptions.Timeout:
            self.generation_error.emit("Ollama generation timed out.")
        except Exception as e:
            self.generation_error.emit(f"LLM generation failed: {str(e)}")

