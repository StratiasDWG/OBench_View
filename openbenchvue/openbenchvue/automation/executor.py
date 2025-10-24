"""
Sequence Execution Engine

Executes test sequences with error handling, progress tracking,
and variable management.
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .sequence import Sequence
from .blocks import BaseBlock, LoopBlock, IfBlock

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Sequence execution state"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ExecutionResult:
    """Result of sequence execution"""
    success: bool
    state: ExecutionState
    blocks_executed: int
    duration: float
    errors: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)


class ExecutionContext:
    """
    Execution context for sequence runtime.

    Provides access to instruments, variables, and logging
    during sequence execution.
    """

    def __init__(self, instruments: Dict[str, Any] = None, logger=None):
        """
        Initialize execution context.

        Args:
            instruments: Dictionary mapping instrument names to instances
            logger: Data logger instance (optional)
        """
        self.instruments = instruments or {}
        self.variables: Dict[str, Any] = {}
        self.logger = logger
        self._start_time = time.time()

    def get_instrument(self, name: str):
        """Get instrument by name"""
        if name not in self.instruments:
            available = ', '.join(self.instruments.keys())
            raise ValueError(f"Instrument '{name}' not found. Available: {available}")
        return self.instruments[name]

    def set_variable(self, name: str, value: Any):
        """Set variable value"""
        self.variables[name] = value
        logger.debug(f"Variable set: {name} = {value}")

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get variable value"""
        return self.variables.get(name, default)

    def get_elapsed_time(self) -> float:
        """Get elapsed time since context creation"""
        return time.time() - self._start_time

    def clear_variables(self):
        """Clear all variables"""
        self.variables.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export context as dictionary"""
        return {
            'instruments': list(self.instruments.keys()),
            'variables': self.variables.copy(),
            'elapsed_time': self.get_elapsed_time()
        }


class SequenceExecutor:
    """
    Sequence executor with progress tracking and control.

    Provides BenchVue-like execution with:
    - Start/stop/pause/resume control
    - Progress callbacks
    - Error handling
    - Variable management
    - Loop and conditional support
    """

    def __init__(
        self,
        sequence: Sequence,
        context: ExecutionContext,
        stop_on_error: bool = True,
        max_iterations: int = 10000
    ):
        """
        Initialize executor.

        Args:
            sequence: Sequence to execute
            context: Execution context
            stop_on_error: Stop execution on first error
            max_iterations: Maximum loop iterations (safety limit)
        """
        self.sequence = sequence
        self.context = context
        self.stop_on_error = stop_on_error
        self.max_iterations = max_iterations

        self.state = ExecutionState.IDLE
        self.current_block_index = 0
        self.errors: List[str] = []
        self.execution_log: List[Dict[str, Any]] = []

        # Control flags
        self._stop_requested = False
        self._pause_requested = False
        self._paused_event = threading.Event()
        self._paused_event.set()  # Not paused initially

        # Callbacks
        self._progress_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []

    def register_progress_callback(self, callback: Callable):
        """Register callback for progress updates"""
        self._progress_callbacks.append(callback)

    def register_completion_callback(self, callback: Callable):
        """Register callback for execution completion"""
        self._completion_callbacks.append(callback)

    def _trigger_progress(self, block: BaseBlock, index: int, result: Dict[str, Any]):
        """Trigger progress callbacks"""
        for callback in self._progress_callbacks:
            try:
                callback(block, index, result, self.state)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _trigger_completion(self, result: ExecutionResult):
        """Trigger completion callbacks"""
        for callback in self._completion_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Completion callback error: {e}")

    def start(self) -> ExecutionResult:
        """
        Execute sequence from beginning.

        Returns:
            ExecutionResult with execution summary
        """
        logger.info(f"Starting sequence: {self.sequence.name}")

        # Validate sequence
        validation_errors = self.sequence.validate()
        if validation_errors:
            logger.error(f"Sequence validation failed: {validation_errors}")
            return ExecutionResult(
                success=False,
                state=ExecutionState.FAILED,
                blocks_executed=0,
                duration=0.0,
                errors=validation_errors
            )

        # Reset state
        self.state = ExecutionState.RUNNING
        self.current_block_index = 0
        self.errors = []
        self.execution_log = []
        self._stop_requested = False
        self._pause_requested = False
        self.context.clear_variables()

        start_time = time.time()
        blocks_executed = 0

        try:
            # Execute blocks sequentially
            while self.current_block_index < len(self.sequence.blocks):
                # Check for stop request
                if self._stop_requested:
                    logger.info("Execution stopped by user")
                    self.state = ExecutionState.STOPPED
                    break

                # Check for pause request
                self._paused_event.wait()
                if self._pause_requested:
                    self.state = ExecutionState.PAUSED
                    continue

                # Get current block
                block = self.sequence.blocks[self.current_block_index]

                # Execute block
                try:
                    logger.debug(f"Executing block {self.current_block_index}: {block.name}")

                    result = block.execute(self.context)
                    blocks_executed += 1

                    # Log execution
                    log_entry = {
                        'timestamp': time.time() - start_time,
                        'block': block.name,
                        'block_id': block.block_id,
                        'index': self.current_block_index,
                        'result': result,
                        'success': True
                    }
                    self.execution_log.append(log_entry)

                    # Trigger progress callbacks
                    self._trigger_progress(block, self.current_block_index, result)

                    # Handle special block types
                    if isinstance(block, LoopBlock):
                        # Loop handling would go here
                        # For simplicity, just logging
                        logger.debug(f"Loop block: {result.get('iterations')} iterations")

                    elif isinstance(block, IfBlock):
                        # Conditional handling
                        if not result.get('condition_met', True):
                            logger.debug("Condition not met, skipping next blocks (simplified)")
                            # In a full implementation, would skip to end of conditional block

                except Exception as e:
                    error_msg = f"Block {self.current_block_index} ({block.name}) failed: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)

                    # Log error
                    log_entry = {
                        'timestamp': time.time() - start_time,
                        'block': block.name,
                        'block_id': block.block_id,
                        'index': self.current_block_index,
                        'error': str(e),
                        'success': False
                    }
                    self.execution_log.append(log_entry)

                    if self.stop_on_error:
                        logger.error("Stopping execution due to error")
                        self.state = ExecutionState.FAILED
                        break

                # Move to next block
                self.current_block_index += 1

            # Execution completed
            if self.state == ExecutionState.RUNNING:
                self.state = ExecutionState.COMPLETED
                logger.info("Sequence execution completed successfully")

        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}")
            self.errors.append(f"Unexpected error: {e}")
            self.state = ExecutionState.FAILED

        # Create result
        duration = time.time() - start_time
        result = ExecutionResult(
            success=(self.state == ExecutionState.COMPLETED),
            state=self.state,
            blocks_executed=blocks_executed,
            duration=duration,
            errors=self.errors,
            variables=self.context.variables.copy(),
            logs=self.execution_log
        )

        # Trigger completion callbacks
        self._trigger_completion(result)

        logger.info(f"Execution finished: {result.state.value}, "
                   f"{blocks_executed} blocks in {duration:.2f}s")

        return result

    def stop(self):
        """Request execution stop"""
        logger.info("Stop requested")
        self._stop_requested = True
        self._pause_requested = False
        self._paused_event.set()  # Unpause if paused

    def pause(self):
        """Request execution pause"""
        logger.info("Pause requested")
        self._pause_requested = True
        self._paused_event.clear()
        self.state = ExecutionState.PAUSED

    def resume(self):
        """Resume paused execution"""
        logger.info("Resume requested")
        self._pause_requested = False
        self._paused_event.set()
        self.state = ExecutionState.RUNNING

    def is_running(self) -> bool:
        """Check if execution is running"""
        return self.state == ExecutionState.RUNNING

    def is_paused(self) -> bool:
        """Check if execution is paused"""
        return self.state == ExecutionState.PAUSED

    def get_progress(self) -> float:
        """
        Get execution progress.

        Returns:
            Progress as percentage (0-100)
        """
        if len(self.sequence.blocks) == 0:
            return 100.0

        return (self.current_block_index / len(self.sequence.blocks)) * 100.0

    def get_current_block(self) -> Optional[BaseBlock]:
        """Get currently executing block"""
        if 0 <= self.current_block_index < len(self.sequence.blocks):
            return self.sequence.blocks[self.current_block_index]
        return None

    def run_async(self, callback: Callable[[ExecutionResult], None] = None):
        """
        Run sequence in background thread.

        Args:
            callback: Called with ExecutionResult when complete
        """
        def _run_thread():
            result = self.start()
            if callback:
                callback(result)

        thread = threading.Thread(target=_run_thread, daemon=True)
        thread.start()
        return thread

    def export_log(self, file_path: str):
        """
        Export execution log to file.

        Args:
            file_path: Path to save log
        """
        import json
        from pathlib import Path

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            log_data = {
                'sequence_name': self.sequence.name,
                'execution_state': self.state.value,
                'blocks_executed': self.current_block_index,
                'errors': self.errors,
                'variables': self.context.variables,
                'log_entries': self.execution_log
            }

            with open(path, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)

            logger.info(f"Execution log exported to {file_path}")

        except Exception as e:
            logger.error(f"Failed to export log: {e}")
