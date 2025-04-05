"""
Encryption utilities for sensitive data
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app

logger = logging.getLogger(__name__)


def get_encryption_key():
    """
    Get or generate an encryption key

    Returns:
        bytes: The encryption key
    """
    # Try to get from environment
    key = os.environ.get('ENCRYPTION_KEY')

    if key:
        # Decode from base64 if needed
        try:
            return base64.urlsafe_b64decode(key.encode())
        except Exception as e:
            logger.warning(f"Error decoding encryption key from environment: {e}")
            # If not valid base64, derive a key from it
            pass

    # If no key in environment or invalid, derive from application secret
    app_secret = None
    try:
        app_secret = current_app.config.get('SECRET_KEY')
    except RuntimeError:
        # No Flask app context
        pass

    if not app_secret:
        app_secret = os.environ.get('SECRET_KEY', 'fallback-secret-key')

    # Use PBKDF2 to derive a key from the secret
    salt = b'medical-transcription-salt'  # A fixed salt is OK here since the secret_key is already random
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    derived_key = kdf.derive(app_secret.encode() if isinstance(app_secret, str) else app_secret)
    return base64.urlsafe_b64encode(derived_key)


def encrypt_text(text):
    """
    Encrypt sensitive text

    Args:
        text: Text to encrypt

    Returns:
        str: Base64-encoded encrypted text
    """
    if not text:
        return text

    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(text.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}", exc_info=True)
        # Return unencrypted in case of error, but log the issue
        return text


def decrypt_text(encrypted_text):
    """
    Decrypt encrypted text

    Args:
        encrypted_text: Base64-encoded encrypted text

    Returns:
        str: Decrypted text
    """
    if not encrypted_text:
        return encrypted_text

    try:
        key = get_encryption_key()
        f = Fernet(key)
        # First decode the url-safe base64 encoding
        decoded = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
        # Then decrypt
        decrypted_data = f.decrypt(decoded)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}", exc_info=True)
        # Return the encrypted text in case of error
        return f"[Encrypted content - unable to decrypt: {str(e)}]"


def generate_key():
    """
    Generate a new encryption key

    Returns:
        str: Base64-encoded key
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')