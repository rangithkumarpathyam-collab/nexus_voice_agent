"""
Futuristic Cyberpunk Mascot Face, Eye Tracking & Visualizer.
Inspired by HeyNixi:
- Dual white capsule eyes that track the mouse cursor across the screen (MouseLook).
- Natural lifelike blinking every 3-5 seconds.
- Wearable cyberpunk audio headset with pulsing beat rings when music plays.
- Expressive audio-reactive moods for listening, thinking, speaking, and errors.
"""
from enum import Enum
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QCursor
from PySide6.QtWidgets import QWidget
from config import THEME


class VisualizerState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class CyberMascotEyes(QWidget):
    clicked = Signal()
    proximity_changed = Signal(float, float)  # (proximity_intensity, hover_intensity)

    def __init__(self, width: int = 90, height: int = 40, size: int = None, parent=None):
        if size is not None:
            width = max(90, size * 2)
            height = max(40, size)
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self.state = VisualizerState.IDLE
        self.audio_level = 0.0

        # Gaze tracking (MouseLook)
        self.look_x = 0.0
        self.look_y = 0.0
        self.target_look_x = 0.0
        self.target_look_y = 0.0

        # Cursor Proximity & Smooth Hover Animation
        self.proximity_intensity = 0.0  # 0.0 (far) to 1.0 (approaching within radius)
        self.hover_intensity = 0.0      # 0.0 (not over) to 1.0 (cursor directly over notch)
        self.hover_bounce = 0.0         # Elastic entry bounce (1.0 down to 0.0)
        self.hover_phase = 0.0          # Organic breathing wave while hovering
        self._is_cursor_hovering = False

        # Inactivity Sleep State
        self._last_cursor_pos = None
        self._idle_ticks = 0
        self.is_sleeping = False
        self.sleep_progress = 0.0  # 0.0 = wide awake, 1.0 = asleep
        self.sleep_phase = 0.0

        # Blinking animation (frequent intervals)
        self.blink_progress = 0.0
        self.is_blinking = False
        self._next_blink_tick = 60
        self._tick_counter = 0

        # Headset & Music bobbing
        self.is_playing_music = False
        self.headset_anim_progress = 0.0  # 0.0 (off) to 1.0 (fully worn)
        self.music_bob_phase = 0.0
        self.pulse_phase = 0.0

        # Animation timer (approx 50 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(20)

    def enterEvent(self, event):
        self._is_cursor_hovering = True
        self.hover_bounce = 1.0  # Trigger smooth responsive spring bounce!
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_cursor_hovering = False
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._is_dragging = False
            hud = self.window()
            if hud:
                hud._drag_pos = event.globalPosition().toPoint() - hud.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            # Right-click toggles cyberpunk headset for instant preview!
            self.set_music_playing(not self.is_playing_music)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, '_press_pos'):
            delta = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if delta > 4:
                self._is_dragging = True
                hud = self.window()
                if hud and hasattr(hud, '_drag_pos'):
                    hud.move(event.globalPosition().toPoint() - hud._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            hud = self.window()
            if getattr(self, '_is_dragging', False):
                self._is_dragging = False
                if hud and hasattr(hud, 'db'):
                    pos = hud.pos()
                    hud.db.set_setting("hud_pos", f"{pos.x()},{pos.y()}")
            else:
                self.clicked.emit()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            hud = self.window()
            if hud and hasattr(hud, 'toggle_drawer'):
                hud.toggle_drawer()
            event.accept()

    def set_state(self, state: VisualizerState):
        self.state = state
        self.update()

    def set_music_playing(self, playing: bool):
        """Puts on cyberpunk headset and dances when music plays."""
        self.is_playing_music = playing
        self.update()

    def set_audio_level(self, level: float):
        """Called with RMS level from microphone thread."""
        clamped = max(0.0, min(1.0, level * 16.0))
        self.audio_level = self.audio_level * 0.6 + clamped * 0.4

    def _animate(self):
        self.pulse_phase = (self.pulse_phase + 0.08) % (math.pi * 2)
        self._tick_counter += 1

        target_proximity = 0.0
        target_hover = 0.0

        # 1. Real-Time Cursor Tracking, Proximity & Inactivity Sleep Detection
        try:
            cursor_pos = QCursor.pos()
            if self._last_cursor_pos is None:
                self._last_cursor_pos = cursor_pos

            delta = (cursor_pos - self._last_cursor_pos).manhattanLength()
            if delta > 2:
                # Cursor moved -> wake up immediately!
                self._last_cursor_pos = cursor_pos
                self._idle_ticks = 0
                self.is_sleeping = False
            else:
                self._idle_ticks += 1
                # If cursor hasn't moved for ~3.5 seconds (175 ticks at 50 FPS):
                if self._idle_ticks > 175:
                    self.is_sleeping = True

            center_global = self.mapToGlobal(self.rect().center())
            dx = cursor_pos.x() - center_global.x()
            dy = cursor_pos.y() - center_global.y()
            dist = math.hypot(dx, dy)

            # Check if cursor is directly hovering over or inside the widget bounds
            local_pos = self.mapFromGlobal(cursor_pos)
            is_directly_over = self.rect().contains(local_pos)

            # Proximity calculation: radius of 180px around the notch
            if is_directly_over:
                target_proximity = 1.0
                target_hover = 1.0
            elif dist < 180.0:
                # Smooth cubic ease-out curve as cursor gets closer
                t = 1.0 - (dist / 180.0)
                target_proximity = t * t * (3.0 - 2.0 * t)  # smoothstep
                target_hover = max(0.0, 1.0 - (dist / 60.0))
            else:
                target_proximity = 0.0
                target_hover = 0.0

            # Dynamic gaze sensitivity: wider and sharper when cursor is nearby
            max_x = 5.5 + target_proximity * 1.5
            max_y = 4.0 + target_proximity * 1.0
            divisor_x = max(25.0, 90.0 - target_proximity * 50.0)
            divisor_y = max(20.0, 70.0 - target_proximity * 40.0)

            self.target_look_x = max(-max_x, min(max_x, dx / divisor_x))
            self.target_look_y = max(-max_y, min(max_y, dy / divisor_y))
        except Exception:
            pass

        # Smooth exponential interpolation (lerp) for proximity and hover factors
        self.proximity_intensity += (target_proximity - self.proximity_intensity) * 0.16
        self.hover_intensity += (target_hover - self.hover_intensity) * 0.20

        # Elastic bounce decay on hover entry
        if self.hover_bounce > 0.001:
            self.hover_bounce = max(0.0, self.hover_bounce - 0.07)

        # Hover breathing phase
        if self.hover_intensity > 0.05:
            self.hover_phase = (self.hover_phase + 0.14) % (math.pi * 2)

        # Emit proximity changed signal so HUD can adjust shadow/glow in sync
        self.proximity_changed.emit(self.proximity_intensity, self.hover_intensity)

        # Smooth sleep transition and breathing
        if self.is_sleeping:
            self.sleep_progress = min(1.0, self.sleep_progress + 0.06)
            self.sleep_phase = (self.sleep_phase + 0.06) % (math.pi * 2)
            # Center gaze while sleeping
            self.target_look_x = 0.0
            self.target_look_y = 0.8
        else:
            self.sleep_progress = max(0.0, self.sleep_progress - 0.12)

        # Smooth exponential interpolation (lerp) for gaze
        self.look_x += (self.target_look_x - self.look_x) * 0.22
        self.look_y += (self.target_look_y - self.look_y) * 0.22

        # 2. Frequent Lifelike Blinking (only when awake)
        if not self.is_sleeping:
            if not self.is_blinking:
                if self._tick_counter >= self._next_blink_tick:
                    self.is_blinking = True
                    self.blink_progress = 0.0
                    # Frequent intervals: every 1.5 to 3.2 seconds
                    self._next_blink_tick = self._tick_counter + random.randint(75, 160)
            else:
                self.blink_progress += 0.22
                if self.blink_progress >= 1.0:
                    self.is_blinking = False
                    self.blink_progress = 0.0
        else:
            self.is_blinking = False

        # 3. Headset animation & Music beat bobbing
        if self.is_playing_music:
            self.headset_anim_progress = min(1.0, self.headset_anim_progress + 0.08)
            self.music_bob_phase = (self.music_bob_phase + 0.16) % (math.pi * 2)
        else:
            self.headset_anim_progress = max(0.0, self.headset_anim_progress - 0.08)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Music rhythmic head bobbing
        bob_y = 0.0
        if self.headset_anim_progress > 0.01:
            bob_y = math.sin(self.music_bob_phase) * 2.2 * self.headset_anim_progress
        cy += bob_y

        # Proximity & Hover bounce effect on Y center (cute interactive spring)
        if self.hover_bounce > 0.001:
            bounce_y = -math.sin(self.hover_bounce * math.pi) * 2.2
            cy += bounce_y

        # Eye dimensions (HeyNixi exact pixel replica from REA)
        eye_base_w = 9.5
        eye_base_h = 16.0
        eye_gap = 22.0

        # Proximity expansion: eyes perk up curiously as cursor approaches
        eye_base_w += self.proximity_intensity * 1.5
        eye_base_h += self.proximity_intensity * 2.5

        # Hover continuous subtle breathing pulse (feels organic and alive)
        if self.hover_intensity > 0.01:
            hover_pulse = math.sin(self.hover_phase) * 0.8 * self.hover_intensity
            eye_base_h += hover_pulse

        # Apply blinking squish (awake)
        blink_factor = math.sin(self.blink_progress * math.pi) if self.is_blinking else 0.0
        awake_h = max(2.4, eye_base_h * (1.0 - blink_factor * 0.88))

        # Sleep horizontal eyelid slit with gentle rhythmic breathing
        sleep_breath = math.sin(self.sleep_phase) * 0.35 if self.is_sleeping else 0.0
        sleep_h = 2.4 + sleep_breath

        # Smooth blend between awake capsule and sleeping slit
        eye_h = awake_h * (1.0 - self.sleep_progress) + sleep_h * self.sleep_progress
        eye_w = eye_base_w * (1.0 - self.sleep_progress) + 11.5 * self.sleep_progress

        # Audio boost when listening / speaking (only if awake)
        if self.state == VisualizerState.LISTENING and not self.is_sleeping:
            eye_h = min(22.0, eye_h + self.audio_level * 5.0)

        # Eye centers with cursor gaze offset
        gaze_x = self.look_x
        gaze_y = self.look_y
        left_eye_cx = cx - (eye_gap / 2.0 + eye_base_w / 2.0) + gaze_x
        right_eye_cx = cx + (eye_gap / 2.0 + eye_base_w / 2.0) + gaze_x
        eye_cy = cy + gaze_y

        # 1. Draw the two capsule eyes
        self._draw_capsule_eye(painter, left_eye_cx, eye_cy, eye_w, eye_h)
        self._draw_capsule_eye(painter, right_eye_cx, eye_cy, eye_w, eye_h)

        # 2. Draw Cyberpunk Headset if wearing
        if self.headset_anim_progress > 0.01:
            self._draw_headset(painter, cx, cy, self.headset_anim_progress)

    def _draw_capsule_eye(self, painter: QPainter, x_center: float, y_center: float, w: float, h: float):
        rect = QRectF(x_center - w / 2.0, y_center - h / 2.0, w, h)
        radius = min(w, h) / 2.0

        # Dynamic aura glow that smoothly expands when cursor approaches
        glow_spread = 3.0 + self.proximity_intensity * 4.0 + self.hover_intensity * 2.5
        glow_rect = QRectF(
            x_center - w / 2.0 - glow_spread,
            y_center - h / 2.0 - glow_spread,
            w + glow_spread * 2.0,
            h + glow_spread * 2.0
        )

        base_alpha = int(45 + self.proximity_intensity * 40 + self.hover_intensity * 35)

        if self.state == VisualizerState.LISTENING:
            glow_color = QColor(192, 132, 252, min(140, base_alpha + 50))  # Purple neon
        elif self.state == VisualizerState.SPEAKING:
            glow_color = QColor(52, 211, 153, min(140, base_alpha + 50))   # Emerald glow
        elif self.state == VisualizerState.ERROR:
            glow_color = QColor(248, 113, 113, min(140, base_alpha + 50))  # Red warning
        else:
            # Idle aura: smooth blend from soft white to luminous icy-blue bloom on hover
            r = int(255 - self.hover_intensity * 45)   # 255 -> 210
            g = int(255 - self.hover_intensity * 15)   # 255 -> 240
            b = 255
            glow_color = QColor(r, g, b, min(130, base_alpha))

        painter.setPen(Qt.NoPen)
        painter.setBrush(glow_color)
        painter.drawRoundedRect(glow_rect, radius + glow_spread * 0.7, radius + glow_spread * 0.7)

        # Pure white capsule body
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        grad.setColorAt(1.0, QColor(242, 246, 252, 255))

        painter.setBrush(grad)
        painter.drawRoundedRect(rect, radius, radius)

    def _draw_headset(self, painter: QPainter, cx: float, cy: float, opacity: float):
        painter.save()
        painter.setOpacity(opacity)

        from PySide6.QtGui import QPainterPath

        # 1. Arched Headband connecting the ear cups
        band_path = QPainterPath()
        start_pt = QPointF(cx - 28.5, cy - 2.0)
        control_pt = QPointF(cx, cy - 19.5)
        end_pt = QPointF(cx + 28.5, cy - 2.0)
        band_path.moveTo(start_pt)
        band_path.quadTo(control_pt, end_pt)

        # Dark outer headband
        pen_outer = QPen(QColor("#161A22"), 4.0)
        pen_outer.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(band_path)

        # Neon cyan piping
        pen_neon = QPen(QColor("#00F0FF"), 1.8)
        pen_neon.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_neon)
        painter.drawPath(band_path)

        # 2. Over-Ear Headphone Cups (Left and Right)
        cup_w = 7.0
        cup_h = 19.0
        left_cup_rect = QRectF(cx - 32.5, cy - cup_h / 2.0, cup_w, cup_h)
        right_cup_rect = QRectF(cx + 25.5, cy - cup_h / 2.0, cup_w, cup_h)

        # Ear cushion gradient
        cup_grad = QLinearGradient(left_cup_rect.topLeft(), left_cup_rect.topRight())
        cup_grad.setColorAt(0.0, QColor("#0A0D12"))
        cup_grad.setColorAt(1.0, QColor("#222A36"))

        painter.setPen(QPen(QColor("#00F0FF"), 1.2))
        painter.setBrush(cup_grad)
        painter.drawRoundedRect(left_cup_rect, 3.5, 3.5)
        painter.drawRoundedRect(right_cup_rect, 3.5, 3.5)

        # 3. Pulsing Audio Beat Waves emitting from ear cups
        wave_pulse = (math.sin(self.music_bob_phase * 2) + 1.0) * 0.5
        ring_radius = 5.0 + wave_pulse * 6.0
        ring_alpha = int((1.0 - wave_pulse) * 160)
        if ring_alpha > 0:
            ring_pen = QPen(QColor(0, 240, 255, ring_alpha), 1.2)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(cx - 36.0 - ring_radius, cy - ring_radius, ring_radius * 2, ring_radius * 2), 120 * 16, 120 * 16)
            painter.drawArc(QRectF(cx + 36.0 - ring_radius, cy - ring_radius, ring_radius * 2, ring_radius * 2), -60 * 16, 120 * 16)

        painter.restore()


# Backwards compatibility alias for other files importing CyberVisualizerOrb
CyberVisualizerOrb = CyberMascotEyes

