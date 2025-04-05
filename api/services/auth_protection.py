"""
Authentication protection services for account security
"""
import time
import os
import logging
from functools import wraps  # Add this import for the wraps decorator
from flask import current_app, request
import redis
from ..utils.error_handling import RateLimitError

# Initialize logger
logger = logging.getLogger(__name__)

# Max failed login attempts before lockout (default 5)
MAX_FAILED_ATTEMPTS = int(os.environ.get("MAX_FAILED_ATTEMPTS", "5"))

# Lockout period in seconds (default 15 minutes = 900 seconds)
LOCKOUT_PERIOD = int(os.environ.get("LOCKOUT_PERIOD", "900"))


def get_redis_client():
    """
    Get a Redis client for tracking failed logins

    Returns:
        Redis client or None if not available
    """
    try:
        # If already initialized, reuse
        if hasattr(current_app, 'redis_client') and current_app.redis_client:
            return current_app.redis_client

        # Get Redis URL from environment
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("No REDIS_URL in environment")
            return None

        # Create new Redis client
        redis_client = redis.from_url(redis_url)

        # Test connection
        redis_client.ping()

        # Cache for reuse
        current_app.redis_client = redis_client
        logger.info("Redis client initialized successfully")

        return redis_client

    except Exception as e:
        logger.error(f"Could not connect to Redis: {str(e)}")
        current_app.redis_client = None
        return None


def track_failed_login(username):
    """
    Track failed login attempts

    Args:
        username: Username or email that failed login
    """
    redis_client = get_redis_client()

    if redis_client:
        # Use Redis to track failed attempts
        key = f"login:failed:{username}"
        attempts = redis_client.incr(key)
        redis_client.set(f"{key}:timestamp", time.time())

        # Set expiration to avoid stale keys
        redis_client.expire(key, LOCKOUT_PERIOD * 2)
        redis_client.expire(f"{key}:timestamp", LOCKOUT_PERIOD * 2)

        logger.warning(f"Failed login attempt for {username} ({attempts}/{MAX_FAILED_ATTEMPTS})")

        # Check if account should be locked
        if attempts >= MAX_FAILED_ATTEMPTS:
            logger.warning(f"Account locked for {username} after {attempts} failed attempts")
    else:
        # Fallback to logging only
        logger.warning(f"Failed login attempt for {username} (Redis unavailable)")


def reset_failed_login(username):
    """
    Reset failed login attempts after successful login

    Args:
        username: Username or email that succeeded login
    """
    redis_client = get_redis_client()

    if redis_client:
        key = f"login:failed:{username}"
        redis_client.delete(key)
        redis_client.delete(f"{key}:timestamp")
        logger.info(f"Reset failed login counter for {username}")


def check_account_lockout(username):
    """
    Check if account is locked due to failed attempts

    Args:
        username: Username or email to check

    Returns:
        tuple: (is_locked, remaining_seconds)
    """
    redis_client = get_redis_client()

    if not redis_client:
        return False, 0

    key = f"login:failed:{username}"
    attempts_str = redis_client.get(key)

    if not attempts_str:
        return False, 0

    attempts = int(attempts_str)

    if attempts >= MAX_FAILED_ATTEMPTS:
        # Check if lockout period has passed
        timestamp_str = redis_client.get(f"{key}:timestamp")
        if not timestamp_str:
            return False, 0

        last_attempt = float(timestamp_str)
        elapsed = time.time() - last_attempt

        if elapsed < LOCKOUT_PERIOD:
            remaining = LOCKOUT_PERIOD - elapsed
            logger.warning(f"Account {username} is locked for {int(remaining)} more seconds")
            return True, remaining

        # Reset counter if lockout period has passed
        logger.info(f"Lockout period expired for {username}, resetting counter")
        redis_client.delete(key)
        redis_client.delete(f"{key}:timestamp")

    return False, 0


def rate_limit_by_ip(rate="30/minute", key_prefix="rate-limit"):
    """
    Decorator function to apply rate limiting by IP address

    Args:
        rate: Rate limit string (e.g. "30/minute", "100/hour")
        key_prefix: Redis key prefix for rate limiting

    Returns:
        Function decorator
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            redis_client = get_redis_client()

            if not redis_client:
                # If Redis is unavailable, skip rate limiting
                return f(*args, **kwargs)

            # Get client IP
            ip = request.remote_addr

            # Parse rate limit
            count, period = rate.split('/')
            count = int(count)

            # Calculate expiration based on period
            if period == 'second':
                expiration = 1
            elif period == 'minute':
                expiration = 60
            elif period == 'hour':
                expiration = 3600
            elif period == 'day':
                expiration = 86400
            else:
                raise ValueError(f"Invalid rate limit period: {period}")

            # Create rate limit key
            key = f"{key_prefix}:{ip}:{f.__name__}"

            # Increment counter
            current = redis_client.incr(key)

            # Set expiration if this is the first request
            if current == 1:
                redis_client.expire(key, expiration)

            # Check if rate limit exceeded
            if current > count:
                # Get time to reset
                ttl = redis_client.ttl(key)
                logger.warning(f"Rate limit exceeded for IP {ip} on {f.__name__}")
                raise RateLimitError(
                    message=f"Rate limit exceeded. Try again in {ttl} seconds.",
                    retry_after=ttl,
                    details={"limit": count, "period": period}
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator