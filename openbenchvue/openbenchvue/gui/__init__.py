"""
GUI Modules

PyQt5-based graphical user interface components.
"""

# GUI components are imported on-demand to avoid requiring PyQt5 for CLI usage
# Basic GUI components
__all__ = [
    'MainWindow',
    'Dashboard',
    'InstrumentPanels',
    'DataViewer',
    'SequenceBuilder',
]

# Enhanced GUI features (optional)
try:
    from .themes import LightTheme, DarkTheme, HighContrastTheme, apply_theme, get_theme
    from .advanced_widgets import (
        AnalogGauge,
        DigitalDisplay,
        StatusIndicator,
        EnhancedProgressBar,
        MeasurementDisplay,
    )

    __all__.extend([
        'LightTheme',
        'DarkTheme',
        'HighContrastTheme',
        'apply_theme',
        'get_theme',
        'AnalogGauge',
        'DigitalDisplay',
        'StatusIndicator',
        'EnhancedProgressBar',
        'MeasurementDisplay',
    ])
except ImportError:
    # Enhanced GUI features not available
    pass
