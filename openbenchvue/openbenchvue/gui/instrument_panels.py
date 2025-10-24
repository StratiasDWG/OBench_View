"""
Instrument Control Panels

Device-specific control interfaces.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QGridLayout, QPushButton,
    QDoubleSpinBox, QCheckBox, QTextEdit, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer

logger = logging.getLogger(__name__)


class InstrumentControlWidget(QWidget):
    """
    Multi-instrument control interface.

    Provides tabbed or dropdown interface for controlling
    multiple connected instruments.
    """

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.instruments = {}
        self.current_instrument = None

        self._create_ui()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms

    def _create_ui(self):
        """Create control UI"""
        layout = QVBoxLayout(self)

        # Instrument selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("<b>Instrument:</b>"))

        self.instrument_selector = QComboBox()
        self.instrument_selector.currentTextChanged.connect(self._on_instrument_selected)
        selector_layout.addWidget(self.instrument_selector, 1)

        layout.addLayout(selector_layout)

        # Control area (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self.control_widget = QWidget()
        self.control_layout = QVBoxLayout(self.control_widget)
        scroll.setWidget(self.control_widget)

        layout.addWidget(scroll)

        # Initial message
        self.no_instrument_label = QLabel(
            "<h3>No Instruments Connected</h3>"
            "<p>Connect instruments from the Dashboard tab.</p>"
        )
        self.no_instrument_label.setAlignment(Qt.AlignCenter)
        self.control_layout.addWidget(self.no_instrument_label)
        self.control_layout.addStretch()

    def add_instrument(self, name: str, instrument):
        """Add instrument to control panel"""
        self.instruments[name] = instrument
        self.instrument_selector.addItem(name)

        # Select if first instrument
        if len(self.instruments) == 1:
            self.instrument_selector.setCurrentText(name)

        logger.info(f"Added instrument to control panel: {name}")

    def _on_instrument_selected(self, name: str):
        """Handle instrument selection"""
        if name and name in self.instruments:
            self.current_instrument = self.instruments[name]
            self._build_control_panel()
        else:
            self.current_instrument = None

    def _build_control_panel(self):
        """Build control panel for current instrument"""
        # Clear existing controls
        while self.control_layout.count():
            child = self.control_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.current_instrument:
            return

        instrument = self.current_instrument
        inst_type = instrument.INSTRUMENT_TYPE.name

        # Create type-specific controls
        if inst_type == "DMM":
            self._create_dmm_controls()
        elif inst_type == "OSCILLOSCOPE":
            self._create_scope_controls()
        elif inst_type == "POWER_SUPPLY":
            self._create_psu_controls()
        elif inst_type == "FUNCTION_GENERATOR":
            self._create_fgen_controls()
        else:
            self._create_generic_controls()

        self.control_layout.addStretch()

    def _create_dmm_controls(self):
        """Create DMM controls"""
        instrument = self.current_instrument

        # Measurement display
        display_group = QGroupBox("Measurement")
        display_layout = QVBoxLayout()

        self.dmm_reading = QLabel("---")
        self.dmm_reading.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.dmm_reading.setAlignment(Qt.AlignCenter)
        display_layout.addWidget(self.dmm_reading)

        display_group.setLayout(display_layout)
        self.control_layout.addWidget(display_group)

        # Function selector
        function_group = QGroupBox("Function")
        function_layout = QGridLayout()

        function_layout.addWidget(QLabel("Measurement:"), 0, 0)
        self.dmm_function = QComboBox()
        self.dmm_function.addItems([
            "DC Voltage", "AC Voltage", "DC Current", "AC Current",
            "Resistance", "Frequency", "Capacitance"
        ])
        function_layout.addWidget(self.dmm_function, 0, 1)

        measure_button = QPushButton("Measure")
        measure_button.clicked.connect(self._dmm_measure)
        function_layout.addWidget(measure_button, 1, 0, 1, 2)

        function_group.setLayout(function_layout)
        self.control_layout.addWidget(function_group)

    def _create_psu_controls(self):
        """Create power supply controls"""
        instrument = self.current_instrument

        # Channel selector
        if hasattr(instrument, 'num_channels') and instrument.num_channels > 1:
            channel_layout = QHBoxLayout()
            channel_layout.addWidget(QLabel("<b>Channel:</b>"))
            self.psu_channel = QComboBox()
            for i in range(1, instrument.num_channels + 1):
                self.psu_channel.addItem(f"Channel {i}")
            channel_layout.addWidget(self.psu_channel)
            channel_layout.addStretch()
            self.control_layout.addLayout(channel_layout)

        # Voltage control
        voltage_group = QGroupBox("Voltage")
        voltage_layout = QGridLayout()

        voltage_layout.addWidget(QLabel("Set:"), 0, 0)
        self.psu_voltage = QDoubleSpinBox()
        self.psu_voltage.setRange(0, 30)
        self.psu_voltage.setDecimals(3)
        self.psu_voltage.setSuffix(" V")
        voltage_layout.addWidget(self.psu_voltage, 0, 1)

        voltage_button = QPushButton("Apply")
        voltage_button.clicked.connect(self._psu_set_voltage)
        voltage_layout.addWidget(voltage_button, 0, 2)

        voltage_layout.addWidget(QLabel("Measured:"), 1, 0)
        self.psu_voltage_measured = QLabel("0.000 V")
        voltage_layout.addWidget(self.psu_voltage_measured, 1, 1)

        voltage_group.setLayout(voltage_layout)
        self.control_layout.addWidget(voltage_group)

        # Current control
        current_group = QGroupBox("Current")
        current_layout = QGridLayout()

        current_layout.addWidget(QLabel("Limit:"), 0, 0)
        self.psu_current = QDoubleSpinBox()
        self.psu_current.setRange(0, 5)
        self.psu_current.setDecimals(3)
        self.psu_current.setSuffix(" A")
        current_layout.addWidget(self.psu_current, 0, 1)

        current_button = QPushButton("Apply")
        current_button.clicked.connect(self._psu_set_current)
        current_layout.addWidget(current_button, 0, 2)

        current_layout.addWidget(QLabel("Measured:"), 1, 0)
        self.psu_current_measured = QLabel("0.000 A")
        current_layout.addWidget(self.psu_current_measured, 1, 1)

        current_group.setLayout(current_layout)
        self.control_layout.addWidget(current_group)

        # Output control
        output_layout = QHBoxLayout()
        self.psu_output = QCheckBox("Output Enabled")
        self.psu_output.toggled.connect(self._psu_toggle_output)
        output_layout.addWidget(self.psu_output)
        output_layout.addStretch()
        self.control_layout.addLayout(output_layout)

    def _create_generic_controls(self):
        """Create generic SCPI controls"""
        group = QGroupBox("SCPI Commands")
        layout = QVBoxLayout()

        self.scpi_input = QTextEdit()
        self.scpi_input.setPlaceholderText("Enter SCPI command...")
        self.scpi_input.setMaximumHeight(60)
        layout.addWidget(self.scpi_input)

        send_button = QPushButton("Send Command")
        send_button.clicked.connect(self._send_scpi)
        layout.addWidget(send_button)

        self.scpi_output = QTextEdit()
        self.scpi_output.setReadOnly(True)
        self.scpi_output.setPlaceholderText("Response will appear here...")
        layout.addWidget(self.scpi_output)

        group.setLayout(layout)
        self.control_layout.addWidget(group)

    def _create_scope_controls(self):
        """Create oscilloscope controls (simplified)"""
        label = QLabel("<p>Oscilloscope controls coming soon...</p>"
                      "<p>Use SCPI commands for now.</p>")
        self.control_layout.addWidget(label)
        self._create_generic_controls()

    def _create_fgen_controls(self):
        """Create function generator controls (simplified)"""
        label = QLabel("<p>Function generator controls coming soon...</p>"
                      "<p>Use SCPI commands for now.</p>")
        self.control_layout.addWidget(label)
        self._create_generic_controls()

    def _dmm_measure(self):
        """Perform DMM measurement"""
        try:
            value = self.current_instrument.measure()
            self.dmm_reading.setText(f"{value:.6f}")
        except Exception as e:
            logger.error(f"DMM measurement failed: {e}")
            self.dmm_reading.setText("Error")

    def _psu_set_voltage(self):
        """Set PSU voltage"""
        try:
            channel = 1  # Simplified
            voltage = self.psu_voltage.value()
            self.current_instrument.set_voltage(channel, voltage)
            logger.info(f"Set voltage to {voltage}V")
        except Exception as e:
            logger.error(f"Failed to set voltage: {e}")

    def _psu_set_current(self):
        """Set PSU current limit"""
        try:
            channel = 1
            current = self.psu_current.value()
            self.current_instrument.set_current(channel, current)
            logger.info(f"Set current to {current}A")
        except Exception as e:
            logger.error(f"Failed to set current: {e}")

    def _psu_toggle_output(self, enabled):
        """Toggle PSU output"""
        try:
            channel = 1
            self.current_instrument.set_output(channel, enabled)
            logger.info(f"Output {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logger.error(f"Failed to toggle output: {e}")

    def _send_scpi(self):
        """Send SCPI command"""
        if not self.current_instrument:
            return

        command = self.scpi_input.toPlainText().strip()
        if not command:
            return

        try:
            if '?' in command:
                response = self.current_instrument.query(command)
                self.scpi_output.append(f"> {command}\n{response}\n")
            else:
                self.current_instrument.write(command)
                self.scpi_output.append(f"> {command}\n(Command sent)\n")

            self.scpi_input.clear()
        except Exception as e:
            self.scpi_output.append(f"> {command}\nError: {e}\n")
            logger.error(f"SCPI command failed: {e}")

    def _update_display(self):
        """Update instrument readings"""
        if not self.current_instrument:
            return

        try:
            inst_type = self.current_instrument.INSTRUMENT_TYPE.name

            if inst_type == "POWER_SUPPLY":
                # Update PSU measurements
                channel = 1
                v_meas = self.current_instrument.measure_voltage(channel)
                i_meas = self.current_instrument.measure_current(channel)
                self.psu_voltage_measured.setText(f"{v_meas:.3f} V")
                self.psu_current_measured.setText(f"{i_meas:.3f} A")

        except Exception as e:
            logger.debug(f"Update failed: {e}")
