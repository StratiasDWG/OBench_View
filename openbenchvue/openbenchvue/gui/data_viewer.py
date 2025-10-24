"""
Data Viewer Widget

Real-time data visualization and logging interface.
"""

import logging
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QSplitter
)
from PyQt5.QtCore import Qt, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ..data.exporter import DataExporter

logger = logging.getLogger(__name__)


class DataViewerWidget(QWidget):
    """
    Data logger and visualization widget.

    Provides BenchVue-like data logging:
    - Start/stop logging
    - Real-time plotting
    - Channel selection
    - Export functionality
    """

    def __init__(self, data_logger):
        super().__init__()
        self.data_logger = data_logger

        self._create_ui()

        # Update timer for plot
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self._update_plot)
        self.plot_timer.start(500)  # Update every 500ms

    def _create_ui(self):
        """Create data viewer UI"""
        layout = QVBoxLayout(self)

        # Control bar
        control_layout = QHBoxLayout()

        self.start_button = QPushButton("▶ Start Logging")
        self.start_button.clicked.connect(self._start_logging)
        control_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("⏸ Stop Logging")
        self.stop_button.clicked.connect(self._stop_logging)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.clear_button = QPushButton("🗑 Clear Data")
        self.clear_button.clicked.connect(self._clear_data)
        control_layout.addWidget(self.clear_button)

        self.export_button = QPushButton("💾 Export...")
        self.export_button.clicked.connect(self._export_dialog)
        control_layout.addWidget(self.export_button)

        control_layout.addStretch()

        self.status_label = QLabel("Not logging")
        control_layout.addWidget(self.status_label)

        layout.addLayout(control_layout)

        # Splitter for channel list and plot
        splitter = QSplitter(Qt.Horizontal)

        # Channel list
        self.channel_list = QListWidget()
        self.channel_list.setMaximumWidth(200)
        splitter.addWidget(self.channel_list)

        # Plot area
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Value')
        self.ax.set_title('Real-Time Data')
        self.ax.grid(True)

        splitter.addWidget(plot_widget)

        layout.addWidget(splitter)

        # Statistics label
        self.stats_label = QLabel("No data")
        layout.addWidget(self.stats_label)

    def _start_logging(self):
        """Start data logging"""
        self.data_logger.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Logging...")
        logger.info("Data logging started")

    def _stop_logging(self):
        """Stop data logging"""
        self.data_logger.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopped")
        logger.info("Data logging stopped")

    def _clear_data(self):
        """Clear logged data"""
        self.data_logger.clear()
        self.channel_list.clear()
        self.ax.clear()
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Value')
        self.ax.set_title('Real-Time Data')
        self.ax.grid(True)
        self.canvas.draw()
        self.stats_label.setText("Data cleared")
        logger.info("Data cleared")

    def _update_plot(self):
        """Update plot with latest data"""
        if self.data_logger.get_count() == 0:
            return

        # Update channel list
        channels = self.data_logger.get_channels()
        current_channels = [self.channel_list.item(i).text()
                           for i in range(self.channel_list.count())]

        if channels != current_channels:
            self.channel_list.clear()
            self.channel_list.addItems(channels)

        # Get data for all channels
        data = self.data_logger.get_all_channels_data()

        if not data:
            return

        # Clear and replot
        self.ax.clear()
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Value')
        self.ax.set_title('Real-Time Data')
        self.ax.grid(True)

        # Plot each channel
        for channel, (times, values) in data.items():
            if len(times) > 0 and len(values) > 0:
                self.ax.plot(times, values, label=channel, marker='o', markersize=2)

        if data:
            self.ax.legend()

        self.canvas.draw()

        # Update statistics
        if channels:
            stats_text = f"Points: {self.data_logger.get_count()} | "
            stats_text += f"Channels: {len(channels)} | "
            stats_text += f"Duration: {self.data_logger.get_duration():.1f}s"
            self.stats_label.setText(stats_text)

    def _export_dialog(self):
        """Show export dialog (simplified)"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
        )

        if file_path:
            self.export_data(file_path)

    def export_data(self, file_path: str):
        """Export data to file"""
        try:
            data = self.data_logger.get_all_channels_data()

            if not data:
                logger.warning("No data to export")
                return

            # Determine format from extension
            if file_path.endswith('.xlsx'):
                DataExporter.to_excel(data, file_path)
            elif file_path.endswith('.json'):
                DataExporter.to_json(data, file_path)
            else:
                DataExporter.to_csv(data, file_path)

            logger.info(f"Data exported to {file_path}")

        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
