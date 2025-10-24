"""
Oscilloscope Driver

Supports waveform capture, triggering, measurements, and analysis.
Mimics BenchVue's Oscilloscope app functionality.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from .base import BaseInstrument, InstrumentType, InstrumentError

logger = logging.getLogger(__name__)


class TriggerMode(Enum):
    """Trigger modes"""
    EDGE = "EDGE"
    PULSE = "PULSE"
    PATTERN = "PATTERN"
    TV = "TV"
    AUTO = "AUTO"


class TriggerSlope(Enum):
    """Trigger slope"""
    POSITIVE = "POS"
    NEGATIVE = "NEG"
    EITHER = "EITH"


class CouplingMode(Enum):
    """Input coupling"""
    DC = "DC"
    AC = "AC"
    GND = "GND"


@dataclass
class WaveformData:
    """Waveform data structure"""
    channel: int
    time: np.ndarray
    voltage: np.ndarray
    sample_rate: float
    time_scale: float
    voltage_scale: float
    points: int
    preamble: Dict[str, Any]


class Oscilloscope(BaseInstrument):
    """
    Oscilloscope driver with waveform capture and analysis.

    Provides BenchVue-like functionality:
    - Multi-channel waveform capture
    - Flexible triggering
    - Automated measurements
    - Cursor measurements
    - Math functions (FFT, etc.)
    - Screen capture
    """

    INSTRUMENT_TYPE = InstrumentType.OSCILLOSCOPE
    SUPPORTED_MODELS = [
        r'DSO[XZ]\d{4}[AB]?',  # Keysight InfiniiVision/Infiniium
        r'MSO[XZ]\d{4}[AB]?',  # Mixed signal scopes
        r'EDUX\d{4}[AB]?',  # Educational scopes
    ]

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        self.num_channels = 4  # Will be detected
        self.available_channels = []
        self.enabled_channels = []

        # Timebase settings
        self.time_scale = 1e-3  # seconds/div
        self.time_position = 0.0  # seconds

        # Trigger settings
        self.trigger_source = 1  # Channel 1
        self.trigger_level = 0.0
        self.trigger_mode = TriggerMode.EDGE
        self.trigger_slope = TriggerSlope.POSITIVE

    def initialize(self):
        """Initialize oscilloscope"""
        try:
            self.clear()

            # Detect number of channels
            self._detect_channels()

            # Set to known state
            self.write(":AUTOSCALE")
            logger.info(f"Oscilloscope initialized with {self.num_channels} channels")

        except Exception as e:
            logger.error(f"Oscilloscope initialization failed: {e}")
            raise

    def _detect_channels(self):
        """Detect available channels"""
        try:
            # Try to determine number of channels
            for ch in range(1, 9):  # Try up to 8 channels
                try:
                    self.query(f":CHAN{ch}:DISP?")
                    self.available_channels.append(ch)
                except:
                    break

            self.num_channels = len(self.available_channels)

            if self.num_channels == 0:
                # Assume 4 channels if detection fails
                self.num_channels = 4
                self.available_channels = [1, 2, 3, 4]

        except Exception as e:
            logger.warning(f"Channel detection failed: {e}")
            self.num_channels = 4
            self.available_channels = [1, 2, 3, 4]

    def get_capabilities(self) -> Dict[str, Any]:
        """Get oscilloscope capabilities"""
        return {
            'channels': self.num_channels,
            'bandwidth': 'Unknown',  # Would query from instrument
            'sample_rate': 'Unknown',
            'memory_depth': 'Unknown',
            'trigger_modes': [mode.name for mode in TriggerMode],
            'measurements': [
                'frequency', 'period', 'amplitude', 'peak_to_peak',
                'rise_time', 'fall_time', 'duty_cycle', 'rms',
                'mean', 'min', 'max', 'overshoot', 'preshoot'
            ],
            'math_functions': ['add', 'subtract', 'multiply', 'fft'],
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current oscilloscope status"""
        status = {
            'enabled_channels': self.enabled_channels,
            'time_scale': self.time_scale,
            'trigger_source': self.trigger_source,
            'trigger_level': self.trigger_level,
            'trigger_mode': self.trigger_mode.name,
        }

        try:
            # Query acquisition status
            status['acquiring'] = self.is_acquiring()
        except:
            pass

        return status

    def enable_channel(self, channel: int, enable: bool = True):
        """
        Enable/disable channel display.

        Args:
            channel: Channel number (1-based)
            enable: True to enable
        """
        try:
            state = "ON" if enable else "OFF"
            self.write(f":CHAN{channel}:DISP {state}")

            if enable and channel not in self.enabled_channels:
                self.enabled_channels.append(channel)
            elif not enable and channel in self.enabled_channels:
                self.enabled_channels.remove(channel)

            logger.debug(f"Channel {channel} {'enabled' if enable else 'disabled'}")
        except Exception as e:
            raise InstrumentError(f"Failed to configure channel: {e}")

    def set_channel_scale(self, channel: int, scale: float, offset: float = 0.0):
        """
        Set channel vertical scale and offset.

        Args:
            channel: Channel number
            scale: Volts per division
            offset: Vertical offset in volts
        """
        try:
            self.write(f":CHAN{channel}:SCAL {scale}")
            self.write(f":CHAN{channel}:OFFS {offset}")

            logger.debug(f"Channel {channel}: {scale}V/div, offset {offset}V")
        except Exception as e:
            raise InstrumentError(f"Failed to set channel scale: {e}")

    def set_channel_coupling(self, channel: int, coupling: CouplingMode):
        """
        Set channel coupling mode.

        Args:
            channel: Channel number
            coupling: Coupling mode (DC/AC/GND)
        """
        try:
            self.write(f":CHAN{channel}:COUP {coupling.value}")
            logger.debug(f"Channel {channel} coupling: {coupling.name}")
        except Exception as e:
            raise InstrumentError(f"Failed to set coupling: {e}")

    def set_channel_probe(self, channel: int, attenuation: float = 1.0):
        """
        Set channel probe attenuation.

        Args:
            channel: Channel number
            attenuation: Probe attenuation factor (1, 10, 100, etc.)
        """
        try:
            self.write(f":CHAN{channel}:PROB {attenuation}")
            logger.debug(f"Channel {channel} probe: {attenuation}X")
        except Exception as e:
            logger.warning(f"Could not set probe attenuation: {e}")

    def set_timebase(self, scale: float, position: float = 0.0):
        """
        Set horizontal timebase.

        Args:
            scale: Time per division (seconds)
            position: Horizontal position/delay (seconds)
        """
        try:
            self.write(f":TIM:SCAL {scale}")
            self.write(f":TIM:POS {position}")

            self.time_scale = scale
            self.time_position = position

            logger.debug(f"Timebase: {scale}s/div, position {position}s")
        except Exception as e:
            raise InstrumentError(f"Failed to set timebase: {e}")

    def set_trigger(
        self,
        source: int = 1,
        level: float = 0.0,
        slope: TriggerSlope = TriggerSlope.POSITIVE,
        mode: TriggerMode = TriggerMode.EDGE
    ):
        """
        Configure trigger.

        Args:
            source: Trigger source channel
            level: Trigger level in volts
            slope: Trigger slope
            mode: Trigger mode
        """
        try:
            # Set trigger mode
            self.write(f":TRIG:MODE {mode.value}")

            # For edge trigger
            if mode == TriggerMode.EDGE:
                self.write(f":TRIG:EDGE:SOUR CHAN{source}")
                self.write(f":TRIG:EDGE:LEV {level}")
                self.write(f":TRIG:EDGE:SLOP {slope.value}")

            self.trigger_source = source
            self.trigger_level = level
            self.trigger_mode = mode
            self.trigger_slope = slope

            logger.debug(f"Trigger: CH{source}, {level}V, {slope.name}")
        except Exception as e:
            raise InstrumentError(f"Failed to configure trigger: {e}")

    def autoscale(self):
        """Perform autoscale"""
        try:
            self.write(":AUTOSCALE")
            logger.info("Autoscale executed")
        except Exception as e:
            raise InstrumentError(f"Autoscale failed: {e}")

    def single(self):
        """Trigger single acquisition"""
        try:
            self.write(":SINGLE")
            logger.debug("Single acquisition triggered")
        except Exception as e:
            raise InstrumentError(f"Single trigger failed: {e}")

    def run(self):
        """Start continuous acquisition"""
        try:
            self.write(":RUN")
            logger.debug("Continuous acquisition started")
        except Exception as e:
            raise InstrumentError(f"Run failed: {e}")

    def stop(self):
        """Stop acquisition"""
        try:
            self.write(":STOP")
            logger.debug("Acquisition stopped")
        except Exception as e:
            raise InstrumentError(f"Stop failed: {e}")

    def is_acquiring(self) -> bool:
        """Check if scope is acquiring"""
        try:
            # Query operation status register
            status = self.query(":OPER:COND?")
            # Bit 3 indicates acquiring
            return bool(int(status) & 0x08)
        except:
            return False

    def capture_waveform(self, channel: int) -> WaveformData:
        """
        Capture waveform from specified channel.

        Args:
            channel: Channel number to capture

        Returns:
            WaveformData object with time and voltage arrays
        """
        try:
            # Set waveform source
            self.write(f":WAV:SOUR CHAN{channel}")

            # Set format to binary for speed
            self.write(":WAV:FORM BYTE")

            # Get preamble (waveform metadata)
            preamble_str = self.query(":WAV:PRE?")
            preamble = self._parse_preamble(preamble_str)

            # Get waveform data
            self.write(":WAV:DATA?")
            raw_data = self._instrument.read_raw()

            # Parse binary data (skip header)
            data = np.frombuffer(raw_data[10:], dtype=np.int8)

            # Convert to voltage using preamble scaling
            voltage = (data - preamble['yreference']) * preamble['yincrement'] + preamble['yorigin']

            # Generate time array
            time = np.arange(len(voltage)) * preamble['xincrement'] + preamble['xorigin']

            waveform = WaveformData(
                channel=channel,
                time=time,
                voltage=voltage,
                sample_rate=1.0 / preamble['xincrement'],
                time_scale=self.time_scale,
                voltage_scale=preamble['yincrement'],
                points=len(voltage),
                preamble=preamble
            )

            logger.debug(f"Captured {len(voltage)} points from channel {channel}")
            return waveform

        except Exception as e:
            raise InstrumentError(f"Waveform capture failed: {e}")

    def _parse_preamble(self, preamble_str: str) -> Dict[str, Any]:
        """Parse waveform preamble"""
        try:
            parts = preamble_str.split(',')

            return {
                'format': int(parts[0]),
                'type': int(parts[1]),
                'points': int(parts[2]),
                'count': int(parts[3]),
                'xincrement': float(parts[4]),
                'xorigin': float(parts[5]),
                'xreference': float(parts[6]),
                'yincrement': float(parts[7]),
                'yorigin': float(parts[8]),
                'yreference': float(parts[9]),
            }
        except Exception as e:
            logger.error(f"Failed to parse preamble: {e}")
            # Return defaults
            return {
                'xincrement': 1e-6,
                'xorigin': 0,
                'xreference': 0,
                'yincrement': 0.001,
                'yorigin': 0,
                'yreference': 128,
                'points': 0,
            }

    def measure(self, measurement: str, channel: int) -> float:
        """
        Perform automated measurement.

        Args:
            measurement: Measurement type (frequency, amplitude, etc.)
            channel: Channel number

        Returns:
            Measurement value
        """
        try:
            # Map common measurement names to SCPI commands
            meas_map = {
                'frequency': 'FREQ',
                'period': 'PER',
                'amplitude': 'VAMP',
                'peak_to_peak': 'VPP',
                'max': 'VMAX',
                'min': 'VMIN',
                'mean': 'VAVG',
                'rms': 'VRMS',
                'rise_time': 'RIS',
                'fall_time': 'FALL',
                'duty_cycle': 'DUTY',
                'overshoot': 'OVER',
                'preshoot': 'PRE',
            }

            meas_cmd = meas_map.get(measurement.lower(), measurement.upper())
            result = self.query(f":MEAS:{meas_cmd}? CHAN{channel}")

            value = float(result)
            logger.debug(f"Measurement {measurement} on CH{channel}: {value}")

            return value

        except Exception as e:
            raise InstrumentError(f"Measurement failed: {e}")

    def get_all_measurements(self, channel: int) -> Dict[str, float]:
        """
        Get all standard measurements for a channel.

        Args:
            channel: Channel number

        Returns:
            Dictionary of measurement results
        """
        measurements = {}
        measurement_types = [
            'frequency', 'period', 'amplitude', 'peak_to_peak',
            'max', 'min', 'mean', 'rms'
        ]

        for meas_type in measurement_types:
            try:
                measurements[meas_type] = self.measure(meas_type, channel)
            except Exception as e:
                logger.debug(f"Could not measure {meas_type}: {e}")
                measurements[meas_type] = float('nan')

        return measurements

    def get_screenshot(self, format: str = 'PNG') -> bytes:
        """
        Capture screenshot of scope display.

        Args:
            format: Image format (PNG, BMP, etc.)

        Returns:
            Binary image data
        """
        try:
            self.write(f":DISP:DATA? {format}")
            image_data = self._instrument.read_raw()

            logger.debug(f"Captured screenshot ({len(image_data)} bytes)")
            return image_data

        except Exception as e:
            raise InstrumentError(f"Screenshot capture failed: {e}")

    def set_math_function(self, function: str, sources: List[int]):
        """
        Configure math function.

        Args:
            function: Math function (add, subtract, multiply, fft)
            sources: List of source channels
        """
        try:
            if function.lower() == 'add':
                self.write(f":FUNC1:OPER ADD")
            elif function.lower() == 'subtract':
                self.write(f":FUNC1:OPER SUBT")
            elif function.lower() == 'multiply':
                self.write(f":FUNC1:OPER MULT")
            elif function.lower() == 'fft':
                self.write(f":FUNC1:MODE FFT")

            # Set sources
            if len(sources) >= 1:
                self.write(f":FUNC1:SOUR1 CHAN{sources[0]}")
            if len(sources) >= 2:
                self.write(f":FUNC1:SOUR2 CHAN{sources[1]}")

            self.write(":FUNC1:DISP ON")

            logger.debug(f"Math function {function} configured")

        except Exception as e:
            logger.warning(f"Could not configure math function: {e}")
