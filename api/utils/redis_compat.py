"""
Redis compatibility module for different Flask-Limiter versions

This module provides a compatibility layer for accessing the RedisStorage class
across different versions of Flask-Limiter.
"""
import logging
import os
import urllib.parse as urlparse  # Import at the module level so it's always available

logger = logging.getLogger(__name__)


def get_redis_storage():
    """
    Get the appropriate RedisStorage class based on the installed flask-limiter version

    Returns:
        RedisStorage class or None if not available
    """
    # First try the limits package directly
    try:
        from limits.storage import RedisStorage
        logger.debug("Using RedisStorage from limits.storage")
        return RedisStorage
    except ImportError:
        logger.debug("Could not import RedisStorage from limits.storage")
        pass

    # Try the newer location (Flask-Limiter >= 3.0.0)
    try:
        from flask_limiter.extensions.storage import RedisStorage
        logger.debug("Using RedisStorage from flask_limiter.extensions.storage")
        return RedisStorage
    except ImportError:
        logger.debug("Could not import RedisStorage from flask_limiter.extensions.storage")
        pass

    # Try other possible locations
    try:
        from flask_limiter.util import storage
        if hasattr(storage, 'RedisStorage'):
            logger.debug("Using RedisStorage from flask_limiter.util.storage")
            return storage.RedisStorage
    except (ImportError, AttributeError):
        logger.debug("Could not import RedisStorage from flask_limiter.util.storage")
        pass

    # Try the older location (Flask-Limiter < 3.0.0)
    try:
        from flask_limiter.storage import RedisStorage
        logger.debug("Using RedisStorage from flask_limiter.storage")
        return RedisStorage
    except ImportError:
        logger.debug("Could not import RedisStorage from flask_limiter.storage")
        pass

    # Try from flask_limiter.util as a last resort
    try:
        from flask_limiter.util import RedisStorage
        logger.debug("Using RedisStorage from flask_limiter.util")
        return RedisStorage
    except ImportError:
        logger.error("Could not import RedisStorage from any location")
        return None


def create_redis_limiter_storage(redis_url=None):
    """
    Create a Redis storage instance for Flask-Limiter

    Args:
        redis_url: Redis URL string, if None will use environment variable

    Returns:
        RedisStorage instance or None if not available
    """
    # Get Redis URL
    if redis_url is None:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.warning("No REDIS_URL found in environment")
            return None

    # Get the RedisStorage class
    RedisStorage = get_redis_storage()
    if not RedisStorage:
        logger.error("No RedisStorage class found")
        return None

    # Parse Redis URL to ensure it's valid
    try:
        parsed = urlparse.urlparse(redis_url)
        if not parsed.hostname:
            logger.error(f"Invalid Redis URL: {redis_url}")
            return None
    except Exception as e:
        logger.error(f"Error parsing Redis URL: {str(e)}")
        return None

    # Create storage instance
    try:
        # Try different initialization methods based on the class signature
        import inspect
        sig = inspect.signature(RedisStorage.__init__)
        param_names = list(sig.parameters.keys())

        # Different RedisStorage implementations have different constructor signatures
        if 'redis_url' in param_names:
            # Newer versions accept redis_url
            logger.debug("Creating RedisStorage with redis_url parameter")
            return RedisStorage(redis_url=redis_url)
        elif 'url' in param_names:
            # Some versions use url
            logger.debug("Creating RedisStorage with url parameter")
            return RedisStorage(url=redis_url)
        elif 'host' in param_names:
            # Older versions need host, port, etc.
            # Extract password from url
            password = None
            if '@' in redis_url:
                auth_part = redis_url.split('@')[0].split('://')[-1]
                if ':' in auth_part:
                    password = auth_part.split(':')[-1]

            # Extract database number
            db = 0
            if parsed.path and parsed.path != '/':
                try:
                    db = int(parsed.path.strip('/'))
                except ValueError:
                    pass

            logger.debug("Creating RedisStorage with host and port parameters")
            return RedisStorage(
                host=parsed.hostname,
                port=parsed.port or 6379,
                password=password,
                db=db
            )
        else:
            # Try with a Redis client directly
            try:
                from redis import Redis
                redis_client = Redis.from_url(redis_url)
                logger.debug("Creating RedisStorage with redis_client parameter")
                return RedisStorage(redis_client)
            except (ImportError, TypeError) as e:
                logger.error(f"Failed to create RedisStorage with Redis client: {e}")
                return None
    except Exception as e:
        logger.error(f"Error creating RedisStorage: {str(e)}")
        return None