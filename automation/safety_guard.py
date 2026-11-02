"""
Desktop Automation Safety Guardrail.
Enforces the mandatory requirement:
'Do not execute computer-control actions without explicit user approval.'
Every action must be intercepted, displayed to the user for confirmation, and audited.
"""
from dataclasses import dataclass
from typing import Callable, Optional
from PySide6.QtCore import QObject, Signal
from database.db_manager import DatabaseManager

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class ProposedAction:
    action_type: str        # e.g., 'type_text', 'press_key', 'open_app', 'click_coordinate'
    description: str        # Human-readable prompt, e.g. "Type text into current window"
    payload: str            # Action data (e.g., text content, path, key combination)
    risk_level: str = "medium" # 'low', 'medium', 'high'


class SafetyGuard(QObject):
    action_requested = Signal(ProposedAction)
    action_executed = Signal(str)
    action_rejected = Signal(str)

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.pending_action: Optional[ProposedAction] = None

    def request_action(self, action: ProposedAction):
        """Queue action and request user authorization on the HUD."""
        self.pending_action = action
        self.action_requested.emit(action)

    def authorize_action(self) -> bool:
        """Called only when the user explicitly clicks 'Authorize' on the UI."""
        if not self.pending_action:
            return False

        action = self.pending_action
        self.pending_action = None

        success = self._execute_safe(action)
        self.db.log_action_request(
            action_type=action.action_type,
            payload=action.payload,
            approved=True,
            executed=success
        )

        if success:
            self.action_executed.emit(f"Executed: {action.description}")
        return success

    def reject_action(self):
        """Called when the user clicks 'Reject' or closes the approval prompt."""
        if not self.pending_action:
            return

        action = self.pending_action
        self.pending_action = None

        self.db.log_action_request(
            action_type=action.action_type,
            payload=action.payload,
            approved=False,
            executed=False
        )
        self.action_rejected.emit(f"Blocked: {action.description}")

    def _execute_safe(self, action: ProposedAction) -> bool:
        """Internal execution with AppLauncher, MediaPlayer, PyAutoGUI, or OS calls."""
        try:
            if action.action_type == "play_youtube":
                from automation.media_player import MediaPlayer
                success, _, _ = MediaPlayer.play_youtube(action.payload)
                return success
            elif action.action_type == "play_spotify":
                from automation.media_player import MediaPlayer
                success, _, _ = MediaPlayer.play_spotify(action.payload)
                return success
            elif action.action_type == "open_app":
                from automation.app_launcher import AppLauncher
                success, msg = AppLauncher().launch(action.payload)
                return success
            elif action.action_type == "open_url":
                import webbrowser
                webbrowser.open(action.payload)
                return True
            elif action.action_type == "type_text" and HAS_PYAUTOGUI:
                pyautogui.write(action.payload, interval=0.01)
                return True
            elif action.action_type in ("press_key", "pause_music") and HAS_PYAUTOGUI:
                pyautogui.press(action.payload)
                return True
            elif action.action_type in ("headset_on", "headset_off"):
                return True
            elif action.action_type == "hotkey" and HAS_PYAUTOGUI:
                keys = [k.strip() for k in action.payload.split("+")]
                pyautogui.hotkey(*keys)
                return True
            return False
        except Exception as e:
            print(f"SafetyGuard execution error: {e}")
            return False

