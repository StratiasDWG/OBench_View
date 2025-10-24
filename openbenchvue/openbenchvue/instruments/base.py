"""
Base Instrument Classes for OpenBenchVue

Defines abstract base classes and common functionality for all instrument drivers.
Uses PyVISA for VISA-compliant instrument communication.
"""

import logging
import time
import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

import pyvisa

logger = logging.getLogger(__name__)


class InstrumentType(Enum):
    """Enumeration of supported instrument types"""
    UNKNOWN = "Unknown"
    DMM = "Digital Multimeter"
    OSCILLOSCOPE = "Oscilloscope"
    POWER_SUPPLY = "Power Supply"
    FUNCTION_GENERATOR = "Function Generator"
    POWER_ANALYZER = "Power Analyzer"
    SPECTRUM_ANALYZER = "Spectrum Analyzer"
    NETWORK_ANALYZER = "Network Analyzer"
    ARBITRARY_WAVEFORM_GENERATOR = "Arbitrary Waveform Generator"
    LOGIC_ANALYZER = "Logic Analyzer"
    GENERIC = "Generic SCPI"


@dataclass
class InstrumentIdentity:
    """Instrument identification information"""
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    resource_string: str
    instrument_type: InstrumentType
    raw_idn: str


class InstrumentError(Exception):
    """Base exception for instrument-related errors"""
    pass


class InstrumentConnectionError(InstrumentError):
    """Exception raised when instrument connection fails"""
    pass


class InstrumentCommandError(InstrumentError):
    """Exception raised when instrument command fails"""
    pass


class InstrumentTimeoutError(InstrumentError):
    """Exception raised when instrument communication times out"""
    pass


class BaseInstrument(ABC):
    """
    Abstract base class for all instrument drivers.

    Provides common VISA communication methods, error handling,
    and interface that all specific instrument classes must implement.

    This mimics BenchVue's unified instrument abstraction layer.
    """

    # Class attributes to be overridden by subclasses
    INSTRUMENT_TYPE: InstrumentType = InstrumentType.UNKNOWN
    SUPPORTED_MODELS: List[str] = []  # List of supported model strings (regex patterns)
    SCPI_TERMINATION: str = '\n'

    def __init__(self, resource_string: str, rm: pyvisa.ResourceManager = None):
        """
        Initialize instrument connection.

        Args:
            resource_string: VISA resource string (e.g., 'GPIB0::1::INSTR')
            rm: PyVISA ResourceManager instance (creates new if None)
        """
        self.resource_string = resource_string
        self._rm = rm or pyvisa.ResourceManager()
        self._instrument: Optional[pyvisa.Resource] = None
        self._identity: Optional[InstrumentIdentity] = None
        self._connected = False
        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {}

        # Connection parameters
        self.timeout = 5000  # milliseconds
        self.query_delay = 0.01  # seconds
        self.chunk_size = 20480  # bytes

    def connect(self, timeout: int = None) -> bool:
        """
        Establish connection to instrument.

        Args:
            timeout: Timeout in milliseconds (uses default if None)

        Returns:
            True if connection successful

        Raises:
            InstrumentConnectionError: If connection fails
        """
        try:
            with self._lock:
                if self._connected:
                    logger.warning(f"Already connected to {self.resource_string}")
                    return True

                logger.info(f"Connecting to {self.resource_string}...")
                self._instrument = self._rm.open_resource(self.resource_string)

                # Configure connection
                self._instrument.timeout = timeout or self.timeout
                self._instrument.query_delay = self.query_delay
                self._instrument.chunk_size = self.chunk_size

                # Set termination characters if supported
                try:
                    if hasattr(self._instrument, 'read_termination'):
                        self._instrument.read_termination = self.SCPI_TERMINATION
                    if hasattr(self._instrument, 'write_termination'):
                        self._instrument.write_termination = self.SCPI_TERMINATION
                except Exception as e:
                    logger.warning(f"Could not set termination: {e}")

                # Verify connection with identification query
                self._identity = self._parse_identity()
                self._connected = True

                logger.info(f"Connected to {self._identity.manufacturer} "
                          f"{self._identity.model} (SN: {self._identity.serial_number})")

                # Call device-specific initialization
                self.initialize()

                return True

        except pyvisa.VisaIOError as e:
            raise InstrumentConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise InstrumentError(f"Unexpected error during connection: {e}")

    def disconnect(self):
        """Close connection to instrument"""
        try:
            with self._lock:
                if self._instrument:
                    self._instrument.close()
                    self._instrument = None
                self._connected = False
                logger.info(f"Disconnected from {self.resource_string}")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def reconnect(self) -> bool:
        """Attempt to reconnect to instrument"""
        self.disconnect()
        time.sleep(1)
        return self.connect()

    @property
    def connected(self) -> bool:
        """Check if instrument is connected"""
        return self._connected and self._instrument is not None

    @property
    def identity(self) -> Optional[InstrumentIdentity]:
        """Get instrument identification"""
        return self._identity

    def write(self, command: str):
        """
        Send command to instrument.

        Args:
            command: SCPI command string

        Raises:
            InstrumentCommandError: If write fails
        """
        if not self.connected:
            raise InstrumentConnectionError("Instrument not connected")

        try:
            with self._lock:
                logger.debug(f"WRITE: {command}")
                self._instrument.write(command)
        except pyvisa.VisaIOError as e:
            if 'timeout' in str(e).lower():
                raise InstrumentTimeoutError(f"Timeout writing command: {command}")
            raise InstrumentCommandError(f"Failed to write '{command}': {e}")

    def read(self) -> str:
        """
        Read response from instrument.

        Returns:
            Response string from instrument

        Raises:
            InstrumentCommandError: If read fails
        """
        if not self.connected:
            raise InstrumentConnectionError("Instrument not connected")

        try:
            with self._lock:
                response = self._instrument.read()
                logger.debug(f"READ: {response}")
                return response.strip()
        except pyvisa.VisaIOError as e:
            if 'timeout' in str(e).lower():
                raise InstrumentTimeoutError("Timeout reading response")
            raise InstrumentCommandError(f"Failed to read: {e}")

    def query(self, command: str) -> str:
        """
        Send command and read response.

        Args:
            command: SCPI command/query string

        Returns:
            Response string from instrument

        Raises:
            InstrumentCommandError: If query fails
        """
        if not self.connected:
            raise InstrumentConnectionError("Instrument not connected")

        try:
            with self._lock:
                logger.debug(f"QUERY: {command}")
                response = self._instrument.query(command)
                logger.debug(f"RESPONSE: {response}")
                return response.strip()
        except pyvisa.VisaIOError as e:
            if 'timeout' in str(e).lower():
                raise InstrumentTimeoutError(f"Timeout querying: {command}")
            raise InstrumentCommandError(f"Failed to query '{command}': {e}")

    def query_binary(self, command: str) -> bytes:
        """
        Query binary data from instrument.

        Args:
            command: SCPI command/query string

        Returns:
            Binary data as bytes

        Raises:
            InstrumentCommandError: If query fails
        """
        if not self.connected:
            raise InstrumentConnectionError("Instrument not connected")

        try:
            with self._lock:
                logger.debug(f"QUERY_BINARY: {command}")
                self._instrument.write(command)
                data = self._instrument.read_raw()
                logger.debug(f"RECEIVED: {len(data)} bytes")
                return data
        except pyvisa.VisaIOError as e:
            raise InstrumentCommandError(f"Failed to query binary: {e}")

    def check_errors(self) -> List[str]:
        """
        Query instrument error queue.

        Returns:
            List of error messages (empty if no errors)
        """
        errors = []
        try:
            # Standard SCPI error query
            while True:
                error = self.query("SYST:ERR?")
                if error.startswith('0,') or 'No error' in error:
                    break
                errors.append(error)
                if len(errors) > 100:  # Safety limit
                    break
        except Exception as e:
            logger.warning(f"Could not check errors: {e}")

        return errors

    def reset(self):
        """Reset instrument to default state"""
        self.write("*RST")
        time.sleep(1)  # Allow time for reset

    def clear(self):
        """Clear instrument status and error queue"""
        self.write("*CLS")

    def _parse_identity(self) -> InstrumentIdentity:
        """
        Query and parse instrument identification.

        Returns:
            InstrumentIdentity object

        Raises:
            InstrumentError: If identification fails
        """
        try:
            idn = self.query("*IDN?")
            parts = idn.split(',')

            if len(parts) >= 4:
                return InstrumentIdentity(
                    manufacturer=parts[0].strip(),
                    model=parts[1].strip(),
                    serial_number=parts[2].strip(),
                    firmware_version=parts[3].strip(),
                    resource_string=self.resource_string,
                    instrument_type=self.INSTRUMENT_TYPE,
                    raw_idn=idn
                )
            else:
                # Fallback for non-standard IDN response
                return InstrumentIdentity(
                    manufacturer="Unknown",
                    model=idn,
                    serial_number="N/A",
                    firmware_version="N/A",
                    resource_string=self.resource_string,
                    instrument_type=self.INSTRUMENT_TYPE,
                    raw_idn=idn
                )
        except Exception as e:
            raise InstrumentError(f"Failed to identify instrument: {e}")

    def register_callback(self, event: str, callback: Callable):
        """
        Register callback for instrument events.

        Args:
            event: Event name (e.g., 'measurement_complete', 'error')
            callback: Callable to invoke when event occurs
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger registered callbacks for an event"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Callback error for {event}: {e}")

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    def initialize(self):
        """
        Perform device-specific initialization after connection.

        This is called automatically after successful connection.
        Override to set up default configurations.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get instrument capabilities.

        Returns:
            Dictionary describing instrument features and limits

        Example:
            {
                'channels': 2,
                'max_voltage': 30.0,
                'max_current': 5.0,
                'features': ['ovp', 'ocp', 'remote_sense']
            }
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current instrument status.

        Returns:
            Dictionary with current instrument state

        Example:
            {
                'output_enabled': True,
                'voltage': 5.0,
                'current': 0.5,
                'errors': []
            }
        """
        pass

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def __repr__(self):
        status = "connected" if self.connected else "disconnected"
        return f"{self.__class__.__name__}('{self.resource_string}', {status})"

    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.disconnect()
        except:
            pass
