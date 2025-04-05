"""
Enhanced User model with improved security features
"""
import re
import logging
import hashlib
import os
from datetime import datetime
from ..db import db

logger = logging.getLogger(__name__)

class User(db.Model):
    """Model for user accounts with enhanced security"""
    __tablename__ = 'users'

    # Important: Add extend_existing=True to avoid table redefinition errors
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add fields for password reset and account security
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"

    def set_password(self, password):
        """Hash and set the password with enhanced validation"""
        # Validate password complexity
        is_valid, message = self.validate_password(password)
        if not is_valid:
            raise ValueError(message)

        # Try bcrypt first, fall back to pbkdf2 if bcrypt is not available
        try:
            import bcrypt
            password_bytes = password.encode('utf-8')
            # Use a higher cost factor for stronger hashing
            salt = bcrypt.gensalt(rounds=12)
            self.hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
            logger.info(f"Password set with bcrypt for user {self.id}")
        except (ImportError, Exception) as e:
            logger.warning(f"Bcrypt not available, using PBKDF2: {str(e)}")
            # Use PBKDF2 as a fallback
            salt = os.urandom(32)  # Generate a random salt
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000  # Number of iterations
            )
            # Store salt and key together
            self.hashed_password = f"pbkdf2:{salt.hex()}${key.hex()}"
            logger.info(f"Password set with PBKDF2 for user {self.id}")

        # Update password change timestamp
        self.password_changed_at = datetime.utcnow()

        # Reset any password reset token
        self.password_reset_token = None
        self.password_reset_expires = None

    def check_password(self, password):
        """Check if the provided password matches the stored hashed password"""
        if not password or not self.hashed_password:
            return False

        # Handle different password hashing methods
        if self.hashed_password.startswith('pbkdf2:'):
            # PBKDF2 hash
            try:
                # Extract salt and stored key
                hashed_parts = self.hashed_password.split(':')[1].split('$')
                if len(hashed_parts) != 2:
                    logger.error(f"Invalid PBKDF2 hash format for user {self.id}")
                    return False

                salt_hex, stored_key_hex = hashed_parts
                salt = bytes.fromhex(salt_hex)
                stored_key = bytes.fromhex(stored_key_hex)

                # Hash the provided password with the same salt
                key = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    salt,
                    100000  # Same number of iterations as in set_password
                )

                # Compare the generated key with the stored key
                return key == stored_key
            except Exception as e:
                logger.error(f"PBKDF2 password check error for user {self.id}: {str(e)}")
                return False
        else:
            # Assume bcrypt hash
            try:
                import bcrypt
                password_bytes = password.encode('utf-8')
                hashed_bytes = self.hashed_password.encode('utf-8')
                return bcrypt.checkpw(password_bytes, hashed_bytes)
            except ImportError:
                logger.error(f"Bcrypt not available for password check for user {self.id}")
                return False
            except Exception as e:
                logger.error(f"Bcrypt password check error for user {self.id}: {str(e)}")
                return False

    @staticmethod
    def validate_password(password):
        """
        Validate password strength

        Args:
            password: Password to validate

        Returns:
            tuple: (is_valid, message)
        """
        if not password:
            return False, "Password cannot be empty"

        if len(password) < 12:
            return False, "Password must be at least 12 characters long"

        # Check for complexity requirements
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'[0-9]', password))
        has_special = bool(re.search(r'[^A-Za-z0-9]', password))

        missing = []
        if not has_upper:
            missing.append("uppercase letter")
        if not has_lower:
            missing.append("lowercase letter")
        if not has_digit:
            missing.append("digit")
        if not has_special:
            missing.append("special character")

        if missing:
            return False, f"Password must contain at least one {', '.join(missing)}"

        # Check for common passwords (simplified)
        common_passwords = [
            "password123", "qwerty123", "123456789", "admin123", "welcome1",
            "letmein123", "123qwerty", "adminadmin", "P@ssword1", "Password123"
        ]

        if password.lower() in common_passwords:
            return False, "Password is too common and easily guessable"

        return True, "Password meets requirements"

    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None
        }

    def record_login(self):
        """Record successful login"""
        self.last_login_at = datetime.utcnow()
        self.login_attempts = 0
        db.session.commit()