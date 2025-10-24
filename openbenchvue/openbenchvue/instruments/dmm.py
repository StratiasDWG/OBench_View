"""
Digital Multimeter (DMM) Driver

Supports standard DMM functions: DC/AC voltage/current, resistance,
capacitance, frequency, continuity, and diode testing.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from enum import Enum

from .base import BaseInstrument, InstrumentType, InstrumentError

logger = logging.getLogger(__name__)


class MeasurementFunction(Enum):
    """DMM measurement functions"""
    DC_VOLTAGE = "VOLT:DC"
    AC_VOLTAGE = "VOLT:AC"
    DC_CURRENT = "CURR:DC"
    AC_CURRENT = "CURR:AC"
    RESISTANCE = "RES"
    FOUR_WIRE_RESISTANCE = "FRES"
    FREQUENCY = "FREQ"
    PERIOD = "PER"
    CAPACITANCE = "CAP"
    CONTINUITY = "CONT"
    DIODE = "DIOD"
    TEMPERATURE = "TEMP"


class DigitalMultimeter(BaseInstrument):
    """
    Digital Multimeter driver with standard SCPI commands.

    Supports common DMM operations found in BenchVue's DMM app:
    - Multiple measurement functions
    - Auto/manual ranging
    - Trigger modes
    - Math functions (null, min/max, statistics)
    - Data logging
    """

    INSTRUMENT_TYPE = InstrumentType.DMM
    SUPPORTED_MODELS = [
        r'34\d{3}[AB]?',  # Keysight 34401A, 34410A, 34461A, etc.
        r'U12\d{2}[AB]?',  # Keysight U1200 series handheld
        r'DAQ970A',  # Keysight DAQ with DMM
        r'DMM\d+',  # Generic DMM
    ]

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        # Current configuration
        self.current_function = MeasurementFunction.DC_VOLTAGE
        self.auto_range = True
        self.range_value = None
        self.nplc = 1  # Integration time in power line cycles
        self.resolution = None

        # Statistics tracking
        self._stats_enabled = False
        self._measurements: List[float] = []

    def initialize(self):
        """Initialize DMM to known state"""
        try:
            self.clear()
            self.reset()

            # Set to default function
            self.configure_measurement(MeasurementFunction.DC_VOLTAGE)

            logger.info("DMM initialized successfully")
        except Exception as e:
            logger.error(f"DMM initialization failed: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """Get DMM capabilities"""
        capabilities = {
            'functions': [func.name for func in MeasurementFunction],
            'auto_range': True,
            'nplc_range': (0.001, 100),
            'statistics': True,
            'math_functions': ['null', 'min_max', 'limit_test'],
            'trigger_sources': ['immediate', 'bus', 'external'],
        }

        # Query specific model capabilities if possible
        try:
            # Example: Query supported functions
            pass
        except Exception as e:
            logger.debug(f"Could not query extended capabilities: {e}")

        return capabilities

    def get_status(self) -> Dict[str, Any]:
        """Get current DMM status"""
        status = {
            'function': self.current_function.name,
            'auto_range': self.auto_range,
            'range': self.range_value,
            'nplc': self.nplc,
            'stats_enabled': self._stats_enabled,
        }

        # Query additional status
        try:
            errors = self.check_errors()
            status['errors'] = errors
        except:
            status['errors'] = []

        return status

    def configure_measurement(
        self,
        function: MeasurementFunction,
        range_value: Optional[float] = None,
        resolution: Optional[float] = None
    ):
        """
        Configure measurement function.

        Args:
            function: Measurement function to configure
            range_value: Measurement range (None for auto)
            resolution: Measurement resolution (None for default)
        """
        try:
            self.current_function = function
            cmd = f"CONF:{function.value}"

            # Add range and resolution if specified
            if range_value is not None:
                self.auto_range = False
                self.range_value = range_value
                if resolution is not None:
                    cmd += f" {range_value},{resolution}"
                else:
                    cmd += f" {range_value}"
            else:
                self.auto_range = True
                self.range_value = None

            self.write(cmd)

            logger.debug(f"Configured for {function.name}")
        except Exception as e:
            raise InstrumentError(f"Failed to configure measurement: {e}")

    def set_range(self, range_value: Optional[float] = None):
        """
        Set measurement range.

        Args:
            range_value: Range value (None for auto range)
        """
        try:
            function_cmd = self.current_function.value

            if range_value is None:
                # Enable auto range
                self.write(f"{function_cmd}:RANG:AUTO ON")
                self.auto_range = True
                self.range_value = None
            else:
                # Set fixed range
                self.write(f"{function_cmd}:RANG {range_value}")
                self.write(f"{function_cmd}:RANG:AUTO OFF")
                self.auto_range = False
                self.range_value = range_value

            logger.debug(f"Range set to {range_value or 'AUTO'}")
        except Exception as e:
            raise InstrumentError(f"Failed to set range: {e}")

    def set_nplc(self, nplc: float):
        """
        Set integration time in number of power line cycles.

        Args:
            nplc: Integration time (0.001 to 100 PLC)
                 Higher = more accurate but slower
        """
        try:
            function_cmd = self.current_function.value
            self.write(f"{function_cmd}:NPLC {nplc}")
            self.nplc = nplc

            logger.debug(f"NPLC set to {nplc}")
        except Exception as e:
            logger.warning(f"Could not set NPLC: {e}")

    def measure(self) -> float:
        """
        Perform single measurement with current configuration.

        Returns:
            Measurement value
        """
        try:
            # Use READ? for configured measurement
            result = self.query("READ?")
            value = float(result)

            # Track for statistics if enabled
            if self._stats_enabled:
                self._measurements.append(value)

            logger.debug(f"Measurement: {value}")
            return value

        except ValueError as e:
            raise InstrumentError(f"Invalid measurement response: {result}")
        except Exception as e:
            raise InstrumentError(f"Measurement failed: {e}")

    def measure_function(self, function: MeasurementFunction) -> float:
        """
        Quick measurement with specified function.

        Args:
            function: Measurement function

        Returns:
            Measurement value
        """
        try:
            # Use MEAS: command for one-shot measurement
            cmd = f"MEAS:{function.value}?"
            result = self.query(cmd)
            value = float(result)

            logger.debug(f"Quick {function.name}: {value}")
            return value

        except Exception as e:
            raise InstrumentError(f"Quick measurement failed: {e}")

    def enable_statistics(self, enable: bool = True):
        """
        Enable/disable measurement statistics tracking.

        Args:
            enable: True to enable statistics
        """
        self._stats_enabled = enable
        if enable:
            self._measurements = []
        logger.debug(f"Statistics {'enabled' if enable else 'disabled'}")

    def get_statistics(self) -> Dict[str, float]:
        """
        Get measurement statistics.

        Returns:
            Dictionary with min, max, mean, std, count
        """
        if not self._measurements:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'std': 0,
            }

        import numpy as np

        return {
            'count': len(self._measurements),
            'min': float(np.min(self._measurements)),
            'max': float(np.max(self._measurements)),
            'mean': float(np.mean(self._measurements)),
            'std': float(np.std(self._measurements)),
        }

    def clear_statistics(self):
        """Clear statistics buffer"""
        self._measurements = []
        logger.debug("Statistics cleared")

    def set_trigger_source(self, source: str = 'immediate'):
        """
        Set trigger source.

        Args:
            source: 'immediate', 'bus', or 'external'
        """
        try:
            source_map = {
                'immediate': 'IMM',
                'bus': 'BUS',
                'external': 'EXT',
            }
            cmd = source_map.get(source.lower(), 'IMM')
            self.write(f"TRIG:SOUR {cmd}")

            logger.debug(f"Trigger source set to {source}")
        except Exception as e:
            logger.warning(f"Could not set trigger source: {e}")

    def trigger(self):
        """Send software trigger"""
        self.write("*TRG")

    def initiate(self):
        """Initiate measurement (wait for trigger)"""
        self.write("INIT")

    def fetch(self) -> float:
        """
        Fetch last measurement without triggering new one.

        Returns:
            Last measurement value
        """
        try:
            result = self.query("FETC?")
            return float(result)
        except Exception as e:
            raise InstrumentError(f"Fetch failed: {e}")

    def set_math_null(self, enable: bool = True, reference: Optional[float] = None):
        """
        Enable null (relative) measurement.

        Args:
            enable: True to enable null function
            reference: Reference value (uses current reading if None)
        """
        try:
            if enable:
                if reference is None:
                    # Use current reading as reference
                    reference = self.measure()

                self.write(f"CALC:NULL:OFFS {reference}")
                self.write("CALC:FUNC NULL")
                self.write("CALC:STAT ON")
            else:
                self.write("CALC:STAT OFF")

            logger.debug(f"Math null {'enabled' if enable else 'disabled'}")
        except Exception as e:
            logger.warning(f"Could not configure math null: {e}")

    def set_limit_test(
        self,
        enable: bool = True,
        lower: float = -float('inf'),
        upper: float = float('inf')
    ):
        """
        Configure limit test (pass/fail).

        Args:
            enable: True to enable limit test
            lower: Lower limit
            upper: Upper limit
        """
        try:
            if enable:
                self.write(f"CALC:LIM:LOW {lower}")
                self.write(f"CALC:LIM:UPP {upper}")
                self.write("CALC:FUNC LIM")
                self.write("CALC:STAT ON")
            else:
                self.write("CALC:STAT OFF")

            logger.debug(f"Limit test {'enabled' if enable else 'disabled'}")
        except Exception as e:
            logger.warning(f"Could not configure limit test: {e}")

    def beep(self):
        """Sound beeper (if supported)"""
        try:
            self.write("SYST:BEEP")
        except Exception as e:
            logger.debug(f"Beep not supported: {e}")

    def set_display_text(self, text: str = ""):
        """
        Set custom text on display.

        Args:
            text: Text to display (empty to clear)
        """
        try:
            if text:
                self.write(f"DISP:TEXT '{text}'")
            else:
                self.write("DISP:TEXT:CLE")
        except Exception as e:
            logger.debug(f"Display text not supported: {e}")

    def set_display_enabled(self, enable: bool = True):
        """
        Enable/disable front panel display.

        Args:
            enable: True to enable display
        """
        try:
            state = "ON" if enable else "OFF"
            self.write(f"DISP {state}")
        except Exception as e:
            logger.debug(f"Display control not supported: {e}")
