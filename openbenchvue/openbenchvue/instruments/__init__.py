"""
Instrument drivers for OpenBenchVue

This package contains instrument drivers for various test and measurement equipment.
Each driver inherits from BaseInstrument and implements device-specific functionality.
"""

from .base import BaseInstrument, InstrumentError, InstrumentType
from .dmm import DigitalMultimeter
from .oscilloscope import Oscilloscope
from .power_supply import PowerSupply
from .function_generator import FunctionGenerator
from .power_analyzer import PowerAnalyzer
from .detector import InstrumentDetector

# Registry of all available instrument classes
INSTRUMENT_CLASSES = [
    DigitalMultimeter,
    Oscilloscope,
    PowerSupply,
    FunctionGenerator,
    PowerAnalyzer,
]

__all__ = [
    'BaseInstrument',
    'InstrumentError',
    'InstrumentType',
    'DigitalMultimeter',
    'Oscilloscope',
    'PowerSupply',
    'FunctionGenerator',
    'PowerAnalyzer',
    'InstrumentDetector',
    'INSTRUMENT_CLASSES',
]
