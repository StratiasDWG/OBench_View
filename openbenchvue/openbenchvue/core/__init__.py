"""
Core Architecture Components

Advanced architecture patterns for OpenBenchVue including plugin system,
event-driven architecture, and dependency injection.
"""

from .plugin_manager import PluginManager, Plugin, PluginMetadata
from .event_bus import EventBus, Event, EventHandler
from .dependency_injection import Container, inject, singleton, transient

__all__ = [
    'PluginManager',
    'Plugin',
    'PluginMetadata',
    'EventBus',
    'Event',
    'EventHandler',
    'Container',
    'inject',
    'singleton',
    'transient',
]
