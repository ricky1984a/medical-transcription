"""
Standardized error handling for the API
"""
import traceback
import logging
from flask import jsonify, current_app

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors"""

    def __init__(self, message, status_code=400, error_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

        # Log the error
        if status_code >= 500:
            logger.error(f"{error_code or 'API_ERROR'}: {message}", exc_info=True)
        elif status_code >= 400:
            logger.warning(f"{error_code or 'API_ERROR'}: {message}")


class ResourceNotFoundError(APIError):
    """Resource not found error"""

    def __init__(self, resource_type, resource_id, details=None):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=details
        )


class ValidationError(APIError):
    """Validation error"""

    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(APIError):
    """Authentication error"""

    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(APIError):
    """Authorization error"""

    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class RateLimitError(APIError):
    """Rate limit exceeded error"""

    def __init__(self, message="Rate limit exceeded", retry_after=None, details=None):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error"""

    def __init__(self, message="Service temporarily unavailable", details=None):
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=details
        )


def register_error_handlers(app):
    """Register error handlers for the application"""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle API errors"""
        response = {
            "message": error.message,
            "error_code": error.error_code or "API_ERROR"
        }

        if error.details:
            response["details"] = error.details

        return jsonify(response), error.status_code

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            "message": "Resource not found",
            "error_code": "NOT_FOUND"
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            "message": "Method not allowed",
            "error_code": "METHOD_NOT_ALLOWED"
        }), 405

    @app.errorhandler(500)
    def server_error(error):
        """Handle 500 errors"""
        # Log the error with traceback
        logger.error(f"Internal server error: {error}", exc_info=True)

        # In development, return the full error details
        if app.debug:
            error_details = {
                "error": str(error),
                "traceback": traceback.format_exc()
            }
        else:
            # In production, return minimal details
            error_details = None

        return jsonify({
            "message": "Internal server error",
            "error_code": "SERVER_ERROR",
            "details": error_details
        }), 500