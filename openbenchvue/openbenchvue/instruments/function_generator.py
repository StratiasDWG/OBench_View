"""
Function/Waveform Generator Driver

Supports standard waveform generation: sine, square, ramp, pulse, arbitrary.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional
from enum import Enum

from .base import BaseInstrument, InstrumentType, InstrumentError

logger = logging.getLogger(__name__)


class WaveformType(Enum):
    """Standard waveform types"""
    SINE = "SIN"
    SQUARE = "SQU"
    RAMP = "RAMP"
    PULSE = "PULS"
    NOISE = "NOIS"
    DC = "DC"
    ARBITRARY = "ARB"


class ModulationType(Enum):
    """Modulation types"""
    AM = "AM"
    FM = "FM"
    PM = "PM"
    PWM = "PWM"
    FSK = "FSK"


class FunctionGenerator(BaseInstrument):
    """
    Function/Waveform Generator driver.

    Provides BenchVue-like signal generation:
    - Standard waveforms (sine, square, ramp, pulse)
    - Arbitrary waveforms
    - Modulation (AM, FM, PM, PWM, FSK)
    - Burst mode
    - Sweep mode
    - Dual channel support
    """

    INSTRUMENT_TYPE = InstrumentType.FUNCTION_GENERATOR
    SUPPORTED_MODELS = [
        r'33\d{3}[AB]?',  # Keysight 33xxx series
        r'EDU33\d{3}[AB]?',  # Educational function generators
        r'SDG\d{4}',  # Generic signal generator
    ]

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        self.num_channels = 1
        self.channels = [1]

        # Current settings
        self.waveform = {}
        self.frequency = {}
        self.amplitude = {}
        self.offset = {}
        self.phase = {}

    def initialize(self):
        """Initialize function generator"""
        try:
            self.clear()
            self.reset()

            # Detect channels
            self._detect_channels()

            # Set default waveform
            for channel in self.channels:
                self.set_waveform(
                    channel=channel,
                    waveform=WaveformType.SINE,
                    frequency=1000.0,
                    amplitude=1.0,
                    offset=0.0
                )

            logger.info(f"Function generator initialized with {self.num_channels} channels")

        except Exception as e:
            logger.error(f"Function generator initialization failed: {e}")
            raise

    def _detect_channels(self):
        """Detect available channels"""
        try:
            # Try dual channel operation
            try:
                self.query("SOUR2:FREQ?")
                self.num_channels = 2
                self.channels = [1, 2]
            except:
                self.num_channels = 1
                self.channels = [1]

        except Exception as e:
            logger.warning(f"Channel detection failed: {e}")
            self.num_channels = 1
            self.channels = [1]

    def get_capabilities(self) -> Dict[str, Any]:
        """Get function generator capabilities"""
        return {
            'channels': self.num_channels,
            'waveforms': [wf.name for wf in WaveformType],
            'modulation': [mod.name for mod in ModulationType],
            'max_frequency': 'Unknown',  # Would query from instrument
            'max_amplitude': 'Unknown',
            'features': [
                'burst',
                'sweep',
                'arbitrary',
                'modulation',
                'sync_output',
            ]
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current generator status"""
        status = {
            'channels': {}
        }

        for channel in self.channels:
            try:
                status['channels'][channel] = {
                    'waveform': self.waveform.get(channel, 'UNKNOWN'),
                    'frequency': self.frequency.get(channel, 0),
                    'amplitude': self.amplitude.get(channel, 0),
                    'offset': self.offset.get(channel, 0),
                }
            except Exception as e:
                logger.debug(f"Could not get status for channel {channel}: {e}")

        return status

    def _source_cmd(self, channel: int) -> str:
        """Get source command prefix for channel"""
        if self.num_channels > 1:
            return f"SOUR{channel}"
        else:
            return "SOUR"

    def set_waveform(
        self,
        channel: int,
        waveform: WaveformType,
        frequency: float = None,
        amplitude: float = None,
        offset: float = None,
        phase: float = None
    ):
        """
        Configure waveform output.

        Args:
            channel: Channel number
            waveform: Waveform type
            frequency: Frequency in Hz (None to keep current)
            amplitude: Amplitude in Vpp (None to keep current)
            offset: DC offset in V (None to keep current)
            phase: Phase in degrees (None to keep current)
        """
        try:
            src = self._source_cmd(channel)

            # Set waveform type
            self.write(f"{src}:FUNC {waveform.value}")
            self.waveform[channel] = waveform.name

            # Set parameters if specified
            if frequency is not None:
                self.write(f"{src}:FREQ {frequency}")
                self.frequency[channel] = frequency

            if amplitude is not None:
                self.write(f"{src}:VOLT {amplitude}")
                self.amplitude[channel] = amplitude

            if offset is not None:
                self.write(f"{src}:VOLT:OFFS {offset}")
                self.offset[channel] = offset

            if phase is not None:
                self.write(f"{src}:PHAS {phase}")
                self.phase[channel] = phase

            logger.debug(f"Channel {channel} configured: {waveform.name}, {frequency}Hz, {amplitude}Vpp")

        except Exception as e:
            raise InstrumentError(f"Failed to set waveform: {e}")

    def set_frequency(self, channel: int, frequency: float):
        """
        Set output frequency.

        Args:
            channel: Channel number
            frequency: Frequency in Hz
        """
        try:
            src = self._source_cmd(channel)
            self.write(f"{src}:FREQ {frequency}")
            self.frequency[channel] = frequency

            logger.debug(f"Channel {channel} frequency set to {frequency}Hz")

        except Exception as e:
            raise InstrumentError(f"Failed to set frequency: {e}")

    def set_amplitude(self, channel: int, amplitude: float, unit: str = 'VPP'):
        """
        Set output amplitude.

        Args:
            channel: Channel number
            amplitude: Amplitude value
            unit: Unit ('VPP', 'VRMS', 'DBM')
        """
        try:
            src = self._source_cmd(channel)
            self.write(f"{src}:VOLT {amplitude} {unit}")
            self.amplitude[channel] = amplitude

            logger.debug(f"Channel {channel} amplitude set to {amplitude}{unit}")

        except Exception as e:
            raise InstrumentError(f"Failed to set amplitude: {e}")

    def set_offset(self, channel: int, offset: float):
        """
        Set DC offset.

        Args:
            channel: Channel number
            offset: DC offset in volts
        """
        try:
            src = self._source_cmd(channel)
            self.write(f"{src}:VOLT:OFFS {offset}")
            self.offset[channel] = offset

            logger.debug(f"Channel {channel} offset set to {offset}V")

        except Exception as e:
            raise InstrumentError(f"Failed to set offset: {e}")

    def set_phase(self, channel: int, phase: float):
        """
        Set waveform phase.

        Args:
            channel: Channel number
            phase: Phase in degrees
        """
        try:
            src = self._source_cmd(channel)
            self.write(f"{src}:PHAS {phase}")
            self.phase[channel] = phase

            logger.debug(f"Channel {channel} phase set to {phase}°")

        except Exception as e:
            raise InstrumentError(f"Failed to set phase: {e}")

    def set_duty_cycle(self, channel: int, duty: float):
        """
        Set duty cycle for square/pulse waveforms.

        Args:
            channel: Channel number
            duty: Duty cycle percentage (0-100)
        """
        try:
            src = self._source_cmd(channel)

            # For square wave
            if self.waveform.get(channel) == 'SQUARE':
                self.write(f"{src}:FUNC:SQU:DCYC {duty}")
            # For pulse
            elif self.waveform.get(channel) == 'PULSE':
                self.write(f"{src}:FUNC:PULS:DCYC {duty}")

            logger.debug(f"Channel {channel} duty cycle set to {duty}%")

        except Exception as e:
            logger.warning(f"Could not set duty cycle: {e}")

    def set_output(self, channel: int, enable: bool):
        """
        Enable/disable output.

        Args:
            channel: Channel number
            enable: True to enable output
        """
        try:
            if self.num_channels > 1:
                cmd = f"OUTP{channel}"
            else:
                cmd = "OUTP"

            state = "ON" if enable else "OFF"
            self.write(f"{cmd} {state}")

            logger.info(f"Channel {channel} output {'enabled' if enable else 'disabled'}")

        except Exception as e:
            raise InstrumentError(f"Failed to set output: {e}")

    def set_modulation(
        self,
        channel: int,
        mod_type: ModulationType,
        enable: bool = True,
        **parameters
    ):
        """
        Configure modulation.

        Args:
            channel: Channel number
            mod_type: Modulation type
            enable: True to enable modulation
            **parameters: Modulation-specific parameters
                - depth: Modulation depth (%)
                - frequency: Modulation frequency (Hz)
                - deviation: Frequency deviation for FM (Hz)
        """
        try:
            src = self._source_cmd(channel)

            if enable:
                # Configure modulation type
                if mod_type == ModulationType.AM:
                    depth = parameters.get('depth', 50)
                    freq = parameters.get('frequency', 100)
                    self.write(f"{src}:AM:DEPT {depth}")
                    self.write(f"{src}:AM:INT:FREQ {freq}")
                    self.write(f"{src}:AM:STAT ON")

                elif mod_type == ModulationType.FM:
                    deviation = parameters.get('deviation', 1000)
                    freq = parameters.get('frequency', 100)
                    self.write(f"{src}:FM:DEV {deviation}")
                    self.write(f"{src}:FM:INT:FREQ {freq}")
                    self.write(f"{src}:FM:STAT ON")

                elif mod_type == ModulationType.PM:
                    deviation = parameters.get('deviation', 90)
                    freq = parameters.get('frequency', 100)
                    self.write(f"{src}:PM:DEV {deviation}")
                    self.write(f"{src}:PM:INT:FREQ {freq}")
                    self.write(f"{src}:PM:STAT ON")

                logger.debug(f"Channel {channel} {mod_type.name} modulation enabled")
            else:
                # Disable all modulation
                self.write(f"{src}:AM:STAT OFF")
                self.write(f"{src}:FM:STAT OFF")
                self.write(f"{src}:PM:STAT OFF")

                logger.debug(f"Channel {channel} modulation disabled")

        except Exception as e:
            raise InstrumentError(f"Failed to configure modulation: {e}")

    def set_burst(
        self,
        channel: int,
        enable: bool = True,
        cycles: int = 1,
        mode: str = 'triggered'
    ):
        """
        Configure burst mode.

        Args:
            channel: Channel number
            enable: True to enable burst
            cycles: Number of cycles per burst
            mode: 'triggered' or 'gated'
        """
        try:
            src = self._source_cmd(channel)

            if enable:
                self.write(f"{src}:BURS:NCYC {cycles}")
                self.write(f"{src}:BURS:MODE {mode.upper()}")
                self.write(f"{src}:BURS:STAT ON")

                logger.debug(f"Channel {channel} burst enabled: {cycles} cycles, {mode}")
            else:
                self.write(f"{src}:BURS:STAT OFF")
                logger.debug(f"Channel {channel} burst disabled")

        except Exception as e:
            raise InstrumentError(f"Failed to configure burst: {e}")

    def trigger(self, channel: int = None):
        """
        Send manual trigger.

        Args:
            channel: Channel to trigger (None for all)
        """
        try:
            if channel:
                self.write(f"TRIG{channel}")
            else:
                self.write("*TRG")

            logger.debug(f"Trigger sent to channel {channel or 'all'}")

        except Exception as e:
            logger.warning(f"Could not trigger: {e}")

    def load_arbitrary_waveform(
        self,
        channel: int,
        data: np.ndarray,
        name: str = "ARB"
    ):
        """
        Load arbitrary waveform data.

        Args:
            channel: Channel number
            data: Waveform data array (normalized -1 to 1)
            name: Waveform name
        """
        try:
            src = self._source_cmd(channel)

            # Normalize data
            data_normalized = np.clip(data, -1, 1)

            # Convert to instrument format (typically 14-bit or 16-bit)
            # This is highly instrument-specific
            # For demonstration, assume simple ASCII format
            data_str = ','.join([str(v) for v in data_normalized])

            self.write(f"{src}:DATA:ARB {name},{data_str}")
            self.write(f"{src}:FUNC ARB")
            self.write(f"{src}:FUNC:ARB {name}")

            logger.debug(f"Loaded arbitrary waveform '{name}' with {len(data)} points")

        except Exception as e:
            raise InstrumentError(f"Failed to load arbitrary waveform: {e}")

    def sync_channels(self, enable: bool = True):
        """
        Synchronize multiple channels (phase lock).

        Args:
            enable: True to enable sync
        """
        try:
            if self.num_channels > 1:
                state = "ON" if enable else "OFF"
                self.write(f"PHAS:SYNC {state}")

                logger.debug(f"Channel sync {'enabled' if enable else 'disabled'}")

        except Exception as e:
            logger.warning(f"Could not configure sync: {e}")
