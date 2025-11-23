"""
Plugin Architecture for OpenBenchVue

Provides a flexible plugin system that allows users to extend OpenBenchVue
with custom instruments, automation blocks, data processors, and UI components.

Example:
    # Create a custom instrument plugin
    class MyCustomInstrument(Plugin):
        metadata = PluginMetadata(
            name="My Custom DMM",
            version="1.0.0",
            author="Your Name",
            description="Custom digital multimeter driver",
            plugin_type="instrument"
        )

        def initialize(self, config):
            # Setup code
            pass

        def get_instrument_class(self):
            return MyDMMDriver

    # Register the plugin
    plugin_manager.register(MyCustomInstrument)
"""

import os
import sys
import importlib
import importlib.util
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    author: str
    description: str
    plugin_type: str  # 'instrument', 'automation_block', 'data_processor', 'gui_widget'
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority


class Plugin(ABC):
    """
    Base class for all plugins

    Subclass this to create custom plugins for OpenBenchVue.
    """

    metadata: PluginMetadata

    def __init__(self):
        self._initialized = False
        self._config = {}

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin

        Args:
            config: Plugin configuration dictionary

        Returns:
            True if initialization succeeded, False otherwise
        """
        pass

    def shutdown(self):
        """Clean up plugin resources"""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        if self.metadata.config_schema is None:
            return True

        # Basic schema validation
        for key, schema in self.metadata.config_schema.items():
            if schema.get('required', False) and key not in config:
                logger.error(f"Missing required config key: {key}")
                return False

            if key in config:
                expected_type = schema.get('type')
                if expected_type and not isinstance(config[key], expected_type):
                    logger.error(f"Config key {key} has wrong type")
                    return False

        return True

    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        return {
            'name': self.metadata.name,
            'version': self.metadata.version,
            'author': self.metadata.author,
            'description': self.metadata.description,
            'type': self.metadata.plugin_type,
            'enabled': self.metadata.enabled,
            'initialized': self._initialized,
        }


class PluginManager:
    """
    Manages plugin loading, initialization, and lifecycle

    The plugin manager scans plugin directories, loads plugins,
    validates dependencies, and manages plugin lifecycle.
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Initialize plugin manager

        Args:
            plugin_dirs: List of directories to scan for plugins
        """
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dirs = plugin_dirs or []
        self._plugin_types: Dict[str, List[Plugin]] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()  # Thread safety for plugin operations

    def add_plugin_directory(self, directory: str):
        """Add a directory to scan for plugins"""
        if os.path.isdir(directory):
            self.plugin_dirs.append(directory)
            logger.info(f"Added plugin directory: {directory}")
        else:
            logger.warning(f"Plugin directory does not exist: {directory}")

    def discover_plugins(self) -> List[str]:
        """
        Discover plugins in registered directories

        Returns:
            List of discovered plugin module paths
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue

            # Look for Python files
            for py_file in plugin_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                discovered.append(str(py_file))

            # Look for plugin packages
            for pkg_dir in plugin_path.iterdir():
                if pkg_dir.is_dir() and (pkg_dir / "__init__.py").exists():
                    discovered.append(str(pkg_dir))

        logger.info(f"Discovered {len(discovered)} potential plugins")
        return discovered

    def load_plugin_from_file(self, filepath: str) -> Optional[Plugin]:
        """
        Load a plugin from a Python file

        Args:
            filepath: Path to plugin file or directory

        Returns:
            Loaded plugin instance or None
        """
        try:
            path = Path(filepath)

            # Load module
            if path.is_file():
                module_name = path.stem
                spec = importlib.util.spec_from_file_location(module_name, filepath)
            else:
                module_name = path.name
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    path / "__init__.py"
                )

            if spec is None or spec.loader is None:
                logger.error(f"Could not load plugin from {filepath}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find Plugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, Plugin) and
                    attr is not Plugin):

                    plugin_instance = attr()
                    logger.info(f"Loaded plugin: {plugin_instance.metadata.name}")
                    return plugin_instance

            logger.warning(f"No Plugin subclass found in {filepath}")
            return None

        except Exception as e:
            logger.error(f"Error loading plugin from {filepath}: {e}")
            return None

    def register(self, plugin: Plugin, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register and initialize a plugin

        Args:
            plugin: Plugin instance to register
            config: Plugin configuration

        Returns:
            True if registration succeeded
        """
        if not plugin.metadata.enabled:
            logger.info(f"Plugin {plugin.metadata.name} is disabled")
            return False

        with self._lock:
            # Check dependencies
            for dep in plugin.metadata.dependencies:
                if dep not in self.plugins:
                    logger.error(
                        f"Plugin {plugin.metadata.name} requires {dep}, "
                        f"but it is not loaded"
                    )
                    return False

            # Validate and initialize
            config = config or {}
            if not plugin.validate_config(config):
                logger.error(f"Invalid config for plugin {plugin.metadata.name}")
                return False

            try:
                if not plugin.initialize(config):
                    logger.error(f"Plugin {plugin.metadata.name} initialization failed")
                    return False

                plugin._initialized = True
                plugin._config = config

                # Register plugin
                self.plugins[plugin.metadata.name] = plugin

                # Add to type index
                plugin_type = plugin.metadata.plugin_type
                if plugin_type not in self._plugin_types:
                    self._plugin_types[plugin_type] = []
                self._plugin_types[plugin_type].append(plugin)

                # Sort by priority
                self._plugin_types[plugin_type].sort(
                    key=lambda p: p.metadata.priority
                )

                logger.info(f"Registered plugin: {plugin.metadata.name}")
                self._emit_hook('plugin_registered', plugin)
                return True

            except Exception as e:
                logger.error(f"Error registering plugin {plugin.metadata.name}: {e}")
                return False

    def unregister(self, plugin_name: str) -> bool:
        """
        Unregister and shutdown a plugin

        Args:
            plugin_name: Name of plugin to unregister

        Returns:
            True if unregistration succeeded
        """
        with self._lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not found")
                return False

            plugin = self.plugins[plugin_name]

            try:
                plugin.shutdown()

                # Remove from registries
                del self.plugins[plugin_name]
                self._plugin_types[plugin.metadata.plugin_type].remove(plugin)

                logger.info(f"Unregistered plugin: {plugin_name}")
                self._emit_hook('plugin_unregistered', plugin)
                return True

            except Exception as e:
                logger.error(f"Error unregistering plugin {plugin_name}: {e}")
                return False

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        with self._lock:
            return self.plugins.get(name)

    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """Get all plugins of a specific type"""
        with self._lock:
            return self._plugin_types.get(plugin_type, []).copy()

    def get_all_plugins(self) -> List[Plugin]:
        """Get all registered plugins"""
        with self._lock:
            return list(self.plugins.values())

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin (useful for development)

        Args:
            plugin_name: Name of plugin to reload

        Returns:
            True if reload succeeded
        """
        if plugin_name not in self.plugins:
            return False

        plugin = self.plugins[plugin_name]
        config = plugin._config

        # Unregister
        if not self.unregister(plugin_name):
            return False

        # Re-register
        return self.register(plugin, config)

    def register_hook(self, hook_name: str, callback: Callable):
        """
        Register a hook callback

        Hooks are called when certain events occur (e.g., plugin_registered)

        Args:
            hook_name: Name of the hook
            callback: Callback function
        """
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def _emit_hook(self, hook_name: str, *args, **kwargs):
        """Emit a hook event"""
        for callback in self._hooks.get(hook_name, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in hook {hook_name}: {e}")

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all plugins"""
        return [plugin.get_info() for plugin in self.plugins.values()]


# Global plugin manager instance
plugin_manager = PluginManager()
