"""
OpenBenchVue - Open-source instrument control and test automation platform

A professional, production-ready alternative to Keysight BenchVue with:
- Advanced plugin architecture for extensibility
- Event-driven design for decoupled components
- Dependency injection for better testing and modularity
- ML-powered analytics for anomaly detection and forecasting
- Enterprise-grade security with authentication and audit logging
- Docker deployment for production environments
"""

__version__ = '1.0.0'
__author__ = 'OpenBenchVue Contributors'
__license__ = 'MIT'

from .utils.config import Config

# Package-level configuration instance
config = Config()

# Import core architecture (optional, advanced features)
try:
    from .core import (
        PluginManager,
        plugin_manager,
        EventBus,
        event_bus,
        Container,
        container,
    )
    _has_core = True
except ImportError:
    _has_core = False

# Import analytics (optional, advanced features)
try:
    from .analytics import (
        StatisticalAnomalyDetector,
        IsolationForestDetector,
        TrendAnalyzer,
        DriftDetector,
        Forecaster,
    )
    _has_analytics = True
except ImportError:
    _has_analytics = False

# Import security (optional, advanced features)
try:
    from .security import (
        AuthenticationManager,
        AuthorizationManager,
        AuditLogger,
    )
    _has_security = True
except ImportError:
    _has_security = False

__all__ = ['config', '__version__']

# Add exports if modules are available
if _has_core:
    __all__.extend([
        'PluginManager',
        'plugin_manager',
        'EventBus',
        'event_bus',
        'Container',
        'container',
    ])

if _has_analytics:
    __all__.extend([
        'StatisticalAnomalyDetector',
        'IsolationForestDetector',
        'TrendAnalyzer',
        'DriftDetector',
        'Forecaster',
    ])

if _has_security:
    __all__.extend([
        'AuthenticationManager',
        'AuthorizationManager',
        'AuditLogger',
    ])
