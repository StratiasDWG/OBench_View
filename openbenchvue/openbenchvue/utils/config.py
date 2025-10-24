"""
Configuration Management for OpenBenchVue

Handles loading and saving configuration from YAML files,
with defaults and runtime modifications.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for OpenBenchVue.

    Loads configuration from YAML file with fallback to defaults.
    Supports runtime modifications and persistence.
    """

    DEFAULT_CONFIG = {
        'visa': {
            'backend': '@iolib',  # '@py' for pyvisa-py, '@iolib' for Keysight/NI
            'timeout': 5000,  # milliseconds
            'query_delay': 0.01,  # seconds between query send and read
            'chunk_size': 20480,  # bytes for data transfer
        },
        'gui': {
            'theme': 'light',  # 'light' or 'dark'
            'update_rate': 100,  # milliseconds for GUI updates
            'plot_points': 1000,  # maximum points to display in real-time plots
            'font_size': 10,
            'window_geometry': None,  # Saved window position/size
        },
        'remote': {
            'enabled': False,
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False,
        },
        'logging': {
            'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
            'file': 'openbenchvue.log',
            'max_bytes': 10485760,  # 10 MB
            'backup_count': 5,
            'console': True,
        },
        'data': {
            'default_export_format': 'csv',
            'export_directory': './data',
            'auto_save': False,
            'buffer_size': 10000,  # Maximum data points in memory
        },
        'automation': {
            'max_iterations': 10000,  # Safety limit for loops
            'execution_timeout': 3600,  # seconds
            'stop_on_error': True,
        },
        'instruments': {
            'auto_detect': True,
            'connection_retry': 3,
            'reconnect_delay': 2.0,  # seconds
            'scan_timeout': 10.0,  # seconds for device scan
        },
    }

    def __init__(self, config_file: str = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML config file. If None, searches for
                        'config.yaml' in current directory and user home.
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self.config_file = config_file or self._find_config_file()

        if self.config_file and os.path.exists(self.config_file):
            self.load(self.config_file)
        else:
            logger.info("No config file found, using defaults")

    def _find_config_file(self) -> str:
        """Search for config.yaml in standard locations"""
        search_paths = [
            './config.yaml',
            os.path.expanduser('~/.openbenchvue/config.yaml'),
            os.path.join(os.path.dirname(__file__), '../../config.yaml'),
        ]

        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found config file: {path}")
                return path

        return './config.yaml'  # Default location for saving

    def load(self, file_path: str):
        """
        Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file
        """
        try:
            with open(file_path, 'r') as f:
                user_config = yaml.safe_load(f)

            if user_config:
                self._merge_config(self._config, user_config)
                logger.info(f"Loaded configuration from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")

    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge override config into base config"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def save(self, file_path: str = None):
        """
        Save current configuration to YAML file.

        Args:
            file_path: Path to save to. If None, uses loaded config file.
        """
        file_path = file_path or self.config_file

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

            with open(file_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)

            logger.info(f"Saved configuration to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {file_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'visa.timeout')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'visa.timeout')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_section(self, section: str) -> Dict:
        """
        Get entire configuration section.

        Args:
            section: Section name (e.g., 'visa', 'gui')

        Returns:
            Dictionary of section configuration
        """
        return self._config.get(section, {}).copy()

    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self._config = self.DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to defaults")

    def __repr__(self):
        return f"Config(file='{self.config_file}')"
