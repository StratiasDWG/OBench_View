"""
Data Handling Modules

Provides data logging, signal processing, and export functionality.
"""

from .logger import DataLogger, DataPoint
from .processor import DataProcessor
from .exporter import DataExporter

# Import advanced data processing features (optional, for enhanced functionality)
try:
    from .advanced_processor import (
        StreamingProcessor,
        AdaptiveDecimator,
        RealTimeFFT,
        WaveformAnalyzer,
        DataQualityAnalyzer,
    )

    __all__ = [
        'DataLogger',
        'DataPoint',
        'DataProcessor',
        'DataExporter',
        'StreamingProcessor',
        'AdaptiveDecimator',
        'RealTimeFFT',
        'WaveformAnalyzer',
        'DataQualityAnalyzer',
    ]
except ImportError:
    # Advanced processing features not available, continue with basic functionality
    __all__ = [
        'DataLogger',
        'DataPoint',
        'DataProcessor',
        'DataExporter',
    ]
