"""
Core Architecture Components

Advanced architecture patterns for OpenBenchVue including plugin system,
event-driven architecture, and dependency injection.
"""

from .plugin_manager import PluginManager, Plugin, PluginMetadata, plugin_manager
from .event_bus import EventBus, Event, EventHandler, event_bus
from .dependency_injection import Container, inject, singleton, transient, container

__all__ = [
    'PluginManager',
    'Plugin',
    'PluginMetadata',
    'plugin_manager',
    'EventBus',
    'Event',
    'EventHandler',
    'event_bus',
    'Container',
    'inject',
    'singleton',
    'transient',
    'container',
]

