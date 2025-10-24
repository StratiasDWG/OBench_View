"""
Advanced GUI Widgets

Professional widgets:
- Analog gauges
- Digital displays
- Status indicators
- Progress widgets
- Instrument wizards
"""

import logging
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath

logger = logging.getLogger(__name__)


class AnalogGauge(QWidget):
    """
    Analog gauge widget with needle and scale.

    Professional circular gauge for displaying measurements.
    """

    def __init__(self, min_value: float = 0, max_value: float = 100,
                 unit: str = "", parent=None):
        super().__init__(parent)

        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.unit = unit

        # Appearance
        self.gauge_color = QColor(33, 150, 243)
        self.needle_color = QColor(244, 67, 54)
        self.scale_color = QColor(100, 100, 100)
        self.text_color = QColor(50, 50, 50)

        # Zones (green, yellow, red)
        self.zones = [
            (0.0, 0.7, QColor(76, 175, 80, 100)),    # Green
            (0.7, 0.9, QColor(255, 193, 7, 100)),    # Yellow
            (0.9, 1.0, QColor(244, 67, 54, 100)),    # Red
        ]

        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, value: float):
        """Set gauge value"""
        self.current_value = max(self.min_value, min(self.max_value, value))
        self.update()

    def set_zones(self, zones: list):
        """
        Set color zones.

        Args:
            zones: List of (start_ratio, end_ratio, QColor) tuples
        """
        self.zones = zones
        self.update()

    def paintEvent(self, event):
        """Custom paint for gauge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height)
        center_x = width / 2
        center_y = height / 2
        radius = size * 0.4

        # Draw background
        painter.setBrush(QBrush(QColor(245, 245, 245)))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), int(radius), int(radius))

        # Draw zones
        start_angle = 225  # degrees
        span_angle = 270   # degrees

        for start_ratio, end_ratio, color in self.zones:
            zone_start = start_angle - (start_ratio * span_angle)
            zone_span = -(end_ratio - start_ratio) * span_angle

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)

            # Draw arc for zone
            rect = QRect(
                int(center_x - radius), int(center_y - radius),
                int(2 * radius), int(2 * radius)
            )
            painter.drawPie(rect, int(zone_start * 16), int(zone_span * 16))

        # Draw scale marks
        painter.setPen(QPen(self.scale_color, 2))

        for i in range(11):  # 11 marks (0-10)
            ratio = i / 10
            angle = math.radians(start_angle - ratio * span_angle)

            # Long marks at 0, 5, 10
            mark_length = radius * 0.15 if i % 5 == 0 else radius * 0.1

            x1 = center_x + radius * 0.85 * math.cos(angle)
            y1 = center_y - radius * 0.85 * math.sin(angle)
            x2 = center_x + (radius * 0.85 - mark_length) * math.cos(angle)
            y2 = center_y - (radius * 0.85 - mark_length) * math.sin(angle)

            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Draw value labels
            if i % 2 == 0:
                value = self.min_value + ratio * (self.max_value - self.min_value)
                text = f"{value:.0f}"

                text_x = center_x + radius * 0.65 * math.cos(angle)
                text_y = center_y - radius * 0.65 * math.sin(angle)

                painter.setFont(QFont('Arial', 8))
                painter.setPen(self.text_color)
                painter.drawText(
                    QRect(int(text_x - 20), int(text_y - 10), 40, 20),
                    Qt.AlignCenter,
                    text
                )

        # Draw needle
        value_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        needle_angle = math.radians(start_angle - value_ratio * span_angle)

        needle_length = radius * 0.8
        needle_x = center_x + needle_length * math.cos(needle_angle)
        needle_y = center_y - needle_length * math.sin(needle_angle)

        # Needle path (triangle)
        path = QPainterPath()
        path.moveTo(center_x, center_y)
        path.lineTo(
            center_x + 5 * math.cos(needle_angle + math.pi/2),
            center_y - 5 * math.sin(needle_angle + math.pi/2)
        )
        path.lineTo(needle_x, needle_y)
        path.lineTo(
            center_x + 5 * math.cos(needle_angle - math.pi/2),
            center_y - 5 * math.sin(needle_angle - math.pi/2)
        )
        path.closeSubpath()

        painter.setBrush(QBrush(self.needle_color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # Draw center circle
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawEllipse(QPoint(int(center_x), int(center_y)), 8, 8)

        # Draw value text
        painter.setPen(self.text_color)
        painter.setFont(QFont('Arial', 14, QFont.Bold))
        text = f"{self.current_value:.2f} {self.unit}"
        painter.drawText(
            QRect(int(center_x - 60), int(center_y + radius * 0.5), 120, 30),
            Qt.AlignCenter,
            text
        )


class DigitalDisplay(QWidget):
    """
    Digital LCD-style display for measurements.
    """

    def __init__(self, label: str = "", unit: str = "", decimals: int = 3, parent=None):
        super().__init__(parent)

        self.label_text = label
        self.unit = unit
        self.decimals = decimals
        self.value = 0.0

        self.setMinimumSize(200, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: float):
        """Set display value"""
        self.value = value
        self.update()

    def paintEvent(self, event):
        """Custom paint for LCD display"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw background (LCD style)
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(50, 50, 50))
        gradient.setColorAt(1, QColor(30, 30, 30))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRoundedRect(5, 5, width - 10, height - 10, 8, 8)

        # Draw label
        painter.setPen(QColor(100, 200, 100))
        painter.setFont(QFont('Arial', 9))
        painter.drawText(
            QRect(15, 10, width - 30, 20),
            Qt.AlignLeft | Qt.AlignTop,
            self.label_text
        )

        # Draw value (large LCD digits)
        painter.setPen(QColor(0, 255, 0))
        painter.setFont(QFont('Courier New', 24, QFont.Bold))

        value_text = f"{self.value:.{self.decimals}f}"
        painter.drawText(
            QRect(15, 25, width - 30, 40),
            Qt.AlignRight | Qt.AlignVCenter,
            value_text
        )

        # Draw unit
        painter.setPen(QColor(150, 200, 150))
        painter.setFont(QFont('Arial', 10))
        painter.drawText(
            QRect(width - 60, height - 25, 50, 20),
            Qt.AlignRight | Qt.AlignBottom,
            self.unit
        )


class StatusIndicator(QWidget):
    """
    LED-style status indicator.
    """

    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)

        self.label_text = label
        self.state = False
        self.color_on = QColor(76, 175, 80)
        self.color_off = QColor(100, 100, 100)

        self.setFixedSize(100, 30)

    def set_state(self, state: bool):
        """Set indicator state"""
        self.state = state
        self.update()

    def set_colors(self, color_on: QColor, color_off: QColor):
        """Set indicator colors"""
        self.color_on = color_on
        self.color_off = color_off
        self.update()

    def paintEvent(self, event):
        """Custom paint for LED"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw LED circle
        color = self.color_on if self.state else self.color_off

        gradient = QLinearGradient(5, 5, 25, 25)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, color)

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(color.darker(150), 2))
        painter.drawEllipse(5, 5, 20, 20)

        # Draw glow effect if on
        if self.state:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color.lighter(120), 3, Qt.SolidLine))
            painter.drawEllipse(3, 3, 24, 24)

        # Draw label
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(QFont('Arial', 9))
        painter.drawText(
            QRect(30, 0, 70, 30),
            Qt.AlignLeft | Qt.AlignVCenter,
            self.label_text
        )


class EnhancedProgressBar(QFrame):
    """
    Enhanced progress bar with percentage and ETA.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(30)
        layout.addWidget(self.progress_bar)

        # Info label
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        self.start_time = None

    def set_value(self, value: int):
        """Set progress value (0-100)"""
        self.progress_bar.setValue(value)

        # Calculate ETA
        if self.start_time is None:
            import time
            self.start_time = time.time()

        if value > 0:
            import time
            elapsed = time.time() - self.start_time
            total_time = elapsed * 100 / value
            remaining = total_time - elapsed

            eta_text = f"ETA: {int(remaining)}s" if remaining > 0 else "Completing..."
            self.info_label.setText(f"{value}% - {eta_text}")
        else:
            self.info_label.setText("0% - Calculating...")

    def reset(self):
        """Reset progress bar"""
        self.progress_bar.setValue(0)
        self.start_time = None
        self.info_label.setText("")


class InstrumentCard(QFrame):
    """
    Card widget for displaying instrument info.
    """

    clicked = pyqtSignal()

    def __init__(self, name: str, inst_type: str, status: str, parent=None):
        super().__init__(parent)

        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumSize(250, 120)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)

        # Name
        name_label = QLabel(f"<h3>{name}</h3>")
        layout.addWidget(name_label)

        # Type
        type_label = QLabel(inst_type)
        type_label.setStyleSheet("color: #666; font-size: 11pt;")
        layout.addWidget(type_label)

        # Status
        self.status_indicator = StatusIndicator(status)
        layout.addWidget(self.status_indicator)

        layout.addStretch()

    def mouseReleaseEvent(self, event):
        """Handle click"""
        self.clicked.emit()

    def set_status(self, connected: bool):
        """Set connection status"""
        self.status_indicator.set_state(connected)


class MeasurementDisplay(QFrame):
    """
    Combined display with gauge and digital readout.
    """

    def __init__(self, label: str, unit: str, min_val: float, max_val: float, parent=None):
        super().__init__(parent)

        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)

        layout = QVBoxLayout(self)

        # Label
        title = QLabel(f"<b>{label}</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Gauge
        self.gauge = AnalogGauge(min_val, max_val, unit)
        layout.addWidget(self.gauge)

        # Digital display
        self.digital = DigitalDisplay("", unit, decimals=3)
        layout.addWidget(self.digital)

    def set_value(self, value: float):
        """Update both gauge and digital display"""
        self.gauge.set_value(value)
        self.digital.set_value(value)


class ToolPanel(QFrame):
    """
    Collapsible tool panel.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.setFrameStyle(QFrame.StyledPanel)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setFrameStyle(QFrame.Box)
        header.setCursor(Qt.PointingHandCursor)

        header_layout = QHBoxLayout(header)
        self.title_label = QLabel(f"▼ {title}")
        self.title_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        header.mousePressEvent = self._toggle_collapsed

        main_layout.addWidget(header)

        # Content
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        main_layout.addWidget(self.content)

        self.collapsed = False

    def _toggle_collapsed(self, event):
        """Toggle panel collapsed state"""
        self.collapsed = not self.collapsed

        if self.collapsed:
            self.content.hide()
            title_text = self.title_label.text().replace("▼", "▶")
            self.title_label.setText(title_text)
        else:
            self.content.show()
            title_text = self.title_label.text().replace("▶", "▼")
            self.title_label.setText(title_text)
