"""
Secure file handling service
"""
import os
import uuid
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from ..utils.error_handling import ValidationError

logger = logging.getLogger(__name__)


def allowed_file(filename, allowed_extensions):
    """
    Check if a file has an allowed extension

    Args:
        filename: Original filename
        allowed_extensions: Set of allowed extensions (without dots)

    Returns:
        bool: True if file extension is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_secure_file_path(original_filename, file_type="file", subdirectory=None):
    """
    Generate a secure path for file storage

    Args:
        original_filename: Original filename provided by the user
        file_type: Type of file (e.g., 'audio', 'document')
        subdirectory: Optional subdirectory within uploads folder

    Returns:
        tuple: (secure_filename, absolute_path)
    """
    # First, secure the filename to remove any potentially dangerous characters
    base_filename = secure_filename(original_filename)

    # Get the file extension
    _, ext = os.path.splitext(base_filename)

    # Create a unique filename with timestamp and UUID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    secure_name = f"{file_type}_{timestamp}_{unique_id}{ext}"

    # Get the base upload directory from config
    base_upload_dir = current_app.config.get(
        'UPLOAD_DIRECTORY',
        os.path.join(current_app.root_path, '..', 'uploads')
    )

    # Create the full directory path
    if subdirectory:
        upload_dir = os.path.join(base_upload_dir, subdirectory)
    else:
        upload_dir = base_upload_dir

    # Ensure the directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Create the full file path
    file_path = os.path.join(upload_dir, secure_name)

    return secure_name, file_path


def save_uploaded_file(file, allowed_extensions=None, max_size_mb=50, file_type="file", subdirectory=None):
    """
    Securely save an uploaded file

    Args:
        file: The uploaded file object
        allowed_extensions: List or set of allowed file extensions (without dots)
        max_size_mb: Maximum allowed file size in MB
        file_type: Type of file for naming (e.g., 'audio', 'document')
        subdirectory: Optional subdirectory within uploads folder

    Returns:
        tuple: (filename, file_path)

    Raises:
        ValidationError: If file validation fails
    """
    if not file:
        raise ValidationError("No file provided")

    if not file.filename:
        raise ValidationError("File has no name")

    # If no extensions specified, get from config or use defaults
    if allowed_extensions is None:
        try:
            # For audio files, get from config
            if file_type == "audio":
                allowed_extensions = current_app.config.get('ALLOWED_AUDIO_EXTENSIONS',
                                                            ['.wav', '.mp3', '.m4a', '.flac'])
            else:
                allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS',
                                                            ['.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'])
        except (RuntimeError, AttributeError):
            # Fallback defaults
            allowed_extensions = ['.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif']

    # Clean up extensions - ensure they're lowercase and without dots
    cleaned_extensions = set()
    for ext in allowed_extensions:
        ext = ext.lower().strip('.')
        cleaned_extensions.add(ext)

    # Check file extension
    if not allowed_file(file.filename, cleaned_extensions):
        raise ValidationError(
            f"File type not allowed. Allowed types: {', '.join(cleaned_extensions)}",
            details={"allowed_extensions": list(cleaned_extensions)}
        )

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer

    # Convert MB to bytes
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValidationError(
            f"File too large. Maximum size: {max_size_mb}MB",
            details={
                "max_size_mb": max_size_mb,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
        )

    # Get secure file path
    secure_name, file_path = get_secure_file_path(
        file.filename, file_type, subdirectory
    )

    # Save the file
    try:
        file.save(file_path)
        logger.info(f"File saved successfully: {file_path}")
        return secure_name, file_path
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}", exc_info=True)
        raise ValidationError(
            f"Error saving file: {str(e)}",
            details={"error": str(e)}
        )


def delete_file(file_path):
    """
    Safely delete a file

    Args:
        file_path: Path to the file to delete

    Returns:
        bool: True if file was deleted, False if not
    """
    if not file_path:
        return False

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False