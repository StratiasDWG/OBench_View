"""
OpenBenchVue - Open-source instrument control and test automation platform
"""

__version__ = '0.1.0'
__author__ = 'OpenBenchVue Contributors'
__license__ = 'MIT'

from .utils.config import Config

# Package-level configuration instance
config = Config()

__all__ = ['config', '__version__']
