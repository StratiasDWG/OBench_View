"""
Test Automation Modules

Provides visual test sequence creation and execution without programming.
"""

from .blocks import BaseBlock, BLOCK_REGISTRY
from .sequence import Sequence, SequenceLoader
from .executor import SequenceExecutor, ExecutionContext

# Import advanced blocks (optional, for enhanced functionality)
try:
    from .advanced_blocks import (
        ADVANCED_BLOCK_REGISTRY,
        ExpressionEvaluator,
        SetVariableBlock,
        WhileBlock,
        TryExceptBlock,
        ParallelBlock,
        WaitForBlock,
        MathBlock,
        DataTransformBlock,
        SweepBlock,
    )

    # Merge advanced blocks into main registry
    BLOCK_REGISTRY.update(ADVANCED_BLOCK_REGISTRY)

    __all__ = [
        'BaseBlock',
        'BLOCK_REGISTRY',
        'Sequence',
        'SequenceLoader',
        'SequenceExecutor',
        'ExecutionContext',
        'ExpressionEvaluator',
        'SetVariableBlock',
        'WhileBlock',
        'TryExceptBlock',
        'ParallelBlock',
        'WaitForBlock',
        'MathBlock',
        'DataTransformBlock',
        'SweepBlock',
        'ADVANCED_BLOCK_REGISTRY',
    ]
except ImportError:
    # Advanced blocks not available, continue with basic functionality
    __all__ = [
        'BaseBlock',
        'BLOCK_REGISTRY',
        'Sequence',
        'SequenceLoader',
        'SequenceExecutor',
        'ExecutionContext',
    ]
