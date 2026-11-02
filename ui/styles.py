"""
Cyberpunk Futuristic Dark Theme Stylesheets (QSS)
Inspired by HeyNixi and Jarvis desktop aesthetics.
"""
from config import THEME

HUD_PILL_COMPACT_STYLE = f"""
    QWidget#MainCard {{
        background-color: #000000;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 22px;
    }}
    QWidget#MainCard:hover {{
        border: 1px solid rgba(255, 255, 255, 0.22);
    }}
"""

HUD_VOICE_HUD_STYLE = f"""
    QWidget#MainCard {{
        background-color: #000000;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 22px;
    }}
"""

VOICE_CMD_PILL_STYLE = """
    QLabel {
        background-color: rgba(26, 31, 40, 0.95);
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 14px;
    }
"""

UNIFIED_CARD_STYLE = f"""
    QWidget#MainCard {{
        background-color: #0A0C10;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
    }}
"""

SEGMENTED_TAB_CONTAINER_STYLE = """
    QWidget#SegmentedTabs {
        background-color: #141720;
        border-radius: 14px;
    }
"""

SEGMENTED_TAB_ACTIVE_STYLE = """
    QPushButton {
        background-color: #262B36;
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        padding: 4px 14px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 600;
    }
"""

SEGMENTED_TAB_INACTIVE_STYLE = """
    QPushButton {
        background-color: transparent;
        color: #717A8C;
        border: none;
        border-radius: 12px;
        padding: 4px 14px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton:hover {
        color: #CBD5E1;
    }
"""

TOP_ICON_BUTTON_STYLE = """
    QPushButton {
        background-color: transparent;
        color: #94A3B8;
        border: none;
        border-radius: 10px;
        font-size: 14px;
        padding: 4px 8px;
    }
    QPushButton:hover {
        background-color: #1E232F;
        color: #FFFFFF;
    }
"""

TOP_ICON_BUTTON_ACTIVE_STYLE = """
    QPushButton {
        background-color: #8B5CF6;
        color: #FFFFFF;
        border: none;
        border-radius: 10px;
        font-size: 14px;
        padding: 4px 8px;
        font-weight: bold;
    }
"""

CIRCULAR_SEND_BUTTON_STYLE = """
    QPushButton {
        background-color: #1877F2;
        color: #FFFFFF;
        border: none;
        border-radius: 18px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2D88FF;
    }
    QPushButton:pressed {
        background-color: #1565C0;
    }
"""

BOTTOM_INPUT_STYLE = """
    QLineEdit {
        background-color: #141720;
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 8px 16px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 13px;
    }
    QLineEdit:focus {
        border: 1px solid #1877F2;
    }
"""

CHAT_USER_BUBBLE_STYLE = """
    QFrame {
        background-color: #1A202C;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 8px 14px;
        margin-left: 50px;
    }
    QLabel {
        color: #FFFFFF;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 13px;
    }
"""

CHAT_AI_BUBBLE_STYLE = """
    QFrame {
        background-color: #12151D;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 8px 14px;
        margin-right: 50px;
    }
    QLabel {
        color: #E2E8F0;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 13px;
    }
"""

HUD_STATUS_LABEL_STYLE = f"""
    QLabel {{
        color: #94A3B8;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
"""

PTT_BUTTON_IDLE_STYLE = f"""
    QPushButton {{
        background-color: rgba(26, 31, 40, 0.85);
        color: #F8FAFC;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 13px;
        padding: 4px 12px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}
    QPushButton:hover {{
        background-color: rgba(38, 46, 58, 0.95);
        border: 1px solid #00F0FF;
        color: #00F0FF;
    }}
"""

PTT_BUTTON_RECORDING_STYLE = f"""
    QPushButton {{
        background-color: #8B5CF6;
        color: #FFFFFF;
        border: 1px solid #C084FC;
        border-radius: 13px;
        padding: 4px 12px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 11px;
        font-weight: bold;
    }}
"""

EXPAND_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: #94A3B8;
        border: none;
        font-size: 13px;
        font-weight: bold;
        padding: 2px 4px;
    }}
    QPushButton:hover {{
        color: #00F0FF;
    }}
"""

CHAT_DRAWER_STYLE = f"""
    QWidget#ChatDrawer {{
        background-color: {THEME['bg_dark']};
        border: 1px solid {THEME['border_glow']};
        border-radius: 16px;
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {THEME['border_dim']};
        border-radius: 3px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {THEME['cyan_accent']};
    }}
"""

INPUT_BOX_STYLE = f"""
    QLineEdit {{
        background-color: {THEME['bg_surface']};
        color: {THEME['text_primary']};
        border: 1px solid {THEME['border_dim']};
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border: 1px solid {THEME['cyan_accent']};
    }}
"""

SEND_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {THEME['cyan_accent']};
        color: #0B0D14;
        border: none;
        border-radius: 12px;
        font-weight: bold;
        padding: 8px 14px;
    }}
    QPushButton:hover {{
        background-color: #38BDF8;
    }}
"""

USER_BUBBLE_STYLE = f"""
    QFrame {{
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 8px 12px;
        margin-left: 40px;
    }}
    QLabel {{
        color: {THEME['text_primary']};
        font-size: 13px;
    }}
"""

AI_BUBBLE_STYLE = f"""
    QFrame {{
        background-color: #0F172A;
        border: 1px solid {THEME['border_glow']};
        border-radius: 12px;
        padding: 8px 12px;
        margin-right: 40px;
    }}
    QLabel {{
        color: {THEME['text_primary']};
        font-size: 13px;
    }}
"""

APPROVAL_CARD_STYLE = f"""
    QFrame#ApprovalCard {{
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid {THEME['warning_amber']};
        border-radius: 12px;
        padding: 10px;
        margin: 6px 0px;
    }}
"""

