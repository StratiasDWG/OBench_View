"""
Advanced Automation Blocks

Enhanced blocks with:
- Expression evaluation
- Parallel execution
- Exception handling
- Advanced control flow
- Data transformation
"""

import logging
import time
import threading
import ast
import operator
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .blocks import BaseBlock

logger = logging.getLogger(__name__)


class ExpressionEvaluator:
    """
    Safe expression evaluator for automation.

    Supports:
    - Arithmetic operations (+, -, *, /, //, %, **)
    - Comparison operations (>, <, >=, <=, ==, !=)
    - Logical operations (and, or, not)
    - Math functions (abs, min, max, round)
    - Variable references
    """

    # Safe operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Gt: operator.gt,
        ast.Lt: operator.lt,
        ast.GtE: operator.ge,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: lambda x, y: x and y,
        ast.Or: lambda x, y: x or y,
        ast.Not: operator.not_,
    }

    # Safe functions
    FUNCTIONS = {
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'int': int,
        'float': float,
        'str': str,
        'len': len,
    }

    def __init__(self, context):
        """
        Initialize evaluator.

        Args:
            context: Execution context with variables
        """
        self.context = context

    def evaluate(self, expression: str) -> Any:
        """
        Safely evaluate expression.

        Args:
            expression: Expression string

        Returns:
            Evaluated result

        Raises:
            ValueError: If expression is invalid or unsafe
        """
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body)
        except Exception as e:
            raise ValueError(f"Invalid expression '{expression}': {e}")

    def _eval_node(self, node):
        """Recursively evaluate AST node"""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.Str):  # Python 3.7
            return node.s
        elif isinstance(node, ast.Name):
            # Variable reference
            return self.context.get_variable(node.id)
        elif isinstance(node, ast.BinOp):
            # Binary operation
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return self.OPERATORS[op_type](left, right)
            else:
                raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            # Unary operation
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                operand = self._eval_node(node.operand)
                return self.OPERATORS[op_type](operand)
            else:
                raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.Compare):
            # Comparison
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_type = type(op)
                if op_type in self.OPERATORS:
                    if not self.OPERATORS[op_type](left, right):
                        return False
                    left = right
                else:
                    raise ValueError(f"Unsupported comparison: {op_type}")
            return True
        elif isinstance(node, ast.BoolOp):
            # Boolean operation
            op_type = type(node.op)
            if op_type == ast.And:
                return all(self._eval_node(v) for v in node.values)
            elif op_type == ast.Or:
                return any(self._eval_node(v) for v in node.values)
            else:
                raise ValueError(f"Unsupported boolean operator: {op_type}")
        elif isinstance(node, ast.Call):
            # Function call
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in self.FUNCTIONS:
                args = [self._eval_node(arg) for arg in node.args]
                return self.FUNCTIONS[func_name](*args)
            else:
                raise ValueError(f"Unsupported function: {func_name}")
        elif isinstance(node, ast.List):
            # List literal
            return [self._eval_node(elem) for elem in node.elts]
        elif isinstance(node, ast.Tuple):
            # Tuple literal
            return tuple(self._eval_node(elem) for elem in node.elts)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")


class SetVariableBlock(BaseBlock):
    """Set variable with expression evaluation"""

    name = "Set Variable"
    category = "Variables"
    description = "Set variable to value or expression result"
    icon = "="

    def _define_parameters(self):
        self.add_parameter('variable', 'string', 'result', 'Variable Name')
        self.add_parameter('expression', 'string', '0', 'Expression')

    def execute(self, context) -> Dict[str, Any]:
        var_name = self.get_parameter('variable')
        expression = self.get_parameter('expression')

        # Evaluate expression
        evaluator = ExpressionEvaluator(context)
        value = evaluator.evaluate(expression)

        # Set variable
        context.set_variable(var_name, value)

        logger.info(f"Set {var_name} = {value}")

        return {'status': 'success', 'variable': var_name, 'value': value}


class WhileBlock(BaseBlock):
    """While loop with condition"""

    name = "While Loop"
    category = "Control"
    description = "Repeat while condition is true"
    icon = "⟳"

    def _define_parameters(self):
        self.add_parameter('condition', 'string', 'i < 10', 'Condition Expression')
        self.add_parameter('max_iterations', 'int', 1000, 'Max Iterations (safety)',
                          min_value=1, max_value=100000)

    def execute(self, context) -> Dict[str, Any]:
        condition = self.get_parameter('condition')
        max_iterations = self.get_parameter('max_iterations')

        evaluator = ExpressionEvaluator(context)
        iterations = 0

        while iterations < max_iterations:
            try:
                if not evaluator.evaluate(condition):
                    break
            except Exception as e:
                logger.error(f"Condition evaluation failed: {e}")
                break

            # Blocks inside while would be executed here by executor
            iterations += 1

        logger.info(f"While loop completed: {iterations} iterations")

        return {
            'status': 'success',
            'iterations': iterations,
            'max_reached': iterations >= max_iterations
        }


class TryExceptBlock(BaseBlock):
    """Exception handling block"""

    name = "Try-Except"
    category = "Control"
    description = "Handle errors gracefully"
    icon = "⚠️"

    def _define_parameters(self):
        self.add_parameter('continue_on_error', 'bool', True, 'Continue on Error')
        self.add_parameter('error_variable', 'string', 'error', 'Error Variable')

    def execute(self, context) -> Dict[str, Any]:
        # This block serves as a marker for the executor
        # Actual exception handling is implemented in executor
        return {
            'status': 'try_block',
            'continue_on_error': self.get_parameter('continue_on_error'),
            'error_variable': self.get_parameter('error_variable')
        }


class ParallelBlock(BaseBlock):
    """Execute multiple blocks in parallel"""

    name = "Parallel Execution"
    category = "Control"
    description = "Run multiple operations simultaneously"
    icon = "∥"

    def _define_parameters(self):
        self.add_parameter('max_workers', 'int', 4, 'Max Parallel Workers',
                          min_value=1, max_value=16)
        self.add_parameter('wait_all', 'bool', True, 'Wait for All to Complete')

    def execute(self, context) -> Dict[str, Any]:
        # Marker block - executor handles parallel execution
        return {
            'status': 'parallel_start',
            'max_workers': self.get_parameter('max_workers'),
            'wait_all': self.get_parameter('wait_all')
        }


class WaitForBlock(BaseBlock):
    """Wait for condition to become true"""

    name = "Wait For Condition"
    category = "Control"
    description = "Wait until condition is met"
    icon = "⏳"

    def _define_parameters(self):
        self.add_parameter('condition', 'string', 'voltage > 5.0', 'Condition')
        self.add_parameter('timeout', 'float', 10.0, 'Timeout (seconds)',
                          min_value=0.1, max_value=3600)
        self.add_parameter('check_interval', 'float', 0.1, 'Check Interval (seconds)',
                          min_value=0.01, max_value=10)

    def execute(self, context) -> Dict[str, Any]:
        condition = self.get_parameter('condition')
        timeout = self.get_parameter('timeout')
        check_interval = self.get_parameter('check_interval')

        evaluator = ExpressionEvaluator(context)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if evaluator.evaluate(condition):
                    elapsed = time.time() - start_time
                    logger.info(f"Condition met after {elapsed:.2f}s")
                    return {
                        'status': 'success',
                        'condition_met': True,
                        'elapsed_time': elapsed
                    }
            except Exception as e:
                logger.warning(f"Condition evaluation error: {e}")

            time.sleep(check_interval)

        # Timeout reached
        logger.warning(f"Wait timeout after {timeout}s")
        return {
            'status': 'timeout',
            'condition_met': False,
            'elapsed_time': timeout
        }


class MathBlock(BaseBlock):
    """Mathematical operations"""

    name = "Math Operation"
    category = "Data"
    description = "Perform mathematical calculations"
    icon = "∑"

    def _define_parameters(self):
        self.add_parameter('operation', 'choice', 'add', 'Operation',
                          choices=['add', 'subtract', 'multiply', 'divide',
                                 'power', 'sqrt', 'abs', 'round'])
        self.add_parameter('input1', 'string', 'a', 'Input 1 (variable or value)')
        self.add_parameter('input2', 'string', 'b', 'Input 2 (variable or value)')
        self.add_parameter('output', 'string', 'result', 'Output Variable')

    def execute(self, context) -> Dict[str, Any]:
        operation = self.get_parameter('operation')
        input1_expr = self.get_parameter('input1')
        input2_expr = self.get_parameter('input2')
        output_var = self.get_parameter('output')

        evaluator = ExpressionEvaluator(context)

        # Evaluate inputs
        val1 = evaluator.evaluate(input1_expr)
        val2 = evaluator.evaluate(input2_expr) if operation not in ['sqrt', 'abs', 'round'] else None

        # Perform operation
        result = None
        if operation == 'add':
            result = val1 + val2
        elif operation == 'subtract':
            result = val1 - val2
        elif operation == 'multiply':
            result = val1 * val2
        elif operation == 'divide':
            result = val1 / val2 if val2 != 0 else float('inf')
        elif operation == 'power':
            result = val1 ** val2
        elif operation == 'sqrt':
            result = val1 ** 0.5
        elif operation == 'abs':
            result = abs(val1)
        elif operation == 'round':
            result = round(val1)

        context.set_variable(output_var, result)

        logger.info(f"Math: {operation}({val1}, {val2}) = {result}")

        return {
            'status': 'success',
            'operation': operation,
            'result': result,
            'output': output_var
        }


class DataTransformBlock(BaseBlock):
    """Transform data arrays"""

    name = "Data Transform"
    category = "Data"
    description = "Transform data arrays (filter, map, reduce)"
    icon = "⚙️"

    def _define_parameters(self):
        self.add_parameter('input_variable', 'string', 'data', 'Input Variable')
        self.add_parameter('operation', 'choice', 'filter', 'Operation',
                          choices=['filter', 'map', 'slice', 'sort', 'reverse'])
        self.add_parameter('expression', 'string', 'x > 0', 'Expression/Condition')
        self.add_parameter('output_variable', 'string', 'filtered', 'Output Variable')

    def execute(self, context) -> Dict[str, Any]:
        input_var = self.get_parameter('input_variable')
        operation = self.get_parameter('operation')
        expression = self.get_parameter('expression')
        output_var = self.get_parameter('output_variable')

        # Get input data
        data = context.get_variable(input_var)
        if not isinstance(data, (list, tuple)):
            raise ValueError(f"Input must be list or tuple, got {type(data)}")

        result = None

        if operation == 'filter':
            # Filter elements matching condition
            result = []
            for item in data:
                # Create temporary context with 'x' variable
                temp_context = type(context)(context.instruments, context.logger)
                temp_context.variables = context.variables.copy()
                temp_context.set_variable('x', item)

                evaluator = ExpressionEvaluator(temp_context)
                if evaluator.evaluate(expression):
                    result.append(item)

        elif operation == 'map':
            # Apply expression to each element
            result = []
            for item in data:
                temp_context = type(context)(context.instruments, context.logger)
                temp_context.variables = context.variables.copy()
                temp_context.set_variable('x', item)

                evaluator = ExpressionEvaluator(temp_context)
                result.append(evaluator.evaluate(expression))

        elif operation == 'slice':
            # Slice array (expression should be "start:end")
            parts = expression.split(':')
            start = int(parts[0]) if parts[0] else None
            end = int(parts[1]) if len(parts) > 1 and parts[1] else None
            result = list(data[start:end])

        elif operation == 'sort':
            # Sort array
            result = sorted(data)

        elif operation == 'reverse':
            # Reverse array
            result = list(reversed(data))

        context.set_variable(output_var, result)

        logger.info(f"Transform: {operation} on {len(data)} items -> {len(result)} items")

        return {
            'status': 'success',
            'operation': operation,
            'input_size': len(data),
            'output_size': len(result),
            'output': output_var
        }


class SweepBlock(BaseBlock):
    """Parameter sweep with multiple values"""

    name = "Parameter Sweep"
    category = "Control"
    description = "Sweep parameter through range of values"
    icon = "📊"

    def _define_parameters(self):
        self.add_parameter('variable', 'string', 'voltage', 'Variable Name')
        self.add_parameter('start', 'float', 0.0, 'Start Value')
        self.add_parameter('stop', 'float', 10.0, 'Stop Value')
        self.add_parameter('step', 'float', 1.0, 'Step Size', min_value=0.001)
        self.add_parameter('mode', 'choice', 'linear', 'Sweep Mode',
                          choices=['linear', 'logarithmic', 'list'])
        self.add_parameter('values_list', 'string', '', 'Custom Values (comma-separated)')

    def execute(self, context) -> Dict[str, Any]:
        variable = self.get_parameter('variable')
        start = self.get_parameter('start')
        stop = self.get_parameter('stop')
        step = self.get_parameter('step')
        mode = self.get_parameter('mode')
        values_list = self.get_parameter('values_list')

        import numpy as np

        if mode == 'linear':
            values = np.arange(start, stop + step/2, step)
        elif mode == 'logarithmic':
            num_points = int((stop - start) / step) + 1
            values = np.logspace(np.log10(start), np.log10(stop), num_points)
        elif mode == 'list':
            values = [float(v.strip()) for v in values_list.split(',') if v.strip()]
        else:
            values = [start]

        # Store values list for sweep iteration
        context.set_variable(f'{variable}_sweep_values', list(values))
        context.set_variable(f'{variable}_sweep_index', 0)

        logger.info(f"Sweep setup: {variable} with {len(values)} values")

        return {
            'status': 'sweep_start',
            'variable': variable,
            'num_values': len(values),
            'values': list(values)[:10]  # First 10 for logging
        }


# Enhanced block registry
ADVANCED_BLOCK_REGISTRY = {
    'SetVariableBlock': SetVariableBlock,
    'WhileBlock': WhileBlock,
    'TryExceptBlock': TryExceptBlock,
    'ParallelBlock': ParallelBlock,
    'WaitForBlock': WaitForBlock,
    'MathBlock': MathBlock,
    'DataTransformBlock': DataTransformBlock,
    'SweepBlock': SweepBlock,
}
