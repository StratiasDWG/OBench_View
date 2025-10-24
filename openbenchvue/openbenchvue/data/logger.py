"""
Data Logger

Real-time data logging with timestamps and channel management.
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """Single data point with timestamp"""
    timestamp: float
    data: Dict[str, Any]


class DataLogger:
    """
    Real-time data logger with buffering and callbacks.

    Provides BenchVue-like data logging:
    - Multi-channel data collection
    - Time-series buffering
    - Real-time callbacks
    - Circular buffer for memory management
    """

    def __init__(self, buffer_size: int = 10000):
        """
        Initialize data logger.

        Args:
            buffer_size: Maximum number of data points to keep in memory
        """
        self.buffer_size = buffer_size

        # Data storage
        self._data: deque = deque(maxlen=buffer_size)
        self._channels: List[str] = []

        # State
        self._logging = False
        self._start_time = None
        self._log_count = 0

        # Threading
        self._lock = threading.RLock()

        # Callbacks
        self._callbacks: List[Callable] = []

    def start(self):
        """Start logging session"""
        with self._lock:
            if not self._logging:
                self._logging = True
                self._start_time = time.time()
                self._log_count = 0
                logger.info("Data logging started")

    def stop(self):
        """Stop logging session"""
        with self._lock:
            if self._logging:
                self._logging = False
                logger.info(f"Data logging stopped: {self._log_count} points")

    def is_logging(self) -> bool:
        """Check if currently logging"""
        return self._logging

    def log_data(self, data: Dict[str, Any], timestamp: float = None):
        """
        Log data point.

        Args:
            data: Dictionary of channel:value pairs
            timestamp: Custom timestamp (uses current time if None)
        """
        if not self._logging:
            return

        with self._lock:
            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = time.time() - (self._start_time or time.time())

            # Create data point
            point = DataPoint(timestamp=timestamp, data=data)

            # Add to buffer
            self._data.append(point)
            self._log_count += 1

            # Update channel list
            for channel in data.keys():
                if channel not in self._channels:
                    self._channels.append(channel)

            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(point)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            if self._log_count % 1000 == 0:
                logger.debug(f"Logged {self._log_count} data points")

    def register_callback(self, callback: Callable):
        """
        Register callback for new data.

        Args:
            callback: Function to call with each DataPoint
        """
        self._callbacks.append(callback)

    def get_data(self, channel: str = None, start_time: float = None, end_time: float = None) -> List[DataPoint]:
        """
        Retrieve logged data.

        Args:
            channel: Specific channel (None for all)
            start_time: Start time filter
            end_time: End time filter

        Returns:
            List of DataPoint objects
        """
        with self._lock:
            data = list(self._data)

            # Filter by time range
            if start_time is not None:
                data = [d for d in data if d.timestamp >= start_time]
            if end_time is not None:
                data = [d for d in data if d.timestamp <= end_time]

            # Filter by channel
            if channel:
                filtered = []
                for point in data:
                    if channel in point.data:
                        filtered.append(DataPoint(
                            timestamp=point.timestamp,
                            data={channel: point.data[channel]}
                        ))
                return filtered

            return data

    def get_channel_data(self, channel: str) -> tuple:
        """
        Get time-series arrays for a channel.

        Args:
            channel: Channel name

        Returns:
            Tuple of (timestamps, values) as numpy arrays
        """
        with self._lock:
            timestamps = []
            values = []

            for point in self._data:
                if channel in point.data:
                    timestamps.append(point.timestamp)
                    values.append(point.data[channel])

            return np.array(timestamps), np.array(values)

    def get_all_channels_data(self) -> Dict[str, tuple]:
        """
        Get time-series data for all channels.

        Returns:
            Dictionary mapping channel names to (timestamps, values) tuples
        """
        result = {}
        for channel in self._channels:
            result[channel] = self.get_channel_data(channel)
        return result

    def get_channels(self) -> List[str]:
        """Get list of all logged channels"""
        return self._channels.copy()

    def get_statistics(self, channel: str) -> Dict[str, float]:
        """
        Get statistics for a channel.

        Args:
            channel: Channel name

        Returns:
            Dictionary with min, max, mean, std, count
        """
        timestamps, values = self.get_channel_data(channel)

        if len(values) == 0:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'std': 0,
            }

        return {
            'count': len(values),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
        }

    def clear(self):
        """Clear all logged data"""
        with self._lock:
            self._data.clear()
            self._channels.clear()
            self._log_count = 0
            logger.info("Data buffer cleared")

    def get_count(self) -> int:
        """Get total number of logged points"""
        return self._log_count

    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        return len(self._data)

    def get_duration(self) -> float:
        """Get logging duration in seconds"""
        if not self._data:
            return 0.0

        with self._lock:
            return self._data[-1].timestamp - self._data[0].timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Export data as dictionary"""
        with self._lock:
            return {
                'channels': self._channels,
                'count': self._log_count,
                'buffer_size': len(self._data),
                'duration': self.get_duration(),
                'data': [
                    {'timestamp': p.timestamp, **p.data}
                    for p in self._data
                ]
            }

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        status = "logging" if self._logging else "stopped"
        return f"DataLogger({len(self._channels)} channels, {len(self._data)} points, {status})"
