"""
Futuristic Collapsible Chat Drawer & Safety Confirmation Widget.
Provides rich conversation history, live streaming text bubbles, and safety approval cards.
"""
from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QLineEdit, QPushButton, QFrame
)
from automation.safety_guard import ProposedAction
from ui.styles import (
    CHAT_DRAWER_STYLE, INPUT_BOX_STYLE, SEND_BUTTON_STYLE,
    USER_BUBBLE_STYLE, AI_BUBBLE_STYLE, APPROVAL_CARD_STYLE
)
from config import OLLAMA_MODEL, THEME


class ChatDrawer(QWidget):
    message_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatDrawer")
        self.setStyleSheet(CHAT_DRAWER_STYLE)
        self.setFixedWidth(380)
        self.setFixedHeight(480)

        self._active_stream_label: Optional[QLabel] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("NEXUS CHAT")
        title_label.setStyleSheet(f"color: {THEME['cyan_accent']}; font-weight: bold; font-size: 13px; letter-spacing: 1px;")

        self.model_badge = QLabel(f"• {OLLAMA_MODEL}")
        self.model_badge.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.model_badge)
        layout.addLayout(header_layout)

        # Approval Card Container
        self.approval_container = QWidget()
        self.approval_layout = QVBoxLayout(self.approval_container)
        self.approval_layout.setContentsMargins(0, 0, 0, 0)
        self.approval_container.hide()
        layout.addWidget(self.approval_container)

        # Message History Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

        # Bottom Input Box
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a prompt or hold Left Alt...")
        self.input_field.setStyleSheet(INPUT_BOX_STYLE)
        self.input_field.returnPressed.connect(self._on_send)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(SEND_BUTTON_STYLE)
        self.send_btn.clicked.connect(self._on_send)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.message_submitted.emit(text)

    def add_user_message(self, text: str):
        bubble = QFrame()
        bubble.setStyleSheet(USER_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(10, 8, 10, 8)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(lbl)

        # Insert before bottom stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_ai_message(self, text: str):
        bubble = QFrame()
        bubble.setStyleSheet(AI_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(10, 8, 10, 8)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(lbl)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def start_streaming_ai_message(self) -> QLabel:
        bubble = QFrame()
        bubble.setStyleSheet(AI_BUBBLE_STYLE)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(10, 8, 10, 8)

        lbl = QLabel("...")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_layout.addWidget(lbl)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._active_stream_label = lbl
        self._scroll_to_bottom()
        return lbl

    def append_streaming_chunk(self, token: str):
        if self._active_stream_label:
            current = self._active_stream_label.text()
            if current == "...":
                current = ""
            self._active_stream_label.setText(current + token)
            self._scroll_to_bottom()

    def finish_streaming_ai_message(self, full_text: str):
        if self._active_stream_label:
            self._active_stream_label.setText(full_text)
            self._active_stream_label = None
            self._scroll_to_bottom()

    def show_approval_request(
        self,
        action: ProposedAction,
        on_approve: Callable[[], None],
        on_reject: Callable[[], None]
    ):
        """Displays an explicit security card requiring user authorization."""
        # Clear any existing approval cards
        for i in reversed(range(self.approval_layout.count())):
            widget = self.approval_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        card = QFrame()
        card.setObjectName("ApprovalCard")
        card.setStyleSheet(APPROVAL_CARD_STYLE)
        card_layout = QVBoxLayout(card)

        title = QLabel("⚠️ SYSTEM ACTION APPROVAL REQUIRED")
        title.setStyleSheet(f"color: {THEME['warning_amber']}; font-weight: bold; font-size: 11px;")

        desc = QLabel(f"<b>Intent:</b> {action.description}<br><b>Payload:</b> <code>{action.payload}</code>")
        desc.setStyleSheet(f"color: {THEME['text_primary']}; font-size: 12px;")
        desc.setWordWrap(True)

        btn_row = QHBoxLayout()
        approve_btn = QPushButton("Authorize")
        approve_btn.setStyleSheet(f"background-color: {THEME['emerald_accent']}; color: #000; font-weight: bold; border-radius: 8px; padding: 6px;")
        
        reject_btn = QPushButton("Block")
        reject_btn.setStyleSheet(f"background-color: {THEME['danger_red']}; color: #FFF; font-weight: bold; border-radius: 8px; padding: 6px;")

        def _handle_approve():
            self.approval_container.hide()
            on_approve()

        def _handle_reject():
            self.approval_container.hide()
            on_reject()

        approve_btn.clicked.connect(_handle_approve)
        reject_btn.clicked.connect(_handle_reject)

        btn_row.addWidget(reject_btn)
        btn_row.addWidget(approve_btn)

        card_layout.addWidget(title)
        card_layout.addWidget(desc)
        card_layout.addLayout(btn_row)

        self.approval_layout.addWidget(card)
        self.approval_container.show()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
