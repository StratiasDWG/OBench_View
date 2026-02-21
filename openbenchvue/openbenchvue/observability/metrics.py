"""
Metrics Collection with Prometheus

Collect and expose system, application, and business metrics.
"""

import logging
import time
import functools
from typing import Optional, Callable, Any
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import psutil
import threading

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Prometheus metrics collector for OpenBenchVue"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector

        Args:
            registry: Prometheus registry (None for default)
        """
        self.registry = registry or CollectorRegistry()

        # System metrics
        self.system_cpu_percent = Gauge(
            'openbenchvue_system_cpu_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        self.system_memory_percent = Gauge(
            'openbenchvue_system_memory_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        self.system_disk_percent = Gauge(
            'openbenchvue_system_disk_percent',
            'System disk usage percentage',
            ['mount_point'],
            registry=self.registry
        )

        # Application metrics
        self.app_info = Info(
            'openbenchvue_app',
            'Application information',
            registry=self.registry
        )

        # HTTP metrics
        self.http_requests_total = Counter(
            'openbenchvue_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        self.http_request_duration_seconds = Histogram(
            'openbenchvue_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )

        # Database metrics
        self.db_connections_active = Gauge(
            'openbenchvue_db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        self.db_query_duration_seconds = Histogram(
            'openbenchvue_db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )
        self.db_queries_total = Counter(
            'openbenchvue_db_queries_total',
            'Total database queries',
            ['operation', 'status'],
            registry=self.registry
        )

        # Instrument metrics
        self.instruments_connected = Gauge(
            'openbenchvue_instruments_connected',
            'Number of connected instruments',
            registry=self.registry
        )
        self.instrument_connections_total = Counter(
            'openbenchvue_instrument_connections_total',
            'Total instrument connection attempts',
            ['instrument_type', 'status'],
            registry=self.registry
        )

        # Measurement metrics
        self.measurements_total = Counter(
            'openbenchvue_measurements_total',
            'Total measurements taken',
            ['instrument_id', 'measurement_type'],
            registry=self.registry
        )
        self.measurement_rate = Gauge(
            'openbenchvue_measurement_rate',
            'Current measurement rate (measurements/sec)',
            ['instrument_id'],
            registry=self.registry
        )
        self.measurement_value = Gauge(
            'openbenchvue_measurement_value',
            'Latest measurement value',
            ['instrument_id', 'measurement_type'],
            registry=self.registry
        )

        # Automation metrics
        self.sequences_total = Counter(
            'openbenchvue_sequences_total',
            'Total sequence executions',
            ['sequence_name', 'status'],
            registry=self.registry
        )
        self.sequence_duration_seconds = Histogram(
            'openbenchvue_sequence_duration_seconds',
            'Sequence execution duration in seconds',
            ['sequence_name'],
            buckets=(1, 5, 10, 30, 60, 300, 600, 1800, 3600),
            registry=self.registry
        )

        # Anomaly metrics
        self.anomalies_detected_total = Counter(
            'openbenchvue_anomalies_detected_total',
            'Total anomalies detected',
            ['anomaly_type', 'severity'],
            registry=self.registry
        )

        # WebSocket metrics
        self.websocket_connections_active = Gauge(
            'openbenchvue_websocket_connections_active',
            'Active WebSocket connections',
            registry=self.registry
        )
        self.websocket_messages_total = Counter(
            'openbenchvue_websocket_messages_total',
            'Total WebSocket messages',
            ['event_type', 'direction'],
            registry=self.registry
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            'openbenchvue_cache_hits_total',
            'Total cache hits',
            ['cache_name'],
            registry=self.registry
        )
        self.cache_misses_total = Counter(
            'openbenchvue_cache_misses_total',
            'Total cache misses',
            ['cache_name'],
            registry=self.registry
        )

        # Error metrics
        self.errors_total = Counter(
            'openbenchvue_errors_total',
            'Total errors',
            ['error_type', 'severity'],
            registry=self.registry
        )

        # Background metrics collection
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_collection = threading.Event()

    def start_collection(self, interval: int = 15):
        """
        Start automatic metrics collection

        Args:
            interval: Collection interval in seconds
        """
        if self._collection_thread is not None:
            logger.warning("Metrics collection already running")
            return

        def collect_system_metrics():
            while not self._stop_collection.is_set():
                try:
                    # CPU usage
                    self.system_cpu_percent.set(psutil.cpu_percent(interval=1))

                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.system_memory_percent.set(memory.percent)

                    # Disk usage
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            self.system_disk_percent.labels(mount_point=partition.mountpoint).set(usage.percent)
                        except (PermissionError, OSError):
                            pass

                except Exception as e:
                    logger.error(f"Error collecting system metrics: {e}")

                self._stop_collection.wait(interval)

        self._collection_thread = threading.Thread(target=collect_system_metrics, daemon=True)
        self._collection_thread.start()
        logger.info(f"Started metrics collection (interval: {interval}s)")

    def stop_collection(self):
        """Stop automatic metrics collection"""
        if self._collection_thread is None:
            return

        self._stop_collection.set()
        self._collection_thread.join(timeout=5)
        self._collection_thread = None
        logger.info("Stopped metrics collection")

    def set_app_info(self, version: str, environment: str = 'production'):
        """Set application information"""
        self.app_info.info({
            'version': version,
            'environment': environment,
        })

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format

        Returns:
            Metrics in Prometheus exposition format
        """
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get content type for metrics"""
        return CONTENT_TYPE_LATEST


# ============================================================================
# Decorators for automatic instrumentation
# ============================================================================

def track_time(metric: Histogram, labels: Optional[dict] = None):
    """
    Decorator to track function execution time

    Args:
        metric: Histogram metric to record duration
        labels: Optional label values
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator


def count_calls(metric: Counter, labels: Optional[dict] = None):
    """
    Decorator to count function calls

    Args:
        metric: Counter metric to increment
        labels: Optional label values
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def track_errors(metric: Counter, error_type: str = 'unhandled'):
    """
    Decorator to track function errors

    Args:
        metric: Counter metric for errors
        error_type: Type of error to track
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                metric.labels(
                    error_type=error_type,
                    severity=e.__class__.__name__
                ).inc()
                raise
        return wrapper
    return decorator


# ============================================================================
# Global Metrics Instance
# ============================================================================

_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def init_metrics(version: str = '1.0.0', environment: str = 'production') -> MetricsCollector:
    """Initialize global metrics collector"""
    global _metrics

    if _metrics is None:
        _metrics = MetricsCollector()
        _metrics.set_app_info(version, environment)
        _metrics.start_collection()

    return _metrics


def shutdown_metrics():
    """Shutdown global metrics collector"""
    global _metrics

    if _metrics is not None:
        _metrics.stop_collection()
        _metrics = None
