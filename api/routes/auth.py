"""
Enhanced authentication routes with security improvements
"""
from datetime import timedelta
import logging
from flask import Blueprint, request, jsonify, g, current_app
from marshmallow import ValidationError

from ..utils.rate_limiter import get_rate_limit
from ..db import db
from ..models.user import User
from ..models.audit_log import AuditLog
from ..security import token_required, create_access_token, create_refresh_token
from ..schemas import UserSchema, LoginSchema, RefreshTokenSchema
from ..services.auth_protection import (
    check_account_lockout, track_failed_login, reset_failed_login, rate_limit_by_ip
)
from ..utils.error_handling import (
    AuthenticationError, ValidationError as APIValidationError, RateLimitError
)

# Initialize logger
logger = logging.getLogger(__name__)

# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__, url_prefix='/api')


@auth_bp.route('/register', methods=['POST'])
@rate_limit_by_ip(rate="10/minute", key_prefix="register")
def register():
    """Register a new user"""
    try:
        # Validate request data
        schema = UserSchema()
        try:
            data = schema.load(request.json or {})
        except ValidationError as err:
            return jsonify({'message': 'Validation error', 'errors': err.messages}), 400

        username = data['username']
        email = data['email']
        password = data['password']

        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already registered'}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username already taken'}), 400

        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Log user creation
        AuditLog.log_phi_access(
            user_id=new_user.id,
            resource_type='user',
            resource_id=new_user.id,
            action='create',
            description=f"User self-registration with username: {username}, email: {email}"
        )

        # Return user without sensitive fields
        return jsonify(new_user.to_dict()), 201
    except APIValidationError as e:
        # This is from our custom error handling
        return jsonify({'message': e.message, 'details': e.details}), e.status_code
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'message': 'An error occurred during registration',
            'error': str(e) if current_app.debug else 'Internal server error'
        }), 500


@auth_bp.route('/token', methods=['POST'])
@rate_limit_by_ip(rate="15/minute", key_prefix="login")
def login():
    """Login and get access token"""
    # Apply rate limiting from app config
    limiter = current_app.limiter
    limiter.limit(get_rate_limit("auth.token"))(lambda: None)()

    # Validate request data
    if request.is_json:
        # JSON request
        try:
            schema = LoginSchema()
            data = schema.load(request.json or {})
        except ValidationError as err:
            return jsonify({'message': 'Validation error', 'errors': err.messages}), 400

        username = data['username']
        password = data['password']
    else:
        # Form data request
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({'message': 'Missing email or password'}), 400

    # Check for account lockout
    is_locked, remaining_seconds = check_account_lockout(username)
    if is_locked:
        return jsonify({
            'message': f'Account is temporarily locked due to too many failed attempts. Try again in {int(remaining_seconds)} seconds.',
            'lockout_seconds': int(remaining_seconds)
        }), 429

    # Find user by email
    user = User.query.filter_by(email=username).first()

    # Check password
    if not user or not user.check_password(password):
        # Track failed login attempts
        track_failed_login(username)
        logger.warning(f"Failed login attempt for user {username}")
        return jsonify({'message': 'Invalid email or password'}), 401

    # Reset failed login attempts
    reset_failed_login(username)

    # Generate tokens
    access_token_expires = timedelta(minutes=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 30))
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Generate refresh token
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Log successful login
    AuditLog.log_phi_access(
        user_id=user.id,
        resource_type='user',
        resource_id=user.id,
        action='login',
        description=f"User login"
    )

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': access_token_expires.total_seconds()
    })


@auth_bp.route('/refresh-token', methods=['POST'])
@rate_limit_by_ip(rate="30/minute", key_prefix="token-refresh")
def refresh_token_route():
    """Get a new access token using refresh token"""
    try:
        # Validate request
        schema = RefreshTokenSchema()
        try:
            data = schema.load(request.json or {})
        except ValidationError as err:
            return jsonify({'message': 'Validation error', 'errors': err.messages}), 400

        refresh_token = data['refresh_token']

        # Verify refresh token
        try:
            import jwt
            from ..security import SECRET_KEY, ALGORITHM

            # Decode and verify token
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

            # Verify token type
            if payload.get('type') != 'refresh':
                raise jwt.InvalidTokenError("Not a refresh token")

            username = payload.get('sub')

            # Get user
            user = User.query.filter_by(username=username).first()
            if not user:
                raise jwt.InvalidTokenError("User not found")

            # Check if user is active
            if not user.is_active:
                raise jwt.InvalidTokenError("User account is inactive")

            # Generate new access token
            access_token_expires = timedelta(minutes=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 30))
            access_token = create_access_token(
                data={"sub": user.username},
                expires_delta=access_token_expires
            )

            # Log token refresh
            AuditLog.log_phi_access(
                user_id=user.id,
                resource_type='user',
                resource_id=user.id,
                action='token_refresh',
                description="Token refresh"
            )

            return jsonify({
                'access_token': access_token,
                'token_type': 'bearer',
                'expires_in': access_token_expires.total_seconds()
            })

        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired refresh token")
            return jsonify({'message': 'Refresh token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            return jsonify({'message': f'Invalid refresh token: {str(e)}'}), 401

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        return jsonify({'message': 'An error occurred during token refresh'}), 500


@auth_bp.route('/users/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user profile"""
    user = g.current_user

    # Log profile access
    AuditLog.log_phi_access(
        user_id=user.id,
        resource_type='user',
        resource_id=user.id,
        action='view',
        description="User viewed their profile"
    )

    return jsonify(user.to_dict())


@auth_bp.route('/users/me/password', methods=['PUT'])
@token_required
def change_password():
    """Change current user's password"""
    user = g.current_user
    data = request.json

    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({'message': 'Missing current_password or new_password'}), 400

    # Verify current password
    if not user.check_password(data['current_password']):
        # Track failed password change as it could be a security issue
        track_failed_login(user.email)
        logger.warning(f"Failed password change attempt for user {user.username}")
        return jsonify({'message': 'Current password is incorrect'}), 401

    # Reset failed login attempts
    reset_failed_login(user.email)

    # Validate new password
    try:
        # Set new password with validation
        user.set_password(data['new_password'])
        db.session.commit()

        # Log password change
        AuditLog.log_phi_access(
            user_id=user.id,
            resource_type='user',
            resource_id=user.id,
            action='password_change',
            description="User changed their password"
        )

        return jsonify({'message': 'Password changed successfully'})
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'message': 'An error occurred during password change'}), 500


@auth_bp.route('/ping', methods=['GET'])
def ping():
    """Simple health check endpoint"""
    return jsonify({"status": "ok", "message": "Authentication service is running"}), 200