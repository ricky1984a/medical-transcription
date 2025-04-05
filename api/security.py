"""
Enhanced security utilities for JWT authentication
"""
import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app
from .config import config
from .utils.error_handling import AuthenticationError

# Initialize logger
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = config.get_jwt_secret_key()
ALGORITHM = config.get_jwt_algorithm()
ACCESS_TOKEN_EXPIRE_MINUTES = config.get_jwt_expire_minutes()
REFRESH_TOKEN_EXPIRE_DAYS = config.get_jwt_refresh_expire_days()


def get_token_from_header():
    """Extract JWT token from Authorization header"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    return None


def token_required(f):
    """Decorator to validate JWT tokens for protected routes"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()

        if not token:
            raise AuthenticationError("Missing authentication token")

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Import User model here to avoid circular imports
            from .models.user import User
            user = User.query.filter_by(username=payload['sub']).first()
            if not user:
                raise AuthenticationError("Invalid token - user not found")

            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is inactive")

            g.current_user = user

        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token: {token[:10]}...")
            raise AuthenticationError("Token has expired")

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise AuthenticationError("Invalid token")

        return f(*args, **kwargs)

    return decorated


def create_access_token(data, expires_delta=None):
    """
    Create a new JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration override

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise


def create_refresh_token(data):
    """
    Create a new JWT refresh token with longer expiration

    Args:
        data: Data to encode in the token

    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise