"""
Main Window

Primary application window with tabbed interface for different functions.
"""

import logging
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QStatusBar, QMenuBar,
    QAction, QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon

from ..instruments.detector import InstrumentDetector
from ..data.logger import DataLogger
from ..remote.server import RemoteServer
from .. import config

from .dashboard import DashboardWidget
from .instrument_panels import InstrumentControlWidget
from .data_viewer import DataViewerWidget
from .sequence_builder import SequenceBuilderWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.

    Provides BenchVue-like interface:
    - Dashboard for instrument discovery
    - Tabbed interface for different functions
    - Status bar with connection info
    - Menu bar with file operations
    """

    instrument_connected = pyqtSignal(str, object)  # name, instrument
    instrument_disconnected = pyqtSignal(str)  # name

    def __init__(self, config_file: str = None):
        super().__init__()

        self.config_file = config_file

        # Initialize components
        self.detector = None
        self.instruments: Dict[str, Any] = {}
        self.data_logger = DataLogger()
        self.remote_server = None

        # Setup UI
        self.setWindowTitle("OpenBenchVue - Instrument Control & Automation")
        self.setGeometry(100, 100, 1200, 800)

        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()

        # Initialize detector
        self._init_detector()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(config.get('gui.update_rate', 100))

        logger.info("Main window initialized")

    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('&File')

        open_action = QAction('&Open Sequence...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._open_sequence)
        file_menu.addAction(open_action)

        save_action = QAction('&Save Sequence...', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self._save_sequence)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction('&Export Data...', self)
        export_action.triggered.connect(self._export_data)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu('&Tools')

        scan_action = QAction('&Scan for Instruments', self)
        scan_action.setShortcut('F5')
        scan_action.triggered.connect(self._scan_instruments)
        tools_menu.addAction(scan_action)

        remote_action = QAction('Start &Remote Server', self)
        remote_action.triggered.connect(self._toggle_remote_server)
        tools_menu.addAction(remote_action)
        self.remote_action = remote_action

        tools_menu.addSeparator()

        settings_action = QAction('&Settings...', self)
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About OpenBenchVue', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        docs_action = QAction('&Documentation', self)
        docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(docs_action)

    def _create_central_widget(self):
        """Create central widget with tabs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Dashboard tab
        self.dashboard = DashboardWidget(self)
        self.dashboard.instrument_connected.connect(self._on_instrument_connected)
        self.tab_widget.addTab(self.dashboard, "Dashboard")

        # Instrument Control tab
        self.instrument_control = InstrumentControlWidget(self)
        self.tab_widget.addTab(self.instrument_control, "Instrument Control")

        # Data Viewer tab
        self.data_viewer = DataViewerWidget(self.data_logger)
        self.tab_widget.addTab(self.data_viewer, "Data Logger")

        # Sequence Builder tab
        self.sequence_builder = SequenceBuilderWidget(self)
        self.tab_widget.addTab(self.sequence_builder, "Automation")

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status labels
        self.status_label = QLabel("Ready")
        self.instruments_label = QLabel("Instruments: 0")
        self.remote_label = QLabel("Remote: Offline")

        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.instruments_label)
        self.status_bar.addPermanentWidget(self.remote_label)

        self.status_bar.showMessage("Welcome to OpenBenchVue")

    def _init_detector(self):
        """Initialize instrument detector"""
        try:
            backend = config.get('visa.backend', '@iolib')
            self.detector = InstrumentDetector(visa_backend=backend)
            logger.info(f"Initialized detector with backend: {backend}")
        except Exception as e:
            logger.error(f"Failed to initialize detector: {e}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize VISA:\n{e}\n\n"
                "Please ensure Keysight IO Libraries or NI-VISA is installed."
            )

    def _scan_instruments(self):
        """Scan for instruments"""
        if self.detector:
            self.dashboard.scan_instruments()

    def _on_instrument_connected(self, name: str, instrument):
        """Handle instrument connection"""
        self.instruments[name] = instrument
        self.instrument_control.add_instrument(name, instrument)
        self._update_status()
        self.instrument_connected.emit(name, instrument)

        logger.info(f"Instrument connected: {name}")

    def _update_ui(self):
        """Periodic UI update"""
        # Update status bar
        self._update_status()

    def _update_status(self):
        """Update status bar"""
        self.instruments_label.setText(f"Instruments: {len(self.instruments)}")

        if self.remote_server and self.remote_server.is_running():
            self.remote_label.setText("Remote: Online")
        else:
            self.remote_label.setText("Remote: Offline")

    def _toggle_remote_server(self):
        """Toggle remote server"""
        if self.remote_server and self.remote_server.is_running():
            self.remote_server.stop()
            self.remote_action.setText('Start &Remote Server')
            QMessageBox.information(self, "Remote Server", "Remote server stopped")
        else:
            try:
                port = config.get('remote.port', 5000)
                self.remote_server = RemoteServer(host='0.0.0.0', port=port)
                self.remote_server.set_instruments(self.instruments)
                self.remote_server.set_data_logger(self.data_logger)
                self.remote_server.start()

                self.remote_action.setText('Stop &Remote Server')

                QMessageBox.information(
                    self,
                    "Remote Server",
                    f"Remote server started!\n\n"
                    f"Access dashboard at:\n{self.remote_server.get_url()}"
                )
            except Exception as e:
                logger.error(f"Failed to start remote server: {e}")
                QMessageBox.critical(self, "Error", f"Failed to start remote server:\n{e}")

    def _open_sequence(self):
        """Open sequence file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Sequence",
            "",
            "Sequence Files (*.yaml *.yml *.json);;All Files (*)"
        )

        if file_path:
            try:
                self.sequence_builder.load_sequence(file_path)
                self.status_bar.showMessage(f"Loaded sequence: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load sequence:\n{e}")

    def _save_sequence(self):
        """Save sequence file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sequence",
            "",
            "YAML Files (*.yaml);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                self.sequence_builder.save_sequence(file_path)
                self.status_bar.showMessage(f"Saved sequence: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save sequence:\n{e}")

    def _export_data(self):
        """Export logged data"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                self.data_viewer.export_data(file_path)
                self.status_bar.showMessage(f"Exported data: {file_path}")
                QMessageBox.information(self, "Export Complete", f"Data exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data:\n{e}")

    def _show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(
            self,
            "Settings",
            "Settings dialog not yet implemented.\n\n"
            "Edit config.yaml manually for now."
        )

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About OpenBenchVue",
            "<h2>OpenBenchVue</h2>"
            "<p>Version 0.1.0</p>"
            "<p>Open-source instrument control and test automation platform.</p>"
            "<p>An alternative to Keysight PathWave BenchVue.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Multi-instrument support (DMM, Scope, PSU, FGen, etc.)</li>"
            "<li>Visual test automation</li>"
            "<li>Real-time data logging and visualization</li>"
            "<li>Remote web access</li>"
            "</ul>"
            "<p><b>Powered by:</b> Python, PyQt5, PyVISA, NumPy, Matplotlib</p>"
            "<p>Licensed under MIT License</p>"
        )

    def _show_documentation(self):
        """Show documentation"""
        import webbrowser
        webbrowser.open("https://github.com/yourusername/openbenchvue")

    def closeEvent(self, event):
        """Handle window close"""
        # Disconnect instruments
        for name, instrument in self.instruments.items():
            try:
                instrument.disconnect()
            except:
                pass

        # Stop remote server
        if self.remote_server:
            self.remote_server.stop()

        # Stop data logging
        if self.data_logger.is_logging():
            self.data_logger.stop()

        logger.info("Application closed")
        event.accept()
