"""
Enhanced security services for the application
"""
import os
import logging
import uuid
from datetime import datetime
from flask import request

logger = logging.getLogger(__name__)


def setup_security_headers(app):
    """
    Configure security headers for the Flask application with relaxed CSP

    Args:
        app: Flask application instance
    """

    @app.after_request
    def add_security_headers(response):
        """Add security headers to responses"""
        # Content Security Policy - More permissive to allow required functionality
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'self'"
        )

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Enable browser XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # HTTP Strict Transport Security (only in production)
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Cache control for sensitive data
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

    return app

    @app.after_request
    def add_security_headers(response):
        """Add security headers to responses"""
        # Content Security Policy - More restrictive
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Enable browser XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # HTTP Strict Transport Security (only in production)
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Cache control for sensitive data
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        return response

    return app


def setup_cors(app):
    """
    Set up CORS with proper configuration

    Args:
        app: Flask application instance
    """
    from flask_cors import CORS

    # Define allowed origins based on environment
    if app.config.get('ENV') == 'production':
        origins = [
            "https://medical-transcription-75mt.vercel.app/",
            "https://medical-transcription-75mt.vercel.app/"
        ]
    else:
        # Development origins
        origins = [
            "https://medical-transcription-75mt.vercel.app/",
            "https://medical-transcription-75mt.vercel.app/"
        ]

    CORS(app,
         resources={r"/api/*": {"origins": origins, "supports_credentials": True}},
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         expose_headers=["Content-Length", "X-Total-Count"],
         max_age=600)

    return app


def generate_secure_filename(original_filename=None, file_type=None):
    """
    Generate a secure, random filename

    Args:
        original_filename: Original filename (optional)
        file_type: Type of file (e.g., 'audio', 'transcript') (optional)

    Returns:
        str: Secure filename with extension
    """
    # Generate a random UUID
    random_id = uuid.uuid4().hex

    # Get current timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Add file type prefix if provided
    prefix = f"{file_type}_" if file_type else ""

    # Extract extension from original filename if provided
    extension = ""
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if ext:
            extension = ext.lower()

    # Combine to create secure filename
    secure_filename = f"{prefix}{timestamp}_{random_id}{extension}"

    return secure_filename


def log_data_access(user_id, resource_type, resource_id, action):
    """
    Log data access for audit purposes

    Args:
        user_id: ID of the user accessing the data
        resource_type: Type of resource being accessed
        resource_id: ID of the resource
        action: Action being performed
    """
    # Import here to avoid circular imports
    try:
        from ..models.audit_log import AuditLog
        AuditLog.log_phi_access(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action
        )
    except ImportError:
        # Fall back to logging
        logger.info(
            f"DATA ACCESS: User {user_id} performed {action} on {resource_type} {resource_id}"
        )


def setup_api_rate_limiting(app):
    """
    Configure API rate limiting

    Args:
        app: Flask application instance
    """
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        # Try to use redis storage if available
        storage_uri = app.config.get('REDIS_URL', os.environ.get('REDIS_URL'))

        if storage_uri:
            # Import the right storage based on Flask-Limiter version
            try:
                from flask_limiter.util import storage
                if hasattr(storage, 'RedisStorage'):
                    storage_class = storage.RedisStorage(uri=storage_uri)
                else:
                    from flask_limiter.util import RedisStorage
                    storage_class = RedisStorage(storage_uri)
            except ImportError:
                try:
                    from flask_limiter.storage import RedisStorage
                    storage_class = RedisStorage(storage_uri)
                except ImportError:
                    storage_class = None
                    logger.warning("Could not import RedisStorage")
        else:
            storage_class = None

        # Create limiter
        if storage_class:
            limiter = Limiter(
                app,
                key_func=get_remote_address,
                storage=storage_class,
                default_limits=["200 per day", "50 per hour"]
            )
            logger.info("Rate limiting configured with Redis storage")
        else:
            # Fallback to memory storage
            limiter = Limiter(
                app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"]
            )
            logger.warning("Rate limiting configured with memory storage (not recommended for production)")

        # Configure specific rate limits
        limiter.limit("10/minute")(app.route("/api/token", methods=["POST"]))
        limiter.limit("10/minute")(app.route("/api/register", methods=["POST"]))
        limiter.limit("20/minute")(app.route("/api/refresh-token", methods=["POST"]))

        # Store limiter in app for use in routes
        app.limiter = limiter

    except ImportError:
        logger.warning("Flask-Limiter not installed, rate limiting disabled")


def sanitize_input(input_str):
    """
    Sanitize user input to prevent XSS attacks

    Args:
        input_str: Input string to sanitize

    Returns:
        str: Sanitized string
    """
    if not input_str:
        return input_str

    # Import HTML sanitizer if available
    try:
        import bleach
        allowed_tags = ['b', 'i', 'u', 'p', 'br', 'ul', 'ol', 'li', 'strong', 'em']
        allowed_attrs = {'*': ['class']}

        # Sanitize HTML
        return bleach.clean(
            input_str,
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True
        )
    except ImportError:
        # Basic sanitization if bleach is not available
        import html
        return html.escape(input_str)


def validate_request_origin(request, allowed_origins=None):
    """
    Validate request origin for CSRF protection

    Args:
        request: Flask request object
        allowed_origins: List of allowed origins

    Returns:
        bool: True if origin is valid, False otherwise
    """
    if not allowed_origins:
        from flask import current_app
        # Get allowed origins from config
        allowed_origins = current_app.config.get('ALLOWED_ORIGINS', [
            'http://localhost:3000',
            'http://127.0.0.1:3000'
        ])

    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')

    # If no origin or referer, accept request
    # (likely a direct API call or test)
    if not origin and not referer:
        return True

    # Check origin
    if origin and origin in allowed_origins:
        return True

    # Check referer
    if referer:
        for allowed in allowed_origins:
            if referer.startswith(allowed):
                return True

    # Log invalid origin
    logger.warning(f"Invalid request origin: {origin or referer}")
    return False