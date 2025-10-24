"""
Automation Block Definitions

Defines reusable automation blocks for drag-and-drop sequence building.
Each block represents an action (measure, set voltage, delay, etc.).
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BlockParameter:
    """Parameter definition for a block"""
    name: str
    type: str  # 'int', 'float', 'string', 'bool', 'choice', 'instrument'
    default: Any
    label: str = ""
    choices: List[Any] = field(default_factory=list)  # For 'choice' type
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""


class BaseBlock(ABC):
    """
    Base class for automation blocks.

    Each block represents a single action in a test sequence.
    """

    # Class attributes to be overridden
    name: str = "Base Block"
    category: str = "General"
    description: str = ""
    icon: str = "⬜"  # Unicode icon for GUI

    def __init__(self):
        self.block_id: str = ""
        self.parameters: Dict[str, BlockParameter] = {}
        self.parameter_values: Dict[str, Any] = {}
        self._define_parameters()

    def _define_parameters(self):
        """Override to define block-specific parameters"""
        pass

    def add_parameter(
        self,
        name: str,
        param_type: str,
        default: Any,
        label: str = "",
        **kwargs
    ):
        """Add parameter definition"""
        param = BlockParameter(
            name=name,
            type=param_type,
            default=default,
            label=label or name.replace('_', ' ').title(),
            **kwargs
        )
        self.parameters[name] = param
        self.parameter_values[name] = default

    def set_parameter(self, name: str, value: Any):
        """Set parameter value"""
        if name in self.parameters:
            self.parameter_values[name] = value
        else:
            raise ValueError(f"Unknown parameter: {name}")

    def get_parameter(self, name: str) -> Any:
        """Get parameter value"""
        return self.parameter_values.get(name)

    @abstractmethod
    def execute(self, context: 'ExecutionContext') -> Dict[str, Any]:
        """
        Execute the block action.

        Args:
            context: Execution context with instruments and variables

        Returns:
            Dictionary with execution results
        """
        pass

    def validate(self) -> List[str]:
        """
        Validate block configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for name, param in self.parameters.items():
            value = self.parameter_values.get(name)

            # Check min/max for numeric types
            if param.type in ['int', 'float']:
                if param.min_value is not None and value < param.min_value:
                    errors.append(f"{param.label} must be >= {param.min_value}")
                if param.max_value is not None and value > param.max_value:
                    errors.append(f"{param.label} must be <= {param.max_value}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize block to dictionary"""
        return {
            'type': self.__class__.__name__,
            'block_id': self.block_id,
            'parameters': self.parameter_values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseBlock':
        """Deserialize block from dictionary"""
        block = cls()
        block.block_id = data.get('block_id', '')

        for name, value in data.get('parameters', {}).items():
            if name in block.parameters:
                block.set_parameter(name, value)

        return block

    def __repr__(self):
        return f"{self.__class__.__name__}({self.block_id})"


# Concrete block implementations

class DelayBlock(BaseBlock):
    """Delay/wait block"""

    name = "Delay"
    category = "Control"
    description = "Wait for specified duration"
    icon = "⏱️"

    def _define_parameters(self):
        self.add_parameter('duration', 'float', 1.0, 'Duration (seconds)', min_value=0.001)

    def execute(self, context) -> Dict[str, Any]:
        duration = self.get_parameter('duration')
        logger.info(f"Delaying for {duration}s")
        time.sleep(duration)
        return {'status': 'success', 'duration': duration}


class SetVoltageBlock(BaseBlock):
    """Set power supply voltage"""

    name = "Set Voltage"
    category = "Power Supply"
    description = "Set output voltage on power supply"
    icon = "⚡"

    def _define_parameters(self):
        self.add_parameter('instrument', 'instrument', None, 'Power Supply')
        self.add_parameter('channel', 'int', 1, 'Channel', min_value=1)
        self.add_parameter('voltage', 'float', 5.0, 'Voltage (V)', min_value=0.0)

    def execute(self, context) -> Dict[str, Any]:
        inst_name = self.get_parameter('instrument')
        channel = self.get_parameter('channel')
        voltage = self.get_parameter('voltage')

        instrument = context.get_instrument(inst_name)
        if not instrument:
            raise RuntimeError(f"Instrument '{inst_name}' not found")

        instrument.set_voltage(channel, voltage)
        logger.info(f"Set {inst_name} CH{channel} to {voltage}V")

        return {'status': 'success', 'voltage': voltage}


class SetCurrentBlock(BaseBlock):
    """Set power supply current limit"""

    name = "Set Current"
    category = "Power Supply"
    description = "Set current limit on power supply"
    icon = "🔌"

    def _define_parameters(self):
        self.add_parameter('instrument', 'instrument', None, 'Power Supply')
        self.add_parameter('channel', 'int', 1, 'Channel', min_value=1)
        self.add_parameter('current', 'float', 1.0, 'Current (A)', min_value=0.0)

    def execute(self, context) -> Dict[str, Any]:
        inst_name = self.get_parameter('instrument')
        channel = self.get_parameter('channel')
        current = self.get_parameter('current')

        instrument = context.get_instrument(inst_name)
        instrument.set_current(channel, current)
        logger.info(f"Set {inst_name} CH{channel} current to {current}A")

        return {'status': 'success', 'current': current}


class OutputEnableBlock(BaseBlock):
    """Enable/disable power supply output"""

    name = "Output Enable"
    category = "Power Supply"
    description = "Enable or disable instrument output"
    icon = "🔘"

    def _define_parameters(self):
        self.add_parameter('instrument', 'instrument', None, 'Instrument')
        self.add_parameter('channel', 'int', 1, 'Channel', min_value=1)
        self.add_parameter('enable', 'bool', True, 'Enable Output')

    def execute(self, context) -> Dict[str, Any]:
        inst_name = self.get_parameter('instrument')
        channel = self.get_parameter('channel')
        enable = self.get_parameter('enable')

        instrument = context.get_instrument(inst_name)
        instrument.set_output(channel, enable)

        state = "enabled" if enable else "disabled"
        logger.info(f"Output {state} on {inst_name} CH{channel}")

        return {'status': 'success', 'enabled': enable}


class MeasureBlock(BaseBlock):
    """Generic measurement block"""

    name = "Measure"
    category = "Measurement"
    description = "Perform measurement and store result"
    icon = "📊"

    def _define_parameters(self):
        self.add_parameter('instrument', 'instrument', None, 'Instrument')
        self.add_parameter('variable', 'string', 'measurement', 'Store in Variable')

    def execute(self, context) -> Dict[str, Any]:
        inst_name = self.get_parameter('instrument')
        var_name = self.get_parameter('variable')

        instrument = context.get_instrument(inst_name)

        # Call appropriate measurement method based on instrument type
        if hasattr(instrument, 'measure'):
            value = instrument.measure()
        else:
            raise RuntimeError(f"Instrument '{inst_name}' does not support measure()")

        # Store in context
        context.set_variable(var_name, value)
        logger.info(f"Measured {value} on {inst_name}, stored in {var_name}")

        return {'status': 'success', 'value': value, 'variable': var_name}


class LoopBlock(BaseBlock):
    """Loop/iteration block"""

    name = "Loop"
    category = "Control"
    description = "Repeat actions multiple times"
    icon = "🔄"

    def _define_parameters(self):
        self.add_parameter('iterations', 'int', 10, 'Iterations', min_value=1, max_value=10000)
        self.add_parameter('variable', 'string', 'i', 'Counter Variable')

    def execute(self, context) -> Dict[str, Any]:
        # Note: Actual loop logic handled by executor
        # This just provides parameters
        return {
            'status': 'loop_start',
            'iterations': self.get_parameter('iterations'),
            'variable': self.get_parameter('variable')
        }


class IfBlock(BaseBlock):
    """Conditional block"""

    name = "If Condition"
    category = "Control"
    description = "Execute actions only if condition is true"
    icon = "❓"

    def _define_parameters(self):
        self.add_parameter('variable', 'string', 'measurement', 'Variable')
        self.add_parameter('operator', 'choice', '>', 'Operator',
                         choices=['>', '<', '>=', '<=', '==', '!='])
        self.add_parameter('value', 'float', 0.0, 'Value')

    def execute(self, context) -> Dict[str, Any]:
        var_name = self.get_parameter('variable')
        operator = self.get_parameter('operator')
        threshold = self.get_parameter('value')

        var_value = context.get_variable(var_name)
        if var_value is None:
            raise RuntimeError(f"Variable '{var_name}' not found")

        # Evaluate condition
        condition_met = False
        if operator == '>':
            condition_met = var_value > threshold
        elif operator == '<':
            condition_met = var_value < threshold
        elif operator == '>=':
            condition_met = var_value >= threshold
        elif operator == '<=':
            condition_met = var_value <= threshold
        elif operator == '==':
            condition_met = var_value == threshold
        elif operator == '!=':
            condition_met = var_value != threshold

        logger.info(f"Condition: {var_name}({var_value}) {operator} {threshold} = {condition_met}")

        return {
            'status': 'condition_evaluated',
            'condition_met': condition_met,
            'variable': var_name,
            'value': var_value
        }


class LogDataBlock(BaseBlock):
    """Log data point"""

    name = "Log Data"
    category = "Data"
    description = "Log data to file or memory"
    icon = "💾"

    def _define_parameters(self):
        self.add_parameter('variable', 'string', 'measurement', 'Variable to Log')
        self.add_parameter('label', 'string', '', 'Label (optional)')

    def execute(self, context) -> Dict[str, Any]:
        var_name = self.get_parameter('variable')
        label = self.get_parameter('label') or var_name

        value = context.get_variable(var_name)
        if value is None:
            raise RuntimeError(f"Variable '{var_name}' not found")

        # Log to context's data logger
        if context.logger:
            context.logger.log_data({label: value})

        logger.info(f"Logged: {label} = {value}")

        return {'status': 'success', 'variable': var_name, 'value': value}


class CommentBlock(BaseBlock):
    """Comment/documentation block"""

    name = "Comment"
    category = "General"
    description = "Add comment or note to sequence"
    icon = "💬"

    def _define_parameters(self):
        self.add_parameter('text', 'string', '', 'Comment Text')

    def execute(self, context) -> Dict[str, Any]:
        text = self.get_parameter('text')
        logger.info(f"Comment: {text}")
        return {'status': 'success', 'text': text}


class AssertBlock(BaseBlock):
    """Assertion/validation block"""

    name = "Assert"
    category = "Validation"
    description = "Assert condition is true (fail test if false)"
    icon = "✓"

    def _define_parameters(self):
        self.add_parameter('variable', 'string', 'measurement', 'Variable')
        self.add_parameter('operator', 'choice', '>', 'Operator',
                         choices=['>', '<', '>=', '<=', '==', '!='])
        self.add_parameter('value', 'float', 0.0, 'Expected Value')
        self.add_parameter('message', 'string', 'Assertion failed', 'Error Message')

    def execute(self, context) -> Dict[str, Any]:
        var_name = self.get_parameter('variable')
        operator = self.get_parameter('operator')
        expected = self.get_parameter('value')
        message = self.get_parameter('message')

        actual = context.get_variable(var_name)
        if actual is None:
            raise RuntimeError(f"Variable '{var_name}' not found")

        # Evaluate assertion
        passed = False
        if operator == '>':
            passed = actual > expected
        elif operator == '<':
            passed = actual < expected
        elif operator == '>=':
            passed = actual >= expected
        elif operator == '<=':
            passed = actual <= expected
        elif operator == '==':
            passed = actual == expected
        elif operator == '!=':
            passed = actual != expected

        if not passed:
            error_msg = f"{message}: {var_name}({actual}) {operator} {expected}"
            logger.error(error_msg)
            raise AssertionError(error_msg)

        logger.info(f"Assertion passed: {var_name}({actual}) {operator} {expected}")

        return {
            'status': 'success',
            'passed': True,
            'variable': var_name,
            'actual': actual,
            'expected': expected
        }


# Block registry for dynamic instantiation
BLOCK_REGISTRY = {
    'DelayBlock': DelayBlock,
    'SetVoltageBlock': SetVoltageBlock,
    'SetCurrentBlock': SetCurrentBlock,
    'OutputEnableBlock': OutputEnableBlock,
    'MeasureBlock': MeasureBlock,
    'LoopBlock': LoopBlock,
    'IfBlock': IfBlock,
    'LogDataBlock': LogDataBlock,
    'CommentBlock': CommentBlock,
    'AssertBlock': AssertBlock,
}


def get_block_categories() -> Dict[str, List[str]]:
    """Get blocks organized by category"""
    categories = {}

    for block_class in BLOCK_REGISTRY.values():
        category = block_class.category
        if category not in categories:
            categories[category] = []
        categories[category].append(block_class.name)

    return categories
