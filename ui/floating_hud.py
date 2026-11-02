"""
Nexus Desktop Assistant - Unified HeyNixi-Style HUD & Window.
Clean-room implementation reverse-engineered from HeyNixi references:
- State 1: Compact Idle Notch (112px x 44px) - stadium pill with capsule eyes tracking cursor.
- State 2: VoiceHUD Recording Notch (146px x 96px) - activated by holding Left Alt / F8,
  features glowing eyes, "Command" pill badge, and pulsing 4-bar blue audio wave.
- State 3: Full Unified Window (440px x 480px) - continuous dark card with top mascot eyes,
  audio wave bars, Chat/History segmented pill, toolbar icons, message area, and
  bottom input bar with circular blue send button.
- Inactivity Sleep: Eyes close into gentle sleeping slits when cursor stops moving.
- Frequent Blinking: Natural lifelike eye squishes every 1.5 - 3.2s.
- Cyberpunk Headset: Strictly wears headset ONLY during actual music/song playback.
"""
import sys
import math
from typing import Optional, List
from PySide6.QtCore import Qt, QPoint, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QStackedWidget,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QPainter

from config import THEME
from database.db_manager import DatabaseManager
from audio.recorder import AudioRecorder
from audio.stt import SpeechToTextWorker
from audio.tts import TextToSpeechWorker
from llm.ollama_client import OllamaStreamWorker, OllamaClient
from automation.safety_guard import SafetyGuard, ProposedAction
from automation.command_router import CommandRouter
from ui.audio_visualizer import CyberMascotEyes, VisualizerState
from ui.styles import (
    HUD_PILL_COMPACT_STYLE, HUD_VOICE_HUD_STYLE, VOICE_CMD_PILL_STYLE, UNIFIED_CARD_STYLE,
    SEGMENTED_TAB_CONTAINER_STYLE, SEGMENTED_TAB_ACTIVE_STYLE, SEGMENTED_TAB_INACTIVE_STYLE,
    TOP_ICON_BUTTON_STYLE, TOP_ICON_BUTTON_ACTIVE_STYLE,
    BOTTOM_INPUT_STYLE, CIRCULAR_SEND_BUTTON_STYLE,
    CHAT_USER_BUBBLE_STYLE, CHAT_AI_BUBBLE_STYLE, APPROVAL_CARD_STYLE
)


class AudioBarsWidget(QWidget):
    """4-bar animated blue audio level indicator matching HeyNixi header."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 14)
        self.levels = [0.35, 0.75, 0.55, 0.30]
        self._target_levels = [0.35, 0.75, 0.55, 0.30]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_bars)
        self._timer.start(50)
        self._phase = 0.0

    def set_audio_level(self, rms: float):
        base = max(0.2, min(1.0, rms * 14.0))
        self._target_levels = [
            min(1.0, base * 0.7 + 0.15),
            min(1.0, base * 1.1 + 0.2),
            min(1.0, base * 0.9 + 0.25),
            min(1.0, base * 0.6 + 0.1)
        ]

    def _animate_bars(self):
        self._phase += 0.12
        for i in range(4):
            idle_offset = math.sin(self._phase + i * 0.8) * 0.12
            target = max(0.2, min(1.0, self._target_levels[i] + idle_offset))
            self.levels[i] += (target - self.levels[i]) * 0.3
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#1877F2'))
        for i, lvl in enumerate(self.levels):
            x = i * 5 + 1
            h = max(3.0, 12.0 * lvl)
            y = (14.0 - h) / 2.0
            p.drawRoundedRect(x, int(y), 3, int(h), 1.5, 1.5)


class FloatingHUD(QWidget):
    ptt_pressed_signal = Signal()
    ptt_released_signal = Signal()
    dictation_pressed_signal = Signal()
    dictation_released_signal = Signal()
    toggle_voice_capture_signal = Signal()
    music_state_signal = Signal(bool)

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.active_convo_id = self.db.get_or_create_active_conversation()
        self._is_dictation_mode = False
        self.mode = "compact"  # "compact" | "voice_hud" | "full_card"

        # Window flags: Top-level frameless, stays on top, translucent
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Core engines
        self.recorder = AudioRecorder()
        self.recorder.level_callback = self._on_audio_level
        self.ollama_client = OllamaClient()
        self.safety_guard = SafetyGuard(self.db, self)
        self.command_router = CommandRouter()

        # Workers tracking
        self._stt_worker: Optional[SpeechToTextWorker] = None
        self._llm_worker: Optional[OllamaStreamWorker] = None
        self._tts_worker: Optional[TextToSpeechWorker] = None
        self._active_stream_label: Optional[QLabel] = None

        # Dragging state
        self._drag_pos = QPoint()
        self._is_dragging = False

        self._init_ui()
        self._restore_position()
        self._connect_signals()

    def _init_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(0)
        self.root_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # --- THE MAIN CARD ---
        self.card = QWidget()
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet(HUD_PILL_COMPACT_STYLE)
        self.card.setFixedSize(112, 44)

        # Ambient drop shadow
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 3)
        self.card.setGraphicsEffect(shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)

        # 1. Top Notch (Capsule Eyes)
        self.notch_container = QWidget()
        notch_layout = QHBoxLayout(self.notch_container)
        notch_layout.setContentsMargins(0, 0, 0, 0)
        notch_layout.setAlignment(Qt.AlignCenter)

        self.orb = CyberMascotEyes(width=112, height=44)
        notch_layout.addWidget(self.orb)
        self.card_layout.addWidget(self.notch_container)

        # 2. Voice HUD Recording Container (shown during Left Alt / F8 PTT)
        self.voice_hud_container = QWidget()
        voice_hud_layout = QVBoxLayout(self.voice_hud_container)
        voice_hud_layout.setContentsMargins(10, 4, 10, 8)
        voice_hud_layout.setSpacing(6)
        voice_hud_layout.setAlignment(Qt.AlignHCenter)

        # Centered "Command" pill
        self.voice_cmd_pill = QLabel("Command")
        self.voice_cmd_pill.setFixedHeight(24)
        self.voice_cmd_pill.setAlignment(Qt.AlignCenter)
        self.voice_cmd_pill.setStyleSheet(VOICE_CMD_PILL_STYLE)
        voice_hud_layout.addWidget(self.voice_cmd_pill)

        # Bottom row: animated blue bars on left, red REC dot on right
        voice_bot = QHBoxLayout()
        voice_bot.setContentsMargins(4, 0, 4, 0)
        self.voice_bars = AudioBarsWidget()
        voice_bot.addWidget(self.voice_bars)
        voice_bot.addStretch()

        self.voice_rec_label = QLabel("● REC")
        self.voice_rec_label.setStyleSheet("color: #EF4444; font-size: 10px; font-weight: bold;")
        voice_bot.addWidget(self.voice_rec_label)

        voice_hud_layout.addLayout(voice_bot)
        self.voice_hud_container.hide()
        self.card_layout.addWidget(self.voice_hud_container)

        # 3. Full Expanded Card Container (shown when clicking notch or chat)
        self.expanded_container = QWidget()
        expanded_layout = QVBoxLayout(self.expanded_container)
        expanded_layout.setContentsMargins(14, 0, 14, 14)
        expanded_layout.setSpacing(10)

        # --- TOP TOOLBAR ---
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 4, 0, 4)
        toolbar.setSpacing(8)

        # Audio Bars
        self.audio_bars = AudioBarsWidget()
        toolbar.addWidget(self.audio_bars)

        # Segmented Tabs [Chat] [History]
        self.tab_container = QWidget()
        self.tab_container.setObjectName("SegmentedTabs")
        self.tab_container.setStyleSheet(SEGMENTED_TAB_CONTAINER_STYLE)
        tab_layout = QHBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(2, 2, 2, 2)
        tab_layout.setSpacing(2)

        self.chat_tab_btn = QPushButton("Chat")
        self.chat_tab_btn.setStyleSheet(SEGMENTED_TAB_ACTIVE_STYLE)
        self.chat_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        tab_layout.addWidget(self.chat_tab_btn)

        self.history_tab_btn = QPushButton("History")
        self.history_tab_btn.setStyleSheet(SEGMENTED_TAB_INACTIVE_STYLE)
        self.history_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        tab_layout.addWidget(self.history_tab_btn)

        toolbar.addWidget(self.tab_container)
        toolbar.addStretch()

        # Right Action Icons: Mode ↖, Mic 🎙️, Clear ✏️, Collapse ⌃
        self.mode_btn = QPushButton("↖")
        self.mode_btn.setStyleSheet(TOP_ICON_BUTTON_STYLE)
        self.mode_btn.setToolTip("Pointer / Agent Mode")
        toolbar.addWidget(self.mode_btn)

        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setStyleSheet(TOP_ICON_BUTTON_STYLE)
        self.mic_btn.setToolTip("Toggle Voice Command (F8 or Left Alt)")
        self.mic_btn.clicked.connect(self.toggle_voice_capture)
        toolbar.addWidget(self.mic_btn)

        self.new_chat_btn = QPushButton("✏️")
        self.new_chat_btn.setStyleSheet(TOP_ICON_BUTTON_STYLE)
        self.new_chat_btn.setToolTip("Start New Conversation")
        self.new_chat_btn.clicked.connect(self.start_new_conversation)
        toolbar.addWidget(self.new_chat_btn)

        self.collapse_btn = QPushButton("⌃")
        self.collapse_btn.setStyleSheet(TOP_ICON_BUTTON_STYLE)
        self.collapse_btn.setToolTip("Collapse to Compact Notch")
        self.collapse_btn.clicked.connect(self.show_compact_notch)
        toolbar.addWidget(self.collapse_btn)

        expanded_layout.addLayout(toolbar)

        # --- STACKED WIDGET (CHAT VS HISTORY) ---
        self.stacked_widget = QStackedWidget()

        # Page 0: Chat View
        self.chat_page = QWidget()
        chat_layout = QVBoxLayout(self.chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(6)

        # Safety Approval Card Container
        self.approval_container = QWidget()
        self.approval_layout = QVBoxLayout(self.approval_container)
        self.approval_layout.setContentsMargins(0, 0, 0, 0)
        self.approval_container.hide()
        chat_layout.addWidget(self.approval_container)

        # Message Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(10)

        # Centered placeholder text matching HeyNixi
        self.empty_label = QLabel("Say something, or type below")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #525A6B; font-size: 13px; font-family: 'Segoe UI', sans-serif;")
        self.messages_layout.addStretch()
        self.messages_layout.addWidget(self.empty_label)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        chat_layout.addWidget(self.scroll_area)
        self.stacked_widget.addWidget(self.chat_page)

        # Page 1: History View
        self.history_page = QWidget()
        history_layout = QVBoxLayout(self.history_page)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(6)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.history_container = QWidget()
        self.history_list_layout = QVBoxLayout(self.history_container)
        self.history_list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list_layout.setSpacing(6)
        self.history_scroll.setWidget(self.history_container)

        history_layout.addWidget(self.history_scroll)
        self.stacked_widget.addWidget(self.history_page)

        expanded_layout.addWidget(self.stacked_widget)

        # --- BOTTOM INPUT BAR ---
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 2, 0, 0)
        input_row.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Nixi...")
        self.input_field.setStyleSheet(BOTTOM_INPUT_STYLE)
        self.input_field.setFixedHeight(40)
        self.input_field.returnPressed.connect(self._on_input_submitted)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("↑")
        self.send_btn.setStyleSheet(CIRCULAR_SEND_BUTTON_STYLE)
        self.send_btn.setFixedSize(38, 38)
        self.send_btn.clicked.connect(self._on_input_submitted)
        input_row.addWidget(self.send_btn)

        expanded_layout.addLayout(input_row)

        self.expanded_container.hide()
        self.card_layout.addWidget(self.expanded_container)
        self.root_layout.addWidget(self.card)

    def _connect_signals(self):
        # Hotkey bridge signals
        self.ptt_pressed_signal.connect(self.start_voice_capture)
        self.ptt_released_signal.connect(self.stop_voice_capture)
        self.toggle_voice_capture_signal.connect(self.toggle_voice_capture)
        self.dictation_pressed_signal.connect(self.start_dictation_capture)
        self.dictation_released_signal.connect(self.stop_dictation_capture)
        self.music_state_signal.connect(self.set_music_mode)

        # Clicking mascot orb in compact mode opens the card
        self.orb.clicked.connect(self._on_orb_clicked)

        # Safety Guard signals
        self.safety_guard.action_requested.connect(self._on_action_requested)
        self.safety_guard.action_executed.connect(lambda msg: self.set_status(msg, VisualizerState.IDLE))
        self.safety_guard.action_rejected.connect(lambda msg: self.set_status(msg, VisualizerState.ERROR))

    def _on_orb_clicked(self):
        if self.mode == "compact":
            self.show_full_card()
        elif self.mode == "voice_hud":
            self.show_compact_notch()
        else:
            self.toggle_voice_capture()

    def _on_audio_level(self, rms: float):
        self.orb.set_audio_level(rms)
        self.voice_bars.set_audio_level(rms)
        self.audio_bars.set_audio_level(rms)

    # --- THREE DYNAMIC MORPHING STATES ---
    def show_compact_notch(self):
        """State 1: Collapses back to the 112px x 44px compact mascot notch."""
        if self.mode == "compact":
            return

        target_w = 112
        target_h = 44
        dx = (target_w - self.card.width()) // 2
        new_x = self.x() - dx
        new_y = self.y()

        self.voice_hud_container.hide()
        self.expanded_container.hide()
        self.card.setStyleSheet(HUD_PILL_COMPACT_STYLE)
        self.card.setFixedSize(target_w, target_h)
        self.orb.setFixedSize(target_w, target_h)
        self.mode = "compact"

        self.move(new_x, new_y)
        self.adjustSize()
        self.update()

    def show_voice_hud(self):
        """State 2: The exact VoiceHUD Recording Notch shown in the video."""
        if self.mode == "voice_hud":
            return

        target_w = 146
        target_h = 96
        dx = (target_w - self.card.width()) // 2
        new_x = self.x() - dx
        new_y = self.y()

        self.expanded_container.hide()
        self.card.setStyleSheet(HUD_VOICE_HUD_STYLE)
        self.card.setFixedSize(target_w, target_h)
        self.orb.setFixedSize(92, 34)

        self.voice_cmd_pill.setText("Command")
        self.voice_hud_container.show()
        self.mode = "voice_hud"

        self.move(new_x, new_y)
        self.adjustSize()
        self.update()

    def show_full_card(self):
        """State 3: Expands into the full 440px x 480px Unified Chat Card."""
        if self.mode == "full_card":
            return

        target_w = 440
        target_h = 480
        dx = (target_w - self.card.width()) // 2
        new_x = self.x() - dx
        new_y = self.y()

        self.voice_hud_container.hide()
        self.card.setStyleSheet(UNIFIED_CARD_STYLE)
        self.card.setFixedSize(target_w, target_h)
        self.orb.setFixedSize(90, 34)

        self.expanded_container.show()
        self.input_field.setFocus()
        self.mode = "full_card"

        self.move(new_x, new_y)
        self.adjustSize()
        self.update()

    # --- TABS: CHAT VS HISTORY ---
    def _switch_tab(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        if index == 0:
            self.chat_tab_btn.setStyleSheet(SEGMENTED_TAB_ACTIVE_STYLE)
            self.history_tab_btn.setStyleSheet(SEGMENTED_TAB_INACTIVE_STYLE)
        else:
            self.chat_tab_btn.setStyleSheet(SEGMENTED_TAB_INACTIVE_STYLE)
            self.history_tab_btn.setStyleSheet(SEGMENTED_TAB_ACTIVE_STYLE)
            self._load_history_list()

    def start_new_conversation(self):
        self.active_convo_id = self.db.get_or_create_active_conversation()
        for i in reversed(range(self.messages_layout.count())):
            item = self.messages_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()
        self.empty_label.show()
        self._switch_tab(0)

    def _load_history_list(self):
        for i in reversed(range(self.history_list_layout.count())):
            item = self.history_list_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        convos = self.db.get_recent_conversations(limit=15)
        if not convos:
            empty = QLabel("No previous conversations")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #525A6B; font-size: 13px; padding: 20px;")
            self.history_list_layout.addWidget(empty)
            return

        for c in convos:
            cid = c["id"]
            title = c["title"] or f"Conversation {cid}"
            created = c["created_at"][:16].replace("T", " ")
            btn = QPushButton(f"💬 {title}\n    {created}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #141720;
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 10px;
                    padding: 8px 12px;
                    text-align: left;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1E232F;
                    border: 1px solid #1877F2;
                }
            """)
            btn.clicked.connect(lambda _, conv_id=cid: self._resume_conversation(conv_id))
            self.history_list_layout.addWidget(btn)

        self.history_list_layout.addStretch()

    def _resume_conversation(self, convo_id: int):
        self.active_convo_id = convo_id
        for i in reversed(range(self.messages_layout.count())):
            item = self.messages_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

        msgs = self.db.get_recent_messages(convo_id, limit=30)
        if msgs:
            self.empty_label.hide()
            for m in msgs:
                if m["role"] == "user":
                    self.add_user_message(m["content"])
                else:
                    self.add_ai_message(m["content"])
        else:
            self.empty_label.show()

        self._switch_tab(0)

    # --- TEXT INPUT & DISPATCH ---
    def _on_input_submitted(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self._process_user_prompt(text)

    # --- VOICE CAPTURE WITH VOICE HUD ANIMATION ---
    @Slot()
    def toggle_voice_capture(self):
        if self.recorder.is_recording:
            self.stop_voice_capture()
        else:
            self.start_voice_capture()

    @Slot()
    def start_voice_capture(self):
        self._is_dictation_mode = False
        if self.mode != "full_card":
            self.show_voice_hud()
        self._begin_audio_recording("LISTENING...")

    @Slot()
    def stop_voice_capture(self):
        self._finish_audio_recording()

    @Slot()
    def start_dictation_capture(self):
        self._is_dictation_mode = True
        if self.mode != "full_card":
            self.show_voice_hud()
        self._begin_audio_recording("DICTATING...")

    @Slot()
    def stop_dictation_capture(self):
        self._finish_audio_recording()

    def _begin_audio_recording(self, status_msg: str):
        if self.recorder.is_recording:
            return
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.terminate()

        try:
            self.recorder.start_recording()
            self.orb.set_state(VisualizerState.LISTENING)
            if self.mode == "voice_hud":
                self.voice_cmd_pill.setText("Command")
                self.voice_rec_label.setText("● REC")
            self.mic_btn.setStyleSheet(TOP_ICON_BUTTON_ACTIVE_STYLE)
        except Exception as e:
            self.set_status(f"Mic Error: {e}", VisualizerState.ERROR)

    def _finish_audio_recording(self):
        if not self.recorder.is_recording:
            return

        self.mic_btn.setStyleSheet(TOP_ICON_BUTTON_STYLE)
        audio_data = self.recorder.stop_recording()

        if len(audio_data) < 16000 * 0.2:
            self.set_status("IDLE", VisualizerState.IDLE)
            if self.mode == "voice_hud":
                self.show_compact_notch()
            return

        if self.mode == "voice_hud":
            self.voice_cmd_pill.setText("Transcribing...")
            self.voice_rec_label.setText("● WAIT")

        self.set_status("TRANSCRIBING...", VisualizerState.PROCESSING)
        self._stt_worker = SpeechToTextWorker(audio_data)
        self._stt_worker.transcription_finished.connect(self._on_transcription_finished)
        self._stt_worker.transcription_error.connect(lambda err: self.set_status(err, VisualizerState.ERROR))
        self._stt_worker.start()

    @Slot(str)
    def _on_transcription_finished(self, text: str):
        cleaned = text.strip()
        if not cleaned:
            self.set_status("NO SPEECH DETECTED", VisualizerState.IDLE)
            if self.mode == "voice_hud":
                QTimer.singleShot(600, self.show_compact_notch)
            return

        if self._is_dictation_mode:
            action = ProposedAction(
                action_type="type_text",
                description="Type text into active window",
                payload=cleaned,
                risk_level="low"
            )
            self.safety_guard.request_action(action)
            if self.mode == "voice_hud":
                QTimer.singleShot(800, self.show_compact_notch)
        else:
            if self.mode == "voice_hud":
                self.voice_cmd_pill.setText(cleaned[:20])
            self._process_user_prompt(cleaned)

    # --- CHAT MESSAGES DISPLAY ---
    def add_user_message(self, text: str):
        self.empty_label.hide()
        bubble = QFrame()
        bubble.setStyleSheet(CHAT_USER_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(lbl)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(bubble)
        self.messages_layout.addLayout(row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def add_ai_message(self, text: str):
        self.empty_label.hide()
        bubble = QFrame()
        bubble.setStyleSheet(CHAT_AI_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(lbl)

        row = QHBoxLayout()
        row.addWidget(bubble)
        row.addStretch()
        self.messages_layout.addLayout(row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def start_streaming_ai_message(self):
        self.empty_label.hide()
        bubble = QFrame()
        bubble.setStyleSheet(CHAT_AI_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(12, 8, 12, 8)

        self._active_stream_label = QLabel("Thinking...")
        self._active_stream_label.setWordWrap(True)
        self._active_stream_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(self._active_stream_label)

        row = QHBoxLayout()
        row.addWidget(bubble)
        row.addStretch()
        self.messages_layout.addLayout(row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    @Slot(str)
    def append_streaming_chunk(self, chunk: str):
        if self._active_stream_label:
            cur = self._active_stream_label.text()
            if cur == "Thinking...":
                cur = ""
            self._active_stream_label.setText(cur + chunk)
            self._scroll_to_bottom()

    def finish_streaming_ai_message(self, full_text: str):
        if self._active_stream_label:
            self._active_stream_label.setText(full_text)
            self._active_stream_label = None
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    # --- PROMPT PROCESSING & STRICT HEADSET CONTROLS ---
    def _process_user_prompt(self, user_text: str):
        self.add_user_message(user_text)
        self.db.add_message(self.active_convo_id, "user", user_text)

        lower_prompt = user_text.lower().strip()

        # Explicit Headset voice toggles
        if any(h in lower_prompt for h in ["headset on", "wear headset", "put on headset", "wear headphones"]):
            self.set_music_mode(True)
            self.add_ai_message("Cyberpunk headset equipped!")
            return
        elif any(h in lower_prompt for h in ["headset off", "remove headset", "take off headset", "remove headphones"]):
            self.set_music_mode(False)
            self.add_ai_message("Cyberpunk headset removed.")
            return

        # Deterministic Command Router FIRST
        cmd_result = self.command_router.route(user_text)
        if cmd_result.is_command:
            # STRICT HEADSET CONTROL:
            # ONLY activate headset if action_type is STRICTLY play_youtube or play_spotify!
            # Never activate headset for regular app/website launches like "Open YouTube"!
            is_media = False
            if cmd_result.action and cmd_result.action.action_type in ("play_youtube", "play_spotify"):
                is_media = True
            if cmd_result.steps and any(s.action_type in ("play_youtube", "play_spotify") for s in cmd_result.steps):
                is_media = True

            if is_media:
                self.set_music_mode(True)
            else:
                self.set_music_mode(False)

            self.add_ai_message(cmd_result.display_response)
            self.db.add_message(self.active_convo_id, "assistant", cmd_result.spoken_response)

            if cmd_result.steps:
                self._execute_plan_steps(cmd_result.steps)
            elif cmd_result.auto_execute and cmd_result.action:
                self.safety_guard.pending_action = cmd_result.action
                self.safety_guard.authorize_action()

            if cmd_result.spoken_response:
                self.set_status("SPEAKING...", VisualizerState.SPEAKING)
                self._tts_worker = TextToSpeechWorker(cmd_result.spoken_response)
                self._tts_worker.speech_finished.connect(self._on_speech_finished)
                self._tts_worker.start()
            else:
                self.set_status("IDLE", VisualizerState.IDLE)
                if self.mode == "voice_hud":
                    QTimer.singleShot(1500, self.show_compact_notch)
            return

        # Local Ollama LLM
        self.set_music_mode(False)
        # If in voice_hud mode and conversational, expand to full card so user can read streaming response
        if self.mode == "voice_hud":
            self.show_full_card()

        self.set_status("THINKING...", VisualizerState.PROCESSING)
        self.start_streaming_ai_message()

        history = self.db.get_recent_messages_for_llm(self.active_convo_id, limit=8)
        self._llm_worker = OllamaStreamWorker(user_prompt=user_text, history=history)
        self._llm_worker.chunk_received.connect(self.append_streaming_chunk)
        self._llm_worker.generation_finished.connect(self._on_generation_finished)
        self._llm_worker.generation_error.connect(self._on_generation_error)
        self._llm_worker.start()

    def _on_speech_finished(self):
        self.set_status("IDLE", VisualizerState.IDLE)
        if self.mode == "voice_hud":
            QTimer.singleShot(1800, self.show_compact_notch)

    def _execute_plan_steps(self, steps):
        import threading
        import time

        def worker():
            for idx, step in enumerate(steps, start=1):
                if step.action_type in ("play_youtube", "play_spotify"):
                    self.music_state_signal.emit(True)

                if step.action_type == "wait":
                    try:
                        time.sleep(float(step.payload))
                    except Exception:
                        time.sleep(1.0)
                    continue

                action = ProposedAction(
                    action_type=step.action_type,
                    description=step.description,
                    payload=step.payload,
                    risk_level="high" if step.requires_approval else "low"
                )

                if step.requires_approval:
                    self.safety_guard.request_action(action)
                    break
                else:
                    self.safety_guard.pending_action = action
                    self.safety_guard.authorize_action()
                    time.sleep(0.6)

            self.set_status("IDLE", VisualizerState.IDLE)
            if self.mode == "voice_hud":
                QTimer.singleShot(1800, self.show_compact_notch)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def _on_generation_finished(self, full_response: str):
        self.finish_streaming_ai_message(full_response)
        self.db.add_message(self.active_convo_id, "assistant", full_response)

        self.set_status("SPEAKING...", VisualizerState.SPEAKING)
        self._tts_worker = TextToSpeechWorker(full_response)
        self._tts_worker.speech_finished.connect(self._on_speech_finished)
        self._tts_worker.speech_error.connect(lambda err: self.set_status("TTS Error", VisualizerState.IDLE))
        self._tts_worker.start()

    @Slot(str)
    def _on_generation_error(self, err_msg: str):
        self.finish_streaming_ai_message(f"⚠️ {err_msg}")
        self.set_status("LLM ERROR", VisualizerState.ERROR)

    # --- SAFETY APPROVAL CARDS ---
    def _on_action_requested(self, action: ProposedAction):
        self.show_full_card()
        for i in reversed(range(self.approval_layout.count())):
            item = self.approval_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        card = QFrame()
        card.setStyleSheet(APPROVAL_CARD_STYLE)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        warn_lbl = QLabel(f"⚠️ Action Authorization: {action.description}")
        warn_lbl.setStyleSheet("color: #FACC15; font-weight: bold; font-size: 12px;")
        card_layout.addWidget(warn_lbl)

        btn_row = QHBoxLayout()
        auth_btn = QPushButton("Authorize")
        auth_btn.setStyleSheet("background-color: #10B981; color: white; border-radius: 8px; padding: 6px 14px; font-weight: bold;")
        auth_btn.clicked.connect(lambda: [card.deleteLater(), self.approval_container.hide(), self.safety_guard.authorize_action()])

        rej_btn = QPushButton("Reject")
        rej_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 8px; padding: 6px 14px; font-weight: bold;")
        rej_btn.clicked.connect(lambda: [card.deleteLater(), self.approval_container.hide(), self.safety_guard.reject_action()])

        btn_row.addWidget(auth_btn)
        btn_row.addWidget(rej_btn)
        card_layout.addLayout(btn_row)

        self.approval_layout.addWidget(card)
        self.approval_container.show()

    # --- UI HELPERS ---
    def set_status(self, text: str, state: VisualizerState):
        self.orb.set_state(state)

    @Slot(bool)
    def set_music_mode(self, playing: bool):
        self.orb.set_music_playing(playing)

    # --- DRAGGING & PERSISTENCE ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            pos = self.pos()
            self.db.set_setting("hud_pos", f"{pos.x()},{pos.y()}")
            event.accept()

    def _restore_position(self):
        saved = self.db.get_setting("hud_pos")
        if saved:
            try:
                x_str, y_str = saved.split(",")
                self.move(int(x_str), int(y_str))
                return
            except Exception:
                pass

        # Default: Top-center of primary screen for the 112px compact notch
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 112) // 2
        y = 30
        self.move(x, y)
