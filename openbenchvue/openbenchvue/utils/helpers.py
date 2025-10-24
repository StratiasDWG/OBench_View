"""
Utility Helper Functions

Common utilities for OpenBenchVue:
- Unit conversion
- Data formatting
- File operations
- Validation
- Performance profiling
"""

import logging
import time
import functools
import re
from typing import Any, Callable, Dict, List, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# Unit Conversions

class UnitConverter:
    """Convert between different units"""

    # Voltage units (to Volts)
    VOLTAGE_UNITS = {
        'V': 1.0,
        'mV': 1e-3,
        'uV': 1e-6,
        'kV': 1e3,
    }

    # Current units (to Amperes)
    CURRENT_UNITS = {
        'A': 1.0,
        'mA': 1e-3,
        'uA': 1e-6,
        'nA': 1e-9,
        'kA': 1e3,
    }

    # Frequency units (to Hertz)
    FREQUENCY_UNITS = {
        'Hz': 1.0,
        'kHz': 1e3,
        'MHz': 1e6,
        'GHz': 1e9,
    }

    # Time units (to seconds)
    TIME_UNITS = {
        's': 1.0,
        'ms': 1e-3,
        'us': 1e-6,
        'ns': 1e-9,
        'min': 60.0,
        'hr': 3600.0,
    }

    # Power units (to Watts)
    POWER_UNITS = {
        'W': 1.0,
        'mW': 1e-3,
        'uW': 1e-6,
        'kW': 1e3,
        'dBm': None,  # Special conversion
    }

    @staticmethod
    def convert(value: float, from_unit: str, to_unit: str, unit_type: str = 'voltage') -> float:
        """
        Convert between units.

        Args:
            value: Value to convert
            from_unit: Source unit
            to_unit: Target unit
            unit_type: Type of unit ('voltage', 'current', 'frequency', 'time', 'power')

        Returns:
            Converted value
        """
        unit_maps = {
            'voltage': UnitConverter.VOLTAGE_UNITS,
            'current': UnitConverter.CURRENT_UNITS,
            'frequency': UnitConverter.FREQUENCY_UNITS,
            'time': UnitConverter.TIME_UNITS,
            'power': UnitConverter.POWER_UNITS,
        }

        unit_map = unit_maps.get(unit_type.lower())
        if not unit_map:
            raise ValueError(f"Unknown unit type: {unit_type}")

        if from_unit not in unit_map or to_unit not in unit_map:
            raise ValueError(f"Invalid units: {from_unit} or {to_unit}")

        # Convert to base unit, then to target unit
        base_value = value * unit_map[from_unit]
        result = base_value / unit_map[to_unit]

        return result

    @staticmethod
    def auto_scale(value: float, unit_type: str = 'voltage') -> Tuple[float, str]:
        """
        Automatically scale value to appropriate unit.

        Args:
            value: Value in base units
            unit_type: Type of unit

        Returns:
            Tuple of (scaled_value, unit)
        """
        unit_maps = {
            'voltage': UnitConverter.VOLTAGE_UNITS,
            'current': UnitConverter.CURRENT_UNITS,
            'frequency': UnitConverter.FREQUENCY_UNITS,
            'time': UnitConverter.TIME_UNITS,
            'power': UnitConverter.POWER_UNITS,
        }

        unit_map = unit_maps.get(unit_type.lower())
        if not unit_map:
            return value, ''

        abs_value = abs(value)

        # Find best unit
        best_unit = None
        best_scaled = abs_value

        for unit, factor in sorted(unit_map.items(), key=lambda x: x[1], reverse=True):
            scaled = abs_value / factor
            if 1.0 <= scaled < 1000.0 or best_unit is None:
                best_unit = unit
                best_scaled = scaled
                break

        return value / unit_map[best_unit], best_unit


class DataFormatter:
    """Format data for display"""

    @staticmethod
    def format_number(value: float, decimals: int = 3, scientific: bool = False) -> str:
        """
        Format number for display.

        Args:
            value: Number to format
            decimals: Number of decimal places
            scientific: Use scientific notation if True

        Returns:
            Formatted string
        """
        if scientific or abs(value) >= 1e6 or (abs(value) < 1e-3 and value != 0):
            return f"{value:.{decimals}e}"
        else:
            return f"{value:.{decimals}f}"

    @staticmethod
    def format_value_with_unit(value: float, unit: str = '', decimals: int = 3) -> str:
        """
        Format value with unit.

        Args:
            value: Value
            unit: Unit string
            decimals: Decimal places

        Returns:
            Formatted string
        """
        formatted = DataFormatter.format_number(value, decimals)
        if unit:
            return f"{formatted} {unit}"
        return formatted

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable form.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    @staticmethod
    def format_size(bytes: int) -> str:
        """
        Format file size in human-readable form.

        Args:
            bytes: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"


class Validator:
    """Data validation utilities"""

    @staticmethod
    def is_valid_scpi(command: str) -> bool:
        """
        Check if string is valid SCPI command.

        Args:
            command: SCPI command string

        Returns:
            True if valid
        """
        if not command:
            return False

        # SCPI commands should contain only alphanumeric, colon, question mark, and spaces
        pattern = r'^[A-Za-z0-9:?\s\-\.,"\']+$'
        return bool(re.match(pattern, command))

    @staticmethod
    def is_valid_visa_resource(resource: str) -> bool:
        """
        Check if string is valid VISA resource string.

        Args:
            resource: Resource string

        Returns:
            True if valid
        """
        # Common VISA resource patterns
        patterns = [
            r'^GPIB\d+::\d+::INSTR$',
            r'^USB\d+::0x[0-9A-Fa-f]{4}::0x[0-9A-Fa-f]{4}::[^:]+::INSTR$',
            r'^TCPIP\d*::.+::(INSTR|SOCKET)$',
            r'^ASRL\d+::INSTR$',
        ]

        return any(re.match(pattern, resource) for pattern in patterns)

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float) -> bool:
        """
        Check if value is within range.

        Args:
            value: Value to check
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            True if in range
        """
        return min_val <= value <= max_val


class Performance:
    """Performance profiling utilities"""

    _timings: Dict[str, List[float]] = {}

    @staticmethod
    def profile(func: Callable = None, name: str = None):
        """
        Decorator to profile function execution time.

        Args:
            func: Function to profile
            name: Custom name for profiling (uses func.__name__ if None)

        Returns:
            Decorated function
        """
        def decorator(f):
            profile_name = name or f.__name__

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = f(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start

                    if profile_name not in Performance._timings:
                        Performance._timings[profile_name] = []

                    Performance._timings[profile_name].append(duration)

                    # Keep only last 100 timings
                    if len(Performance._timings[profile_name]) > 100:
                        Performance._timings[profile_name].pop(0)

            return wrapper

        # Allow use as @profile or @profile(name='...')
        if func is None:
            return decorator
        else:
            return decorator(func)

    @staticmethod
    def get_stats(name: str = None) -> Dict[str, Any]:
        """
        Get profiling statistics.

        Args:
            name: Function name (None for all)

        Returns:
            Dictionary with timing statistics
        """
        import numpy as np

        if name:
            if name not in Performance._timings:
                return {}

            timings = Performance._timings[name]
            return {
                'count': len(timings),
                'total': sum(timings),
                'mean': np.mean(timings),
                'median': np.median(timings),
                'min': np.min(timings),
                'max': np.max(timings),
                'std': np.std(timings),
            }
        else:
            # Return stats for all functions
            stats = {}
            for func_name, timings in Performance._timings.items():
                stats[func_name] = Performance.get_stats(func_name)
            return stats

    @staticmethod
    def reset():
        """Reset profiling data"""
        Performance._timings.clear()

    @staticmethod
    def report() -> str:
        """
        Generate profiling report.

        Returns:
            Formatted report string
        """
        stats = Performance.get_stats()

        if not stats:
            return "No profiling data available"

        lines = ["Performance Profile:", "=" * 60]

        # Sort by total time
        sorted_funcs = sorted(stats.items(), key=lambda x: x[1].get('total', 0), reverse=True)

        for func_name, func_stats in sorted_funcs:
            lines.append(f"\n{func_name}:")
            lines.append(f"  Calls: {func_stats['count']}")
            lines.append(f"  Total: {DataFormatter.format_duration(func_stats['total'])}")
            lines.append(f"  Mean:  {func_stats['mean']*1000:.2f}ms")
            lines.append(f"  Min:   {func_stats['min']*1000:.2f}ms")
            lines.append(f"  Max:   {func_stats['max']*1000:.2f}ms")

        return "\n".join(lines)


class FileHelper:
    """File operation utilities"""

    @staticmethod
    def ensure_directory(path: str) -> Path:
        """
        Ensure directory exists, create if not.

        Args:
            path: Directory path

        Returns:
            Path object
        """
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def get_unique_filename(base_path: str, extension: str = '') -> Path:
        """
        Get unique filename by appending number if needed.

        Args:
            base_path: Base file path
            extension: File extension (with or without dot)

        Returns:
            Unique Path object
        """
        if extension and not extension.startswith('.'):
            extension = f'.{extension}'

        base = Path(base_path)
        if extension:
            base = base.with_suffix(extension)

        if not base.exists():
            return base

        # Append number
        counter = 1
        while True:
            new_path = base.with_stem(f"{base.stem}_{counter}")
            if not new_path.exists():
                return new_path
            counter += 1

    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Convert string to safe filename.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        # Remove invalid characters
        safe = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # Remove leading/trailing whitespace
        safe = safe.strip()

        # Limit length
        if len(safe) > 255:
            safe = safe[:255]

        return safe or "unnamed"

    @staticmethod
    def load_json(path: str) -> Dict[str, Any]:
        """
        Load JSON file.

        Args:
            path: File path

        Returns:
            Dictionary from JSON
        """
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            return {}

    @staticmethod
    def save_json(data: Dict[str, Any], path: str, pretty: bool = True):
        """
        Save data to JSON file.

        Args:
            data: Dictionary to save
            path: File path
            pretty: Pretty-print JSON
        """
        try:
            FileHelper.ensure_directory(Path(path).parent)

            with open(path, 'w') as f:
                if pretty:
                    json.dump(data, f, indent=2)
                else:
                    json.dump(data, f)

            logger.info(f"Saved JSON to {path}")

        except Exception as e:
            logger.error(f"Failed to save JSON to {path}: {e}")
            raise


class RateLimiter:
    """Rate limiting utility"""

    def __init__(self, max_rate: float):
        """
        Initialize rate limiter.

        Args:
            max_rate: Maximum rate in operations/second
        """
        self.max_rate = max_rate
        self.min_interval = 1.0 / max_rate if max_rate > 0 else 0
        self.last_call = 0

    def __call__(self, func):
        """Decorator for rate limiting"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last = now - self.last_call

            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)

            self.last_call = time.time()
            return func(*args, **kwargs)

        return wrapper

    def wait(self):
        """Wait if needed to respect rate limit"""
        now = time.time()
        time_since_last = now - self.last_call

        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)

        self.last_call = time.time()
