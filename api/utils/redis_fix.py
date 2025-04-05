"""
Redis connection helper utilities for handling connection issues
"""
import os
import logging
import redis

logger = logging.getLogger(__name__)


def get_redis_client(redis_url=None):
    """
    Get a Redis client with proper error handling

    Args:
        redis_url: Redis URL string, if None will use environment variable

    Returns:
        Redis client or None if connection fails
    """
    if redis_url is None:
        # Try to get from environment
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("No REDIS_URL found in environment")
            return None

    # Hide password in logs
    safe_url = redis_url
    if '@' in redis_url:
        parts = redis_url.split('@')
        safe_url = f"redis://*****@{parts[1]}" if len(parts) > 1 else redis_url

    logger.info(f"Connecting to Redis at {safe_url}")

    try:
        # Create Redis client using from_url with retry settings
        client = redis.from_url(
            url=redis_url,
            socket_timeout=5,  # 5 second timeout
            socket_connect_timeout=5,
            retry_on_timeout=True,
            decode_responses=False,  # Important - keep binary for limiter
            max_connections=10
        )

        # Test connection
        client.ping()
        logger.info("Redis connection successful")
        return client

    except redis.RedisError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to Redis: {str(e)}")
        return None


def create_redis_connection_string(host, port=6379, password=None, db=0, ssl=False):
    """
    Create a Redis connection string from components

    Args:
        host: Redis host
        port: Redis port
        password: Redis password (optional)
        db: Redis database number
        ssl: Whether to use SSL

    Returns:
        str: Redis connection string
    """
    scheme = "rediss" if ssl else "redis"
    auth = f":{password}@" if password else ""
    return f"{scheme}://{auth}{host}:{port}/{db}"


def test_redis_connection():
    """
    Test Redis connection and return diagnostic info

    Returns:
        dict: Diagnostic information about the Redis connection
    """
    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        return {
            "status": "error",
            "message": "REDIS_URL environment variable not set"
        }

    # Hide password in the URL for reporting
    safe_url = redis_url
    if '@' in safe_url:
        parts = safe_url.split('@')
        auth_part = parts[0].split(':')
        if len(auth_part) > 2:
            auth_part[2] = '***'  # Hide password
            parts[0] = ':'.join(auth_part)
            safe_url = '@'.join(parts)

    diagnostic = {
        "status": "unknown",
        "url": safe_url,
        "details": {}
    }

    try:
        client = redis.from_url(
            url=redis_url,
            socket_timeout=3,
            retry_on_timeout=True
        )

        # Basic connection test
        client.ping()

        # Get Redis info
        info = client.info()

        # Report selected info
        diagnostic.update({
            "status": "connected",
            "message": "Connection successful",
            "details": {
                "redis_version": info.get('redis_version'),
                "uptime_days": info.get('uptime_in_days'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_human": info.get('used_memory_human'),
                "total_connections_received": info.get('total_connections_received')
            }
        })

        # Test basic operations
        test_key = "redis_test_key"
        client.set(test_key, "Redis test value")
        value = client.get(test_key)
        client.delete(test_key)

        if value == b"Redis test value":
            diagnostic["operations_test"] = "passed"
        else:
            diagnostic["operations_test"] = "failed"

        return diagnostic

    except redis.ConnectionError as e:
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "url": safe_url,
            "error_type": "connection_error"
        }
    except redis.RedisError as e:
        return {
            "status": "error",
            "message": f"Redis error: {str(e)}",
            "url": safe_url,
            "error_type": "redis_error"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "url": safe_url,
            "error_type": "unexpected_error"
        }