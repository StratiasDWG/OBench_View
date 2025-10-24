"""
Enhanced Base Instrument Classes

Advanced features:
- Automatic reconnection with exponential backoff
- Response caching for performance
- State tracking and validation
- Connection pooling
- Performance metrics
- Advanced error recovery
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import hashlib

from .base import BaseInstrument, InstrumentError, InstrumentConnectionError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance tracking for instrument operations"""
    total_commands: int = 0
    failed_commands: int = 0
    total_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    reconnections: int = 0

    def get_success_rate(self) -> float:
        """Calculate command success rate"""
        if self.total_commands == 0:
            return 100.0
        return ((self.total_commands - self.failed_commands) / self.total_commands) * 100

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    def get_average_time(self) -> float:
        """Get average command time"""
        if self.total_commands == 0:
            return 0.0
        return self.total_time / self.total_commands


@dataclass
class CacheEntry:
    """Cache entry with expiration"""
    value: Any
    timestamp: datetime
    ttl: float  # Time to live in seconds

    def is_valid(self) -> bool:
        """Check if cache entry is still valid"""
        return datetime.now() - self.timestamp < timedelta(seconds=self.ttl)


class EnhancedInstrument(BaseInstrument):
    """
    Enhanced instrument with advanced features.

    Features:
    - Automatic reconnection with exponential backoff
    - Response caching for frequently queried values
    - State tracking and validation
    - Performance metrics
    - Health monitoring
    - Command history
    """

    def __init__(self, resource_string: str, rm=None):
        super().__init__(resource_string, rm)

        # Enhanced features
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_enabled = True
        self._cache_default_ttl = 1.0  # seconds

        # Auto-reconnection
        self._auto_reconnect = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay_base = 1.0
        self._last_reconnect_time = None

        # Performance tracking
        self._metrics = PerformanceMetrics()

        # Command history
        self._command_history: List[Dict[str, Any]] = []
        self._max_history = 100

        # State tracking
        self._instrument_state: Dict[str, Any] = {}
        self._state_callbacks: List[Callable] = []

        # Health monitoring
        self._last_health_check = None
        self._health_check_interval = 60.0  # seconds
        self._is_healthy = False

    def _cache_key(self, command: str) -> str:
        """Generate cache key for command"""
        return hashlib.md5(command.encode()).hexdigest()

    def _get_from_cache(self, command: str) -> Optional[str]:
        """Get response from cache if valid"""
        if not self._cache_enabled:
            return None

        key = self._cache_key(command)
        entry = self._cache.get(key)

        if entry and entry.is_valid():
            self._metrics.cache_hits += 1
            logger.debug(f"Cache hit: {command}")
            return entry.value

        self._metrics.cache_misses += 1
        return None

    def _store_in_cache(self, command: str, response: str, ttl: float = None):
        """Store response in cache"""
        if not self._cache_enabled:
            return

        key = self._cache_key(command)
        ttl = ttl or self._cache_default_ttl

        self._cache[key] = CacheEntry(
            value=response,
            timestamp=datetime.now(),
            ttl=ttl
        )

        # Limit cache size
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp
            )
            for key, _ in sorted_entries[:100]:
                del self._cache[key]

    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("Cache cleared")

    def set_cache_enabled(self, enabled: bool):
        """Enable/disable caching"""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()

    def query_cached(self, command: str, ttl: float = None) -> str:
        """
        Query with caching support.

        Args:
            command: SCPI command
            ttl: Cache time-to-live in seconds (None for default)

        Returns:
            Response string
        """
        # Check cache first
        cached = self._get_from_cache(command)
        if cached is not None:
            return cached

        # Query instrument
        response = self.query(command)

        # Store in cache
        self._store_in_cache(command, response, ttl)

        return response

    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnection successful
        """
        if not self._auto_reconnect:
            return False

        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False

        # Calculate backoff delay
        delay = self._reconnect_delay_base * (2 ** self._reconnect_attempts)

        logger.info(f"Attempting reconnection {self._reconnect_attempts + 1}/{self._max_reconnect_attempts} "
                   f"after {delay:.1f}s delay...")

        time.sleep(delay)

        try:
            self.reconnect()
            self._reconnect_attempts = 0
            self._last_reconnect_time = datetime.now()
            self._metrics.reconnections += 1
            logger.info("Reconnection successful")
            return True
        except Exception as e:
            self._reconnect_attempts += 1
            logger.error(f"Reconnection failed: {e}")
            return False

    def query(self, command: str) -> str:
        """Enhanced query with auto-reconnect and metrics"""
        start_time = time.time()

        try:
            response = super().query(command)

            # Update metrics
            self._metrics.total_commands += 1
            self._metrics.total_time += time.time() - start_time

            # Add to history
            self._add_to_history(command, response, success=True)

            return response

        except InstrumentConnectionError as e:
            logger.warning(f"Connection error: {e}")

            # Attempt reconnection
            if self._attempt_reconnect():
                # Retry command
                return self.query(command)
            else:
                self._metrics.failed_commands += 1
                self._add_to_history(command, None, success=False, error=str(e))
                raise

        except Exception as e:
            self._metrics.failed_commands += 1
            self._add_to_history(command, None, success=False, error=str(e))
            raise

    def write(self, command: str):
        """Enhanced write with metrics"""
        start_time = time.time()

        try:
            super().write(command)

            self._metrics.total_commands += 1
            self._metrics.total_time += time.time() - start_time

            self._add_to_history(command, None, success=True)

        except InstrumentConnectionError as e:
            if self._attempt_reconnect():
                return self.write(command)
            else:
                self._metrics.failed_commands += 1
                self._add_to_history(command, None, success=False, error=str(e))
                raise

        except Exception as e:
            self._metrics.failed_commands += 1
            self._add_to_history(command, None, success=False, error=str(e))
            raise

    def _add_to_history(self, command: str, response: str = None,
                       success: bool = True, error: str = None):
        """Add command to history"""
        entry = {
            'timestamp': datetime.now(),
            'command': command,
            'response': response,
            'success': success,
            'error': error
        }

        self._command_history.append(entry)

        # Limit history size
        if len(self._command_history) > self._max_history:
            self._command_history.pop(0)

    def get_command_history(self) -> List[Dict[str, Any]]:
        """Get command history"""
        return self._command_history.copy()

    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics"""
        return self._metrics

    def reset_metrics(self):
        """Reset performance metrics"""
        self._metrics = PerformanceMetrics()
        logger.info("Metrics reset")

    def check_health(self) -> bool:
        """
        Check instrument health.

        Returns:
            True if instrument is healthy
        """
        try:
            # Basic health check: verify communication
            idn = self.query("*IDN?")

            # Check for errors
            errors = self.check_errors()

            self._is_healthy = (idn is not None and len(errors) == 0)
            self._last_health_check = datetime.now()

            return self._is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._is_healthy = False
            return False

    def is_healthy(self) -> bool:
        """
        Check if instrument is healthy (uses cached result if recent).

        Returns:
            True if instrument is healthy
        """
        # Check if we need to perform health check
        if (self._last_health_check is None or
            datetime.now() - self._last_health_check > timedelta(seconds=self._health_check_interval)):
            return self.check_health()

        return self._is_healthy

    def get_state(self, key: str = None) -> Any:
        """
        Get instrument state.

        Args:
            key: State key (None for all state)

        Returns:
            State value or dict of all state
        """
        if key is None:
            return self._instrument_state.copy()
        return self._instrument_state.get(key)

    def set_state(self, key: str, value: Any):
        """
        Set instrument state.

        Args:
            key: State key
            value: State value
        """
        old_value = self._instrument_state.get(key)
        self._instrument_state[key] = value

        # Trigger callbacks
        if old_value != value:
            for callback in self._state_callbacks:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    logger.error(f"State callback error: {e}")

    def register_state_callback(self, callback: Callable):
        """
        Register callback for state changes.

        Args:
            callback: Function(key, old_value, new_value)
        """
        self._state_callbacks.append(callback)

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostics.

        Returns:
            Dictionary with diagnostic information
        """
        metrics = self.get_metrics()

        return {
            'connected': self.connected,
            'healthy': self.is_healthy(),
            'resource': self.resource_string,
            'performance': {
                'total_commands': metrics.total_commands,
                'success_rate': f"{metrics.get_success_rate():.1f}%",
                'avg_time': f"{metrics.get_average_time()*1000:.1f}ms",
                'cache_hit_rate': f"{metrics.get_cache_hit_rate():.1f}%",
                'reconnections': metrics.reconnections,
            },
            'cache': {
                'enabled': self._cache_enabled,
                'size': len(self._cache),
                'ttl': self._cache_default_ttl,
            },
            'state': self._instrument_state.copy(),
            'last_health_check': self._last_health_check,
        }

    def __repr__(self):
        status = "connected" if self.connected else "disconnected"
        health = "healthy" if self._is_healthy else "unknown"
        return f"{self.__class__.__name__}('{self.resource_string}', {status}, {health})"


def with_retry(max_attempts: int = 3, delay: float = 0.5):
    """
    Decorator for automatic retry on failure.

    Args:
        max_attempts: Maximum retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")

            raise last_error

        return wrapper
    return decorator


def with_timeout(timeout_seconds: float):
    """
    Decorator for operation timeout.

    Args:
        timeout_seconds: Timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)

            if thread.is_alive():
                raise TimeoutError(f"Operation timed out after {timeout_seconds}s")

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper
    return decorator


class InstrumentPool:
    """
    Connection pool for managing multiple instrument connections.

    Provides:
    - Connection reuse
    - Automatic cleanup
    - Load balancing
    """

    def __init__(self, max_connections: int = 10):
        """
        Initialize connection pool.

        Args:
            max_connections: Maximum number of connections
        """
        self.max_connections = max_connections
        self._pool: Dict[str, List[EnhancedInstrument]] = {}
        self._lock = threading.Lock()

    def get_connection(self, resource_string: str, instrument_class=None) -> EnhancedInstrument:
        """
        Get connection from pool or create new one.

        Args:
            resource_string: VISA resource string
            instrument_class: Instrument class (None for auto-detect)

        Returns:
            Instrument instance
        """
        with self._lock:
            # Check if we have available connections
            if resource_string in self._pool and self._pool[resource_string]:
                instrument = self._pool[resource_string].pop()

                # Verify connection is still valid
                if instrument.connected:
                    logger.debug(f"Reusing connection from pool: {resource_string}")
                    return instrument

            # Create new connection
            if instrument_class is None:
                instrument_class = EnhancedInstrument

            instrument = instrument_class(resource_string)
            instrument.connect()

            logger.debug(f"Created new connection: {resource_string}")
            return instrument

    def release_connection(self, instrument: EnhancedInstrument):
        """
        Release connection back to pool.

        Args:
            instrument: Instrument to release
        """
        with self._lock:
            resource = instrument.resource_string

            if resource not in self._pool:
                self._pool[resource] = []

            # Only keep if under max connections
            if len(self._pool[resource]) < self.max_connections:
                self._pool[resource].append(instrument)
                logger.debug(f"Released connection to pool: {resource}")
            else:
                instrument.disconnect()
                logger.debug(f"Pool full, closing connection: {resource}")

    def close_all(self):
        """Close all pooled connections"""
        with self._lock:
            for instruments in self._pool.values():
                for instrument in instruments:
                    try:
                        instrument.disconnect()
                    except:
                        pass

            self._pool.clear()
            logger.info("All pooled connections closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                'total_resources': len(self._pool),
                'total_connections': sum(len(conns) for conns in self._pool.values()),
                'max_connections': self.max_connections,
                'resources': {k: len(v) for k, v in self._pool.items()}
            }
