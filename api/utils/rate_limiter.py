"""
Update the rate_limiter.py file to properly implement get_rate_limit
"""
# api/utils/rate_limiter.py
"""
Rate limiter utilities for API rate limiting
"""
import logging

logger = logging.getLogger(__name__)


def get_rate_limit(endpoint_name, default_limit="30/minute"):
    """
    Get the rate limit for a specific endpoint

    Args:
        endpoint_name: The name of the endpoint
        default_limit: Default limit to use if no configuration found

    Returns:
        str: The rate limit string (e.g. "100/day")
    """
    try:
        # Importing config here to avoid circular imports
        from ..config import config

        # Check if there is a rate limit configuration
        if 'rate_limits' in config.config:
            # Try to get endpoint-specific limit
            rate_limits = config.config.get('rate_limits', {})
            if endpoint_name in rate_limits:
                limit = rate_limits[endpoint_name]
                logger.debug(f"Using configured rate limit for {endpoint_name}: {limit}")
                return limit

        # Fall back to default
        logger.debug(f"Using default rate limit for {endpoint_name}: {default_limit}")
        return default_limit

    except Exception as e:
        logger.error(f"Error getting rate limit for {endpoint_name}: {e}")
        return default_limit