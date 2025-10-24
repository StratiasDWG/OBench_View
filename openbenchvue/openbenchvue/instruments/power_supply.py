"""
Power Supply Driver

Supports programmable DC power supplies with voltage/current control,
output enable/disable, and monitoring features.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from .base import BaseInstrument, InstrumentType, InstrumentError

logger = logging.getLogger(__name__)


class OutputMode(Enum):
    """Output regulation mode"""
    CONSTANT_VOLTAGE = "CV"
    CONSTANT_CURRENT = "CC"
    UNREGULATED = "UR"


@dataclass
class ChannelState:
    """Power supply channel state"""
    channel: int
    voltage_set: float
    current_set: float
    voltage_measured: float
    current_measured: float
    power: float
    enabled: bool
    mode: OutputMode


class PowerSupply(BaseInstrument):
    """
    Programmable Power Supply driver.

    Provides BenchVue-like power supply control:
    - Multi-channel voltage/current control
    - Output enable/disable
    - Over-voltage/over-current protection
    - Power measurements
    - Sequencing and lists
    - Remote sensing
    """

    INSTRUMENT_TYPE = InstrumentType.POWER_SUPPLY
    SUPPORTED_MODELS = [
        r'E36\d{3}[AB]?',  # Keysight E3600 series
        r'N\d{4}[AB]X',  # Keysight N6700/N7900 series
        r'DP\d{3,4}',  # Generic power supply
    ]

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        self.num_channels = 1
        self.channels: List[int] = []
        self.channel_states: Dict[int, ChannelState] = {}

        # Capabilities
        self.max_voltage = {}
        self.max_current = {}
        self.max_power = {}

    def initialize(self):
        """Initialize power supply"""
        try:
            self.clear()

            # Detect channels
            self._detect_channels()

            # Query capabilities
            self._query_capabilities()

            # Disable all outputs initially for safety
            for channel in self.channels:
                self.set_output(channel, False)

            logger.info(f"Power supply initialized with {self.num_channels} channels")

        except Exception as e:
            logger.error(f"Power supply initialization failed: {e}")
            raise

    def _detect_channels(self):
        """Detect available channels"""
        try:
            # Try to query number of channels
            try:
                # Some models support channel count query
                result = self.query("SYST:CHAN:COUN?")
                self.num_channels = int(result)
            except:
                # Try each channel until error
                for ch in range(1, 9):
                    try:
                        self.query(f"INST:SEL? (@{ch})")
                        self.channels.append(ch)
                    except:
                        break

                if self.channels:
                    self.num_channels = len(self.channels)
                else:
                    # Assume single channel
                    self.num_channels = 1
                    self.channels = [1]

            if not self.channels:
                self.channels = list(range(1, self.num_channels + 1))

        except Exception as e:
            logger.warning(f"Channel detection failed: {e}")
            self.num_channels = 1
            self.channels = [1]

    def _query_capabilities(self):
        """Query instrument capabilities"""
        for channel in self.channels:
            try:
                # Select channel
                self._select_channel(channel)

                # Query limits
                try:
                    self.max_voltage[channel] = float(self.query("VOLT? MAX"))
                except:
                    self.max_voltage[channel] = 30.0  # Default

                try:
                    self.max_current[channel] = float(self.query("CURR? MAX"))
                except:
                    self.max_current[channel] = 5.0  # Default

                try:
                    self.max_power[channel] = float(self.query("POW? MAX"))
                except:
                    self.max_power[channel] = self.max_voltage[channel] * self.max_current[channel]

            except Exception as e:
                logger.warning(f"Could not query capabilities for channel {channel}: {e}")

    def _select_channel(self, channel: int):
        """Select active channel"""
        try:
            # Different command formats for different models
            try:
                self.write(f"INST:SEL CH{channel}")
            except:
                try:
                    self.write(f"INST:NSEL {channel}")
                except:
                    # Some models use channels in command directly
                    pass
        except Exception as e:
            logger.debug(f"Channel selection may not be required: {e}")

    def get_capabilities(self) -> Dict[str, Any]:
        """Get power supply capabilities"""
        return {
            'channels': self.num_channels,
            'max_voltage': self.max_voltage,
            'max_current': self.max_current,
            'max_power': self.max_power,
            'features': [
                'ovp', 'ocp', 'opp',  # Protection features
                'remote_sensing',
                'sequencing',
                'data_logging'
            ]
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current power supply status"""
        status = {
            'channels': {},
            'errors': []
        }

        for channel in self.channels:
            try:
                state = self.get_channel_state(channel)
                status['channels'][channel] = {
                    'voltage': state.voltage_measured,
                    'current': state.current_measured,
                    'power': state.power,
                    'enabled': state.enabled,
                    'mode': state.mode.name,
                }
            except Exception as e:
                logger.debug(f"Could not get state for channel {channel}: {e}")

        return status

    def set_voltage(self, channel: int, voltage: float):
        """
        Set output voltage.

        Args:
            channel: Channel number
            voltage: Voltage in volts
        """
        try:
            # Check limits
            max_v = self.max_voltage.get(channel, float('inf'))
            if voltage > max_v:
                raise ValueError(f"Voltage {voltage}V exceeds maximum {max_v}V")

            self._select_channel(channel)
            self.write(f"VOLT {voltage}")

            logger.debug(f"Channel {channel} voltage set to {voltage}V")

        except Exception as e:
            raise InstrumentError(f"Failed to set voltage: {e}")

    def set_current(self, channel: int, current: float):
        """
        Set current limit.

        Args:
            channel: Channel number
            current: Current limit in amperes
        """
        try:
            # Check limits
            max_i = self.max_current.get(channel, float('inf'))
            if current > max_i:
                raise ValueError(f"Current {current}A exceeds maximum {max_i}A")

            self._select_channel(channel)
            self.write(f"CURR {current}")

            logger.debug(f"Channel {channel} current set to {current}A")

        except Exception as e:
            raise InstrumentError(f"Failed to set current: {e}")

    def set_output(self, channel: int, enable: bool):
        """
        Enable/disable output.

        Args:
            channel: Channel number
            enable: True to enable output
        """
        try:
            self._select_channel(channel)
            state = "ON" if enable else "OFF"
            self.write(f"OUTP {state}")

            logger.info(f"Channel {channel} output {'enabled' if enable else 'disabled'}")

        except Exception as e:
            raise InstrumentError(f"Failed to set output state: {e}")

    def measure_voltage(self, channel: int) -> float:
        """
        Measure actual output voltage.

        Args:
            channel: Channel number

        Returns:
            Measured voltage in volts
        """
        try:
            self._select_channel(channel)
            result = self.query("MEAS:VOLT?")
            return float(result)

        except Exception as e:
            raise InstrumentError(f"Failed to measure voltage: {e}")

    def measure_current(self, channel: int) -> float:
        """
        Measure actual output current.

        Args:
            channel: Channel number

        Returns:
            Measured current in amperes
        """
        try:
            self._select_channel(channel)
            result = self.query("MEAS:CURR?")
            return float(result)

        except Exception as e:
            raise InstrumentError(f"Failed to measure current: {e}")

    def measure_power(self, channel: int) -> float:
        """
        Measure actual output power.

        Args:
            channel: Channel number

        Returns:
            Measured power in watts
        """
        try:
            voltage = self.measure_voltage(channel)
            current = self.measure_current(channel)
            return voltage * current

        except Exception as e:
            raise InstrumentError(f"Failed to measure power: {e}")

    def get_channel_state(self, channel: int) -> ChannelState:
        """
        Get complete channel state.

        Args:
            channel: Channel number

        Returns:
            ChannelState object
        """
        try:
            self._select_channel(channel)

            # Get setpoints
            v_set = float(self.query("VOLT?"))
            i_set = float(self.query("CURR?"))

            # Get measurements
            v_meas = self.measure_voltage(channel)
            i_meas = self.measure_current(channel)
            power = v_meas * i_meas

            # Get output state
            output_state = self.query("OUTP?")
            enabled = output_state.strip() in ['1', 'ON']

            # Determine mode (CV/CC)
            # If measured current is near limit, in CC mode
            mode = OutputMode.CONSTANT_VOLTAGE
            if i_meas > 0.95 * i_set:
                mode = OutputMode.CONSTANT_CURRENT

            state = ChannelState(
                channel=channel,
                voltage_set=v_set,
                current_set=i_set,
                voltage_measured=v_meas,
                current_measured=i_meas,
                power=power,
                enabled=enabled,
                mode=mode
            )

            self.channel_states[channel] = state
            return state

        except Exception as e:
            raise InstrumentError(f"Failed to get channel state: {e}")

    def set_ovp(self, channel: int, voltage: float, enable: bool = True):
        """
        Set over-voltage protection.

        Args:
            channel: Channel number
            voltage: OVP threshold in volts
            enable: True to enable OVP
        """
        try:
            self._select_channel(channel)
            self.write(f"VOLT:PROT {voltage}")

            if enable:
                self.write("VOLT:PROT:STAT ON")
            else:
                self.write("VOLT:PROT:STAT OFF")

            logger.debug(f"Channel {channel} OVP set to {voltage}V")

        except Exception as e:
            logger.warning(f"Could not set OVP: {e}")

    def set_ocp(self, channel: int, current: float, enable: bool = True):
        """
        Set over-current protection.

        Args:
            channel: Channel number
            current: OCP threshold in amperes
            enable: True to enable OCP
        """
        try:
            self._select_channel(channel)
            self.write(f"CURR:PROT {current}")

            if enable:
                self.write("CURR:PROT:STAT ON")
            else:
                self.write("CURR:PROT:STAT OFF")

            logger.debug(f"Channel {channel} OCP set to {current}A")

        except Exception as e:
            logger.warning(f"Could not set OCP: {e}")

    def set_remote_sense(self, channel: int, enable: bool = True):
        """
        Enable/disable remote voltage sensing.

        Args:
            channel: Channel number
            enable: True for remote sensing
        """
        try:
            self._select_channel(channel)
            state = "ON" if enable else "OFF"
            self.write(f"VOLT:SENS:SOUR {state}")

            logger.debug(f"Channel {channel} remote sense {'enabled' if enable else 'disabled'}")

        except Exception as e:
            logger.warning(f"Could not set remote sense: {e}")

    def set_voltage_slew_rate(self, channel: int, rate: float):
        """
        Set voltage slew rate (change rate limit).

        Args:
            channel: Channel number
            rate: Slew rate in V/s
        """
        try:
            self._select_channel(channel)
            self.write(f"VOLT:SLEW {rate}")

            logger.debug(f"Channel {channel} slew rate set to {rate}V/s")

        except Exception as e:
            logger.warning(f"Could not set slew rate: {e}")

    def track_channels(self, enable: bool = True):
        """
        Enable/disable channel tracking (all channels follow CH1).

        Args:
            enable: True to enable tracking
        """
        try:
            state = "ON" if enable else "OFF"
            self.write(f"OUTP:TRAC {state}")

            logger.debug(f"Channel tracking {'enabled' if enable else 'disabled'}")

        except Exception as e:
            logger.warning(f"Could not set tracking: {e}")

    def save_state(self, location: int):
        """
        Save current instrument state to memory.

        Args:
            location: Memory location (1-10 typically)
        """
        try:
            self.write(f"*SAV {location}")
            logger.debug(f"State saved to location {location}")

        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    def recall_state(self, location: int):
        """
        Recall instrument state from memory.

        Args:
            location: Memory location (1-10 typically)
        """
        try:
            self.write(f"*RCL {location}")
            logger.debug(f"State recalled from location {location}")

        except Exception as e:
            logger.warning(f"Could not recall state: {e}")
