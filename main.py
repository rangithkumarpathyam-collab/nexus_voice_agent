"""
Nexus Desktop Assistant - Main Entrypoint
Initializes Qt Application, global pynput keyboard hooks, and launches the Floating HUD.
"""
import sys
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from config import PTT_HOTKEY
from database.db_manager import DatabaseManager
from ui.floating_hud import FloatingHUD

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class GlobalHotkeyManager:
    """
    Listens for global hotkeys across all Windows apps:
    - Left Alt (or Right Ctrl): Voice Assistant Push-To-Talk (Hold to speak, release to process)
    - Right Alt: In-Place Voice Dictation (Transcribes and types into active window with safety check)
    """
    def __init__(self, hud: FloatingHUD):
        self.hud = hud
        # Left Alt as primary voice hotkey (and Right Ctrl as backup)
        self.ptt_keys = {
            keyboard.Key.alt_l,
            getattr(keyboard.Key, "alt", None),
            keyboard.Key.ctrl_r
        }
        self.dictation_key = keyboard.Key.alt_r
        self.ptt_pressed = False
        self.dictation_pressed = False
        self._listener = None

    def start(self):
        if not HAS_PYNPUT:
            print("[Warning] pynput not installed. Global hotkeys disabled; use on-screen PTT button.")
            return

        def on_press(key):
            try:
                # F8: Single key toggle (press to listen, press to finish)
                if key == keyboard.Key.f8:
                    self.hud.toggle_voice_capture_signal.emit()
                    return

                if key in self.ptt_keys and not self.ptt_pressed:
                    self.ptt_pressed = True
                    self.hud.ptt_pressed_signal.emit()
                elif key == self.dictation_key and not self.dictation_pressed:
                    self.dictation_pressed = True
                    self.hud.dictation_pressed_signal.emit()
            except Exception:
                pass

        def on_release(key):
            try:
                if key in self.ptt_keys and self.ptt_pressed:
                    self.ptt_pressed = False
                    self.hud.ptt_released_signal.emit()
                elif key == self.dictation_key and self.dictation_pressed:
                    self.dictation_pressed = False
                    self.hud.dictation_released_signal.emit()
            except Exception:
                pass

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()


def main():
    # Ensure stdout/stderr handles UTF-8 on Windows
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Enable High DPI scaling for modern 2K/4K displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("NexusAssistant")
    app.setQuitOnLastWindowClosed(False)

    # Initialize Database
    db = DatabaseManager()

    # Launch HUD
    hud = FloatingHUD(db=db)
    hud.show()
    hud.raise_()
    hud.activateWindow()

    # Launch Global Hotkey Listener
    hotkey_mgr = GlobalHotkeyManager(hud)
    hotkey_mgr.start()

    print("\n" + "=" * 65)
    print(" [NEXUS] AI Assistant (HeyNixi-Inspired Windows Assistant) STARTED")
    print(" - Interface: Floating HUD docked at screen top-center")
    print(" - Voice Push-To-Talk: Hold LEFT-ALT or RIGHT-CTRL (release to send)")
    print(" - Voice Toggle: Press F8 or click glowing Cyber Orb on the notch")
    print(" - In-Place Dictation: Hold RIGHT-ALT (types into active app with approval)")
    print(" - Chat Drawer: Click the arrow toggle on the pill")
    print(" - Safety Guard: Strict interactive approval required for desktop actions")
    print("=" * 65 + "\n")

    exit_code = app.exec()
    hotkey_mgr.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

