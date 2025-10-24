"""
Dashboard Widget

Instrument discovery and connection interface.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QProgressBar,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

logger = logging.getLogger(__name__)


class ScanThread(QThread):
    """Background thread for instrument scanning"""
    scan_complete = pyqtSignal(list)  # List of identities

    def __init__(self, detector):
        super().__init__()
        self.detector = detector

    def run(self):
        try:
            identities = self.detector.detect_instruments()
            self.scan_complete.emit(identities)
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            self.scan_complete.emit([])


class DashboardWidget(QWidget):
    """
    Dashboard for instrument discovery and connection.

    Mimics BenchVue's main dashboard where users can:
    - Scan for instruments
    - View detected instruments
    - Connect/disconnect
    - View instrument details
    """

    instrument_connected = pyqtSignal(str, object)  # name, instrument

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.detector = main_window.detector
        self.detected_instruments = []

        self._create_ui()

    def _create_ui(self):
        """Create dashboard UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("<h2>Instrument Discovery</h2>")
        layout.addWidget(header)

        description = QLabel(
            "Scan for connected instruments and establish connections. "
            "Supports USB, GPIB, LAN, and RS-232 interfaces via VISA."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Scan button
        btn_layout = QHBoxLayout()
        self.scan_button = QPushButton("🔍 Scan for Instruments")
        self.scan_button.clicked.connect(self.scan_instruments)
        self.scan_button.setMinimumHeight(40)
        btn_layout.addWidget(self.scan_button)

        self.connect_button = QPushButton("✓ Connect Selected")
        self.connect_button.clicked.connect(self._connect_selected)
        self.connect_button.setEnabled(False)
        btn_layout.addWidget(self.connect_button)

        layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Instrument list
        list_label = QLabel("<b>Detected Instruments:</b>")
        layout.addWidget(list_label)

        self.instrument_list = QListWidget()
        self.instrument_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.instrument_list)

        # Status label
        self.status_label = QLabel("Click 'Scan for Instruments' to begin")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def scan_instruments(self):
        """Start instrument scan"""
        if not self.detector:
            QMessageBox.warning(
                self,
                "VISA Not Available",
                "VISA backend not initialized. "
                "Please install Keysight IO Libraries or NI-VISA."
            )
            return

        # Clear list
        self.instrument_list.clear()
        self.detected_instruments = []

        # Show progress
        self.scan_button.setEnabled(False)
        self.connect_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Scanning for instruments...")

        # Start scan in background thread
        self.scan_thread = ScanThread(self.detector)
        self.scan_thread.scan_complete.connect(self._on_scan_complete)
        self.scan_thread.start()

    def _on_scan_complete(self, identities):
        """Handle scan completion"""
        self.detected_instruments = identities

        # Hide progress
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)

        if identities:
            self.status_label.setText(f"Found {len(identities)} instrument(s)")

            # Populate list
            for identity in identities:
                item_text = (
                    f"{identity.manufacturer} {identity.model}\n"
                    f"  Type: {identity.instrument_type.value}\n"
                    f"  Resource: {identity.resource_string}\n"
                    f"  S/N: {identity.serial_number}"
                )
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, identity)
                self.instrument_list.addItem(item)

            logger.info(f"Scan complete: {len(identities)} instruments found")
        else:
            self.status_label.setText("No instruments detected")
            QMessageBox.information(
                self,
                "Scan Complete",
                "No instruments were detected.\n\n"
                "Please check:\n"
                "• Instruments are powered on\n"
                "• Cables are connected\n"
                "• VISA drivers are installed\n"
                "• GPIB/USB/LAN configuration is correct"
            )

    def _on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.instrument_list.selectedItems()) > 0
        self.connect_button.setEnabled(has_selection)

    def _connect_selected(self):
        """Connect to selected instruments"""
        selected_items = self.instrument_list.selectedItems()

        if not selected_items:
            return

        connected_count = 0

        for item in selected_items:
            identity = item.data(Qt.UserRole)

            try:
                # Create instrument
                instrument = self.detector.create_instrument(identity)

                if instrument:
                    # Connect
                    instrument.connect()

                    # Generate name
                    name = f"{identity.instrument_type.name}_{connected_count+1}"

                    # Emit signal
                    self.instrument_connected.emit(name, instrument)

                    # Mark item as connected
                    item.setBackground(Qt.green)
                    item.setForeground(Qt.white)

                    connected_count += 1
                    logger.info(f"Connected: {name} at {identity.resource_string}")

            except Exception as e:
                logger.error(f"Connection failed: {e}")
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    f"Failed to connect to {identity.model}:\n{e}"
                )

        if connected_count > 0:
            self.status_label.setText(f"Connected {connected_count} instrument(s)")
            QMessageBox.information(
                self,
                "Connection Complete",
                f"Successfully connected {connected_count} instrument(s)"
            )
