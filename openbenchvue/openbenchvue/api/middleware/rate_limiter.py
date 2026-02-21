"""
Rate Limiting Middleware

Token bucket algorithm for API rate limiting to prevent abuse.
"""

import logging
import time
from typing import Dict, Optional, Callable
from functools import wraps
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter"""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket

        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if successful, False if insufficient tokens
        """
        with self._lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            # Check if enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def get_tokens(self) -> float:
        """Get current token count"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            return min(self.capacity, self.tokens + elapsed * self.refill_rate)


class RateLimiter:
    """Rate limiter with multiple strategies"""

    def __init__(
        self,
        default_limit: int = 100,
        default_window: int = 60,
        enable_per_user: bool = True,
        enable_per_ip: bool = True,
        enable_per_endpoint: bool = True,
    ):
        """
        Initialize rate limiter

        Args:
            default_limit: Default request limit
            default_window: Default time window (seconds)
            enable_per_user: Enable per-user limits
            enable_per_ip: Enable per-IP limits
            enable_per_endpoint: Enable per-endpoint limits
        """
        self.default_limit = default_limit
        self.default_window = default_window
        self.enable_per_user = enable_per_user
        self.enable_per_ip = enable_per_ip
        self.enable_per_endpoint = enable_per_endpoint

        # Token buckets
        self.buckets: Dict[str, TokenBucket] = {}
        self._bucket_lock = threading.Lock()

        # Custom limits
        self.custom_limits: Dict[str, tuple] = {}  # key -> (limit, window)

    def set_limit(self, key: str, limit: int, window: int):
        """
        Set custom limit for a key

        Args:
            key: Rate limit key (user, IP, endpoint)
            limit: Request limit
            window: Time window in seconds
        """
        self.custom_limits[key] = (limit, window)

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create token bucket for key"""
        if key not in self.buckets:
            with self._bucket_lock:
                if key not in self.buckets:
                    # Get custom limit or use default
                    limit, window = self.custom_limits.get(key, (self.default_limit, self.default_window))
                    refill_rate = limit / window

                    self.buckets[key] = TokenBucket(capacity=limit, refill_rate=refill_rate)

        return self.buckets[key]

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> tuple:
        """
        Check rate limit

        Args:
            user_id: User identifier
            ip_address: Client IP address
            endpoint: API endpoint

        Returns:
            (allowed, remaining, reset_time)
        """
        # Build rate limit keys
        keys_to_check = []

        if self.enable_per_user and user_id:
            keys_to_check.append(f'user:{user_id}')

        if self.enable_per_ip and ip_address:
            keys_to_check.append(f'ip:{ip_address}')

        if self.enable_per_endpoint and endpoint:
            keys_to_check.append(f'endpoint:{endpoint}')

        # Check all applicable limits
        for key in keys_to_check:
            bucket = self._get_bucket(key)
            if not bucket.consume():
                # Rate limit exceeded
                remaining = int(bucket.get_tokens())
                reset_time = int(time.time() + (1 - bucket.tokens) / bucket.refill_rate)

                logger.warning(f"Rate limit exceeded for {key}")

                return (False, remaining, reset_time)

        # All limits passed
        # Calculate remaining from most restrictive bucket
        if keys_to_check:
            bucket = self._get_bucket(keys_to_check[0])
            remaining = int(bucket.get_tokens())
            reset_time = int(time.time() + bucket.capacity / bucket.refill_rate)
        else:
            remaining = self.default_limit
            reset_time = int(time.time() + self.default_window)

        return (True, remaining, reset_time)

    def cleanup_old_buckets(self, max_age: int = 3600):
        """
        Remove inactive buckets

        Args:
            max_age: Maximum bucket age in seconds
        """
        now = time.time()
        to_remove = []

        with self._bucket_lock:
            for key, bucket in self.buckets.items():
                if now - bucket.last_refill > max_age:
                    to_remove.append(key)

            for key in to_remove:
                del self.buckets[key]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} inactive rate limit buckets")


# ============================================================================
# Decorator for Flask routes
# ============================================================================

def rate_limit(
    limit: Optional[int] = None,
    window: Optional[int] = None,
    per_user: bool = True,
    per_ip: bool = True,
    per_endpoint: bool = True,
):
    """
    Decorator to apply rate limiting to Flask routes

    Args:
        limit: Request limit (None for default)
        window: Time window in seconds (None for default)
        per_user: Apply per-user limit
        per_ip: Apply per-IP limit
        per_endpoint: Apply per-endpoint limit

    Usage:
        @app.route('/api/measurements')
        @rate_limit(limit=10, window=60)
        def get_measurements():
            return jsonify(measurements)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify

            # Get rate limiter instance
            limiter = get_rate_limiter()

            # Extract identifiers
            user_id = getattr(request, 'user_id', None) if per_user else None
            ip_address = request.remote_addr if per_ip else None
            endpoint = request.endpoint if per_endpoint else None

            # Check rate limit
            allowed, remaining, reset_time = limiter.check_rate_limit(
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint
            )

            # Add rate limit headers
            response_headers = {
                'X-RateLimit-Limit': str(limit or limiter.default_limit),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(reset_time),
            }

            if not allowed:
                # Rate limit exceeded
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again after {reset_time - int(time.time())} seconds.',
                    'retry_after': reset_time
                })
                response.status_code = 429
                response.headers.update(response_headers)
                return response

            # Execute route handler
            result = func(*args, **kwargs)

            # Add headers to response
            if hasattr(result, 'headers'):
                result.headers.update(response_headers)

            return result

        return wrapper
    return decorator


# ============================================================================
# Global Rate Limiter Instance
# ============================================================================

_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def init_rate_limiter(
    default_limit: int = 100,
    default_window: int = 60
) -> RateLimiter:
    """Initialize global rate limiter"""
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            default_limit=default_limit,
            default_window=default_window
        )
        logger.info(f"Rate limiter initialized (limit={default_limit}, window={default_window}s)")

    return _rate_limiter
