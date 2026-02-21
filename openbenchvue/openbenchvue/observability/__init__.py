"""
Observability Package

Prometheus metrics, health checks, and monitoring for production deployments.

Features:
- Prometheus metrics collection
- Kubernetes-style health probes (liveness, readiness, startup)
- System metrics (CPU, memory, disk)
- Application metrics (requests, latency, errors)
- Business metrics (measurements, instruments, sequences)
"""

from .metrics import (
    MetricsCollector,
    get_metrics,
    init_metrics,
    shutdown_metrics,
    track_time,
    count_calls,
    track_errors,
)

from .health import (
    HealthStatus,
    HealthCheck,
    HealthChecker,
    get_health_checker,
    init_health_checker,
    create_database_check,
    create_redis_check,
    create_disk_space_check,
    create_memory_check,
)

__all__ = [
    # Metrics
    'MetricsCollector',
    'get_metrics',
    'init_metrics',
    'shutdown_metrics',
    'track_time',
    'count_calls',
    'track_errors',

    # Health
    'HealthStatus',
    'HealthCheck',
    'HealthChecker',
    'get_health_checker',
    'init_health_checker',
    'create_database_check',
    'create_redis_check',
    'create_disk_space_check',
    'create_memory_check',
]
