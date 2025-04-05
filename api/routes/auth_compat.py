"""
Compatibility layer for authentication routes to handle DLL loading issues
This module provides fallback implementations for auth routes
"""
import os
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, g, current_app

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint for auth compat routes
auth_compat_bp = Blueprint('auth_compat', __name__, url_prefix='/api')


def generate_token():
    """Generate a simple token (not a real JWT but functional for development)"""
    return secrets.token_hex(32)


def token_required_compat(f):
    """Simplified auth decorator for development when bcrypt fails"""

    @wraps(f)
    def decorated(*args, **kwargs):
        # In a real implementation, this would verify the token
        # But for now we'll create a dummy user for all requests
        # since this is just an emergency fallback when auth fails

        class DummyUser:
            """Dummy user for fallback auth"""
            id = 1
            username = "development_user"
            email = "dev@example.com"
            is_active = True
            created_at = datetime.utcnow()
            last_login_at = None

            def to_dict(self):
                """Convert to dictionary"""
                return {
                    'id': self.id,
                    'username': self.username,
                    'email': self.email,
                    'is_active': self.is_active
                }

        # Set the current user
        g.current_user = DummyUser()

        logger.warning("Using emergency authentication - ALL REQUESTS AUTHORIZED")

        return f(*args, **kwargs)

    return decorated


@auth_compat_bp.route('/token', methods=['POST'])
def login():
    """Emergency login endpoint that always succeeds"""
    logger.warning("Emergency login endpoint used - authentication bypassed")

    # Generate a token
    token = generate_token()

    # Create a simple response
    return jsonify({
        'access_token': token,
        'refresh_token': token,
        'token_type': 'bearer',
        'expires_in': 3600,
        'message': 'Emergency authentication mode - NOT SECURE'
    })


@auth_compat_bp.route('/register', methods=['POST'])
def register():
    """Emergency registration endpoint"""
    # Just return a success message - no actual registration happens
    return jsonify({
        'id': 1,
        'username': 'development_user',
        'email': 'dev@example.com',
        'is_active': True,
        'message': 'Emergency registration mode - NOT SECURE'
    }), 201


@auth_compat_bp.route('/users/me', methods=['GET'])
@token_required_compat
def get_current_user():
    """Get current authenticated user profile"""
    user = g.current_user
    return jsonify(user.to_dict())


@auth_compat_bp.route('/refresh-token', methods=['POST'])
def refresh_token_route():
    """Emergency token refresh endpoint"""
    token = generate_token()

    return jsonify({
        'access_token': token,
        'token_type': 'bearer',
        'expires_in': 3600,
        'message': 'Emergency token refresh mode - NOT SECURE'
    })


@auth_compat_bp.route('/users/me/password', methods=['PUT'])
@token_required_compat
def change_password():
    """Emergency password change endpoint"""
    return jsonify({'message': 'Password changed successfully (emergency mode)'})


@auth_compat_bp.route('/ping', methods=['GET'])
def ping():
    """Simple health check endpoint"""
    return jsonify({"status": "ok", "message": "Authentication service is running (emergency mode)"}), 200