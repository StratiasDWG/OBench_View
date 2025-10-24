"""
Test Automation Modules

Provides visual test sequence creation and execution without programming.
"""

from .blocks import BaseBlock, BLOCK_REGISTRY
from .sequence import Sequence, SequenceLoader
from .executor import SequenceExecutor, ExecutionContext

__all__ = [
    'BaseBlock',
    'BLOCK_REGISTRY',
    'Sequence',
    'SequenceLoader',
    'SequenceExecutor',
    'ExecutionContext',
]
