"""
Enhanced speech recognition service with improved error handling
"""
import os
import uuid
import tempfile
import logging
import speech_recognition as sr
from ..config import config

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Custom exception for transcription errors"""

    def __init__(self, message, error_type=None, details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details


def save_temp_file(file_content, extension=".wav"):
    """
    Save uploaded file to a temporary location with enhanced error handling

    Args:
        file_content: Binary content of the file
        extension: File extension (default: .wav)

    Returns:
        str: Path to the saved temporary file

    Raises:
        TranscriptionError: If file cannot be saved
    """
    try:
        # Get upload directory from config
        upload_dir = config.get_upload_directory()

        # Ensure upload directory exists
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Validate file content
        if not file_content or len(file_content) == 0:
            raise TranscriptionError(
                "Empty file content provided",
                error_type="EMPTY_FILE"
            )

        # Check file size
        max_size = config.get_max_upload_size()
        if len(file_content) > max_size:
            raise TranscriptionError(
                f"File size exceeds maximum allowed size of {max_size / 1000000:.1f}MB",
                error_type="FILE_TOO_LARGE",
                details={"max_size_mb": max_size / 1000000}
            )

        # Generate unique filename
        filename = f"{uuid.uuid4()}{extension}"
        file_path = os.path.join(upload_dir, filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved successfully to: {file_path}")
        return file_path

    except TranscriptionError:
        # Re-raise custom exceptions
        raise
    except PermissionError:
        raise TranscriptionError(
            "Permission denied when saving file",
            error_type="PERMISSION_ERROR",
            details={"directory": upload_dir}
        )
    except OSError as e:
        raise TranscriptionError(
            f"Failed to save file: {str(e)}",
            error_type="IO_ERROR",
            details={"error": str(e)}
        )
    except Exception as e:
        raise TranscriptionError(
            f"Unexpected error saving file: {str(e)}",
            error_type="UNKNOWN_ERROR",
            details={"error": str(e)}
        )


def validate_audio_file(file_path):
    """
    Validate that the file is a valid audio file that can be processed

    Args:
        file_path: Path to the audio file

    Raises:
        TranscriptionError: If file is invalid or cannot be processed
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise TranscriptionError(
            f"Audio file not found: {file_path}",
            error_type="FILE_NOT_FOUND"
        )

    # Check file extension
    allowed_extensions = config.get_allowed_audio_extensions()
    _, extension = os.path.splitext(file_path)
    if extension.lower() not in allowed_extensions:
        raise TranscriptionError(
            f"Unsupported file format: {extension}. Supported formats: {', '.join(allowed_extensions)}",
            error_type="UNSUPPORTED_FORMAT",
            details={"allowed_extensions": allowed_extensions}
        )

    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        raise TranscriptionError(
            "Audio file is empty",
            error_type="EMPTY_FILE"
        )

    # Try to open the file with speech_recognition to validate it early
    try:
        with sr.AudioFile(file_path) as _:
            pass
    except ValueError as e:
        raise TranscriptionError(
            f"Invalid audio file: {str(e)}",
            error_type="INVALID_AUDIO",
            details={"error": str(e)}
        )


def transcribe_audio(file_path, language=None):
    """
    Transcribe an audio file with enhanced error handling

    Args:
        file_path: Path to the audio file
        language: Language code for transcription (default from config)

    Returns:
        str: Transcribed text

    Raises:
        TranscriptionError: If transcription fails
    """
    # Use default language from config if not specified
    if language is None:
        language = config.get_speech_recognition_language()
        logger.info(f"Using default language for transcription: {language}")

    # Validate the audio file first
    validate_audio_file(file_path)

    try:
        recognizer = sr.Recognizer()

        # Configure noise reduction and adjust sensitivity
        recognizer.dynamic_energy_threshold = True
        recognizer.energy_threshold = 300  # Adjust based on your needs

        with sr.AudioFile(file_path) as source:
            logger.debug(f"Recording audio from file: {file_path}")
            # Adjust for ambient noise for better accuracy
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

            # Use Google's speech recognition service
            logger.debug(f"Transcribing audio with language: {language}")
            text = recognizer.recognize_google(audio_data, language=language)

            if not text or text.strip() == "":
                raise TranscriptionError(
                    "Transcription returned empty text",
                    error_type="EMPTY_TRANSCRIPTION"
                )

            logger.info(f"Transcription successful: {len(text)} characters")
            return text

    except sr.UnknownValueError:
        raise TranscriptionError(
            "Speech could not be recognized. The audio may be unclear or contain no speech.",
            error_type="UNRECOGNIZED_SPEECH"
        )
    except sr.RequestError as e:
        raise TranscriptionError(
            f"Could not request results from speech recognition service: {str(e)}",
            error_type="SERVICE_ERROR",
            details={"error": str(e)}
        )
    except TranscriptionError:
        # Re-raise custom exceptions
        raise
    except Exception as e:
        raise TranscriptionError(
            f"Unexpected error during transcription: {str(e)}",
            error_type="UNKNOWN_ERROR",
            details={"error": str(e)}
        )