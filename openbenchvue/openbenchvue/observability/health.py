"""
Health Check System

Kubernetes-style health probes for monitoring application health.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


class HealthCheck:
    """Individual health check"""

    def __init__(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 5.0
    ):
        """
        Initialize health check

        Args:
            name: Check name
            check_func: Function that returns (status, message, details)
            critical: Whether this is a critical check
            timeout: Timeout for check execution (seconds)
        """
        self.name = name
        self.check_func = check_func
        self.critical = critical
        self.timeout = timeout
        self.last_check_time: Optional[datetime] = None
        self.last_status: HealthStatus = HealthStatus.UNKNOWN
        self.last_message: str = ''
        self.last_details: Dict[str, Any] = {}

    async def execute(self) -> Dict[str, Any]:
        """
        Execute health check

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            # Execute check with timeout
            if asyncio.iscoroutinefunction(self.check_func):
                result = await asyncio.wait_for(
                    self.check_func(),
                    timeout=self.timeout
                )
            else:
                result = self.check_func()

            # Parse result
            if isinstance(result, tuple):
                status, message, *details = result + (None,)
                details = details[0] if details else {}
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = 'OK' if result else 'Check failed'
                details = {}
            else:
                status = HealthStatus.UNKNOWN
                message = 'Invalid check result'
                details = {}

            self.last_status = status
            self.last_message = message
            self.last_details = details or {}
            self.last_check_time = datetime.utcnow()

            duration = time.time() - start_time

            return {
                'name': self.name,
                'status': status.value,
                'message': message,
                'details': details,
                'critical': self.critical,
                'duration_ms': round(duration * 1000, 2),
                'timestamp': self.last_check_time.isoformat()
            }

        except asyncio.TimeoutError:
            self.last_status = HealthStatus.UNHEALTHY
            self.last_message = f'Check timed out after {self.timeout}s'
            self.last_check_time = datetime.utcnow()

            return {
                'name': self.name,
                'status': HealthStatus.UNHEALTHY.value,
                'message': self.last_message,
                'details': {},
                'critical': self.critical,
                'duration_ms': round(self.timeout * 1000, 2),
                'timestamp': self.last_check_time.isoformat()
            }

        except Exception as e:
            self.last_status = HealthStatus.UNHEALTHY
            self.last_message = f'Check failed: {str(e)}'
            self.last_check_time = datetime.utcnow()

            logger.error(f"Health check '{self.name}' failed: {e}")

            return {
                'name': self.name,
                'status': HealthStatus.UNHEALTHY.value,
                'message': self.last_message,
                'details': {'error': str(e)},
                'critical': self.critical,
                'duration_ms': round((time.time() - start_time) * 1000, 2),
                'timestamp': self.last_check_time.isoformat()
            }


class HealthChecker:
    """Health check manager"""

    def __init__(self):
        """Initialize health checker"""
        self.checks: Dict[str, HealthCheck] = {}
        self._startup_complete = False
        self._shutdown_initiated = False

    def register_check(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 5.0
    ):
        """
        Register a health check

        Args:
            name: Check name
            check_func: Check function
            critical: Whether this is critical
            timeout: Check timeout
        """
        self.checks[name] = HealthCheck(name, check_func, critical, timeout)
        logger.info(f"Registered health check: {name} (critical={critical})")

    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")

    async def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - indicates if application is running

        Returns:
            Liveness status
        """
        if self._shutdown_initiated:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'message': 'Shutdown in progress',
                'timestamp': datetime.utcnow().isoformat()
            }

        return {
            'status': HealthStatus.HEALTHY.value,
            'message': 'Application is running',
            'timestamp': datetime.utcnow().isoformat()
        }

    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - indicates if application can handle requests

        Returns:
            Readiness status with check results
        """
        if not self._startup_complete:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'message': 'Application startup not complete',
                'checks': [],
                'timestamp': datetime.utcnow().isoformat()
            }

        if self._shutdown_initiated:
            return {
                'status': HealthStatus.UNHEALTHY.value,
                'message': 'Shutdown in progress',
                'checks': [],
                'timestamp': datetime.utcnow().isoformat()
            }

        # Execute all checks
        results = []
        for check in self.checks.values():
            result = await check.execute()
            results.append(result)

        # Determine overall status
        critical_failed = any(
            r['status'] == HealthStatus.UNHEALTHY.value and r['critical']
            for r in results
        )
        any_failed = any(r['status'] == HealthStatus.UNHEALTHY.value for r in results)
        any_degraded = any(r['status'] == HealthStatus.DEGRADED.value for r in results)

        if critical_failed:
            overall_status = HealthStatus.UNHEALTHY
            message = 'Critical health checks failed'
        elif any_failed:
            overall_status = HealthStatus.DEGRADED
            message = 'Some health checks failed'
        elif any_degraded:
            overall_status = HealthStatus.DEGRADED
            message = 'Service degraded'
        else:
            overall_status = HealthStatus.HEALTHY
            message = 'All checks passed'

        return {
            'status': overall_status.value,
            'message': message,
            'checks': results,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def check_startup(self) -> Dict[str, Any]:
        """
        Startup probe - indicates if application has completed initialization

        Returns:
            Startup status
        """
        if self._startup_complete:
            return {
                'status': HealthStatus.HEALTHY.value,
                'message': 'Application startup complete',
                'timestamp': datetime.utcnow().isoformat()
            }

        return {
            'status': HealthStatus.UNHEALTHY.value,
            'message': 'Application still starting up',
            'timestamp': datetime.utcnow().isoformat()
        }

    def mark_startup_complete(self):
        """Mark application startup as complete"""
        self._startup_complete = True
        logger.info("Application startup marked as complete")

    def mark_shutdown_initiated(self):
        """Mark shutdown as initiated"""
        self._shutdown_initiated = True
        logger.info("Application shutdown marked as initiated")


# ============================================================================
# Default Health Checks
# ============================================================================

def create_database_check(db_connection) -> Callable:
    """Create database health check"""
    async def check():
        try:
            # Try to execute a simple query
            with db_connection.session_scope() as session:
                session.execute('SELECT 1')

            pool_status = db_connection.get_pool_status()
            checked_out = pool_status.get('checked_out', 0)
            total = pool_status.get('total_connections', 0)

            if total > 0 and checked_out / total > 0.9:
                return (
                    HealthStatus.DEGRADED,
                    'Database connection pool nearly exhausted',
                    pool_status
                )

            return (HealthStatus.HEALTHY, 'Database connection OK', pool_status)

        except Exception as e:
            return (HealthStatus.UNHEALTHY, f'Database connection failed: {e}', {})

    return check


def create_redis_check(redis_client) -> Callable:
    """Create Redis health check"""
    async def check():
        try:
            redis_client.ping()
            info = redis_client.info()

            return (
                HealthStatus.HEALTHY,
                'Redis connection OK',
                {
                    'connected_clients': info.get('connected_clients'),
                    'used_memory_human': info.get('used_memory_human'),
                }
            )

        except Exception as e:
            return (HealthStatus.UNHEALTHY, f'Redis connection failed: {e}', {})

    return check


def create_disk_space_check(threshold_percent: float = 90) -> Callable:
    """Create disk space health check"""
    import psutil

    def check():
        try:
            usage = psutil.disk_usage('/')
            percent = usage.percent

            if percent >= threshold_percent:
                return (
                    HealthStatus.UNHEALTHY,
                    f'Disk usage critical: {percent}%',
                    {'percent': percent, 'free_gb': usage.free / (1024**3)}
                )
            elif percent >= threshold_percent * 0.8:
                return (
                    HealthStatus.DEGRADED,
                    f'Disk usage high: {percent}%',
                    {'percent': percent, 'free_gb': usage.free / (1024**3)}
                )

            return (
                HealthStatus.HEALTHY,
                f'Disk usage OK: {percent}%',
                {'percent': percent, 'free_gb': usage.free / (1024**3)}
            )

        except Exception as e:
            return (HealthStatus.UNKNOWN, f'Disk check failed: {e}', {})

    return check


def create_memory_check(threshold_percent: float = 90) -> Callable:
    """Create memory usage health check"""
    import psutil

    def check():
        try:
            memory = psutil.virtual_memory()
            percent = memory.percent

            if percent >= threshold_percent:
                return (
                    HealthStatus.DEGRADED,
                    f'Memory usage high: {percent}%',
                    {'percent': percent, 'available_gb': memory.available / (1024**3)}
                )

            return (
                HealthStatus.HEALTHY,
                f'Memory usage OK: {percent}%',
                {'percent': percent, 'available_gb': memory.available / (1024**3)}
            )

        except Exception as e:
            return (HealthStatus.UNKNOWN, f'Memory check failed: {e}', {})

    return check


# ============================================================================
# Global Health Checker Instance
# ============================================================================

_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def init_health_checker() -> HealthChecker:
    """Initialize global health checker with default checks"""
    global _health_checker

    if _health_checker is None:
        _health_checker = HealthChecker()

        # Register default checks
        _health_checker.register_check(
            'disk_space',
            create_disk_space_check(threshold_percent=90),
            critical=False
        )
        _health_checker.register_check(
            'memory',
            create_memory_check(threshold_percent=90),
            critical=False
        )

        logger.info("Health checker initialized with default checks")

    return _health_checker
