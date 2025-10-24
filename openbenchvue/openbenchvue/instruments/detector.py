"""
Instrument Detection and Auto-Discovery

Scans for connected instruments and matches them to appropriate drivers.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
import pyvisa

from .base import BaseInstrument, InstrumentIdentity, InstrumentType
from .dmm import DigitalMultimeter
from .oscilloscope import Oscilloscope
from .power_supply import PowerSupply
from .function_generator import FunctionGenerator
from .power_analyzer import PowerAnalyzer

logger = logging.getLogger(__name__)


class InstrumentDetector:
    """
    Instrument detector for auto-discovery.

    Scans VISA resources and matches instruments to appropriate drivers
    based on IDN responses and model patterns.
    """

    # Mapping of instrument classes
    INSTRUMENT_CLASSES = [
        DigitalMultimeter,
        Oscilloscope,
        PowerSupply,
        FunctionGenerator,
        PowerAnalyzer,
    ]

    def __init__(self, visa_backend: str = '@iolib'):
        """
        Initialize detector.

        Args:
            visa_backend: VISA backend to use ('@iolib', '@py', etc.)
        """
        self.visa_backend = visa_backend
        try:
            self.rm = pyvisa.ResourceManager(visa_backend)
            logger.info(f"Initialized VISA ResourceManager with backend: {visa_backend}")
        except Exception as e:
            logger.error(f"Failed to initialize VISA: {e}")
            raise

    def scan_resources(self, timeout: float = 10.0) -> List[str]:
        """
        Scan for available VISA resources.

        Args:
            timeout: Scan timeout in seconds

        Returns:
            List of VISA resource strings
        """
        try:
            resources = self.rm.list_resources()
            logger.info(f"Found {len(resources)} VISA resources")

            for resource in resources:
                logger.debug(f"  - {resource}")

            return list(resources)

        except Exception as e:
            logger.error(f"Resource scan failed: {e}")
            return []

    def identify_instrument(self, resource: str, timeout: int = 5000) -> Optional[InstrumentIdentity]:
        """
        Identify instrument at given resource.

        Args:
            resource: VISA resource string
            timeout: Communication timeout in ms

        Returns:
            InstrumentIdentity or None if identification fails
        """
        try:
            # Open resource temporarily
            instrument = self.rm.open_resource(resource)
            instrument.timeout = timeout

            # Query identification
            idn_response = instrument.query("*IDN?").strip()
            logger.debug(f"{resource}: {idn_response}")

            # Parse IDN response
            parts = idn_response.split(',')

            if len(parts) >= 4:
                manufacturer = parts[0].strip()
                model = parts[1].strip()
                serial = parts[2].strip()
                firmware = parts[3].strip()
            else:
                manufacturer = "Unknown"
                model = idn_response
                serial = "N/A"
                firmware = "N/A"

            # Determine instrument type by matching model patterns
            instrument_type = self._match_instrument_type(model, manufacturer)

            identity = InstrumentIdentity(
                manufacturer=manufacturer,
                model=model,
                serial_number=serial,
                firmware_version=firmware,
                resource_string=resource,
                instrument_type=instrument_type,
                raw_idn=idn_response
            )

            instrument.close()
            return identity

        except Exception as e:
            logger.warning(f"Could not identify {resource}: {e}")
            return None

    def _match_instrument_type(self, model: str, manufacturer: str) -> InstrumentType:
        """
        Match instrument type based on model and manufacturer.

        Args:
            model: Instrument model string
            manufacturer: Manufacturer name

        Returns:
            InstrumentType
        """
        model_upper = model.upper()
        manufacturer_upper = manufacturer.upper()

        # Check each instrument class for model pattern match
        for instrument_class in self.INSTRUMENT_CLASSES:
            for pattern in instrument_class.SUPPORTED_MODELS:
                if re.search(pattern, model, re.IGNORECASE):
                    logger.debug(f"Matched {model} to {instrument_class.__name__}")
                    return instrument_class.INSTRUMENT_TYPE

        # Heuristic matching based on keywords
        if any(kw in model_upper for kw in ['DMM', 'MULTIMETER', '344']):
            return InstrumentType.DMM
        elif any(kw in model_upper for kw in ['DSO', 'MSO', 'SCOPE', 'OSCILLO']):
            return InstrumentType.OSCILLOSCOPE
        elif any(kw in model_upper for kw in ['PSU', 'POWER', 'E36', 'N67', 'N79']):
            return InstrumentType.POWER_SUPPLY
        elif any(kw in model_upper for kw in ['FG', 'FGEN', '33', 'SIGNAL', 'WAVEFORM']):
            return InstrumentType.FUNCTION_GENERATOR
        elif any(kw in model_upper for kw in ['PA', 'ANALYZER', 'POWER']):
            return InstrumentType.POWER_ANALYZER

        logger.debug(f"Could not determine type for {model}, using GENERIC")
        return InstrumentType.GENERIC

    def detect_instruments(self, timeout: float = 10.0) -> List[InstrumentIdentity]:
        """
        Scan and identify all connected instruments.

        Args:
            timeout: Scan timeout in seconds

        Returns:
            List of identified instruments
        """
        logger.info("Starting instrument detection...")

        resources = self.scan_resources(timeout)
        identified = []

        for resource in resources:
            identity = self.identify_instrument(resource)
            if identity:
                identified.append(identity)
                logger.info(f"Detected: {identity.manufacturer} {identity.model} "
                          f"({identity.instrument_type.value})")

        logger.info(f"Detection complete: found {len(identified)} instruments")
        return identified

    def create_instrument(self, identity: InstrumentIdentity) -> Optional[BaseInstrument]:
        """
        Create appropriate instrument driver instance.

        Args:
            identity: Instrument identity

        Returns:
            Configured instrument instance or None
        """
        try:
            # Find matching instrument class
            for instrument_class in self.INSTRUMENT_CLASSES:
                if instrument_class.INSTRUMENT_TYPE == identity.instrument_type:
                    logger.debug(f"Creating {instrument_class.__name__} for {identity.model}")
                    instrument = instrument_class(identity.resource_string, self.rm)
                    return instrument

            # Fallback to generic base class
            logger.warning(f"No specific driver for {identity.instrument_type.value}, "
                         f"using generic SCPI")
            return None

        except Exception as e:
            logger.error(f"Failed to create instrument driver: {e}")
            return None

    def auto_connect(self, timeout: float = 10.0) -> Dict[str, BaseInstrument]:
        """
        Auto-detect and connect to all instruments.

        Args:
            timeout: Detection and connection timeout

        Returns:
            Dictionary mapping resource strings to connected instrument instances
        """
        instruments = {}

        # Detect all instruments
        identities = self.detect_instruments(timeout)

        # Create and connect driver instances
        for identity in identities:
            try:
                instrument = self.create_instrument(identity)
                if instrument:
                    instrument.connect()
                    instruments[identity.resource_string] = instrument
                    logger.info(f"Connected: {identity.model} at {identity.resource_string}")
            except Exception as e:
                logger.error(f"Failed to connect to {identity.resource_string}: {e}")

        logger.info(f"Auto-connect complete: {len(instruments)} instruments ready")
        return instruments

    def get_visa_info(self) -> Dict[str, str]:
        """
        Get VISA installation information.

        Returns:
            Dictionary with VISA backend details
        """
        try:
            # Get available backends
            try:
                backends = pyvisa.highlevel.list_backends()
            except:
                backends = ['@iolib', '@py']

            info = {
                'current_backend': self.visa_backend,
                'available_backends': backends,
                'pyvisa_version': pyvisa.__version__,
            }

            # Try to get backend-specific info
            try:
                visa_lib = self.rm.visalib
                info['library_path'] = str(visa_lib.get_library_paths())
            except:
                pass

            return info

        except Exception as e:
            logger.error(f"Could not get VISA info: {e}")
            return {'error': str(e)}

    def test_connection(self, resource: str) -> Tuple[bool, str]:
        """
        Test connection to a specific resource.

        Args:
            resource: VISA resource string

        Returns:
            Tuple of (success, message)
        """
        try:
            instrument = self.rm.open_resource(resource)
            instrument.timeout = 5000

            # Try basic query
            response = instrument.query("*IDN?")

            instrument.close()

            return (True, f"Connected successfully: {response}")

        except Exception as e:
            return (False, f"Connection failed: {str(e)}")

    def close(self):
        """Close resource manager"""
        try:
            if hasattr(self, 'rm'):
                self.rm.close()
                logger.info("Resource manager closed")
        except Exception as e:
            logger.error(f"Error closing resource manager: {e}")

    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.close()
        except:
            pass
