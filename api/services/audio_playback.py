"""
Audio playback service for handling audio files
"""
import os
import uuid
import logging
from flask import send_file, abort
from ..config import config

logger = logging.getLogger(__name__)


class AudioPlaybackError(Exception):
    """Custom exception for audio playback errors"""

    def __init__(self, message, error_type=None, details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details


def get_audio_file(file_path):
    """
    Get an audio file for playback

    Args:
        file_path: Path to the audio file

    Returns:
        FileResponse: Audio file response for streaming

    Raises:
        AudioPlaybackError: If file cannot be accessed
    """
    try:
        # Validate file path
        if not file_path:
            raise AudioPlaybackError(
                "No file path provided",
                error_type="MISSING_PATH"
            )

        # Check if file exists
        if not os.path.exists(file_path):
            raise AudioPlaybackError(
                f"Audio file not found: {file_path}",
                error_type="FILE_NOT_FOUND"
            )

        # Check file extension
        allowed_extensions = config.get_allowed_audio_extensions()
        _, extension = os.path.splitext(file_path)
        if extension.lower() not in allowed_extensions:
            raise AudioPlaybackError(
                f"Unsupported file format: {extension}",
                error_type="UNSUPPORTED_FORMAT",
                details={"allowed_extensions": allowed_extensions}
            )

        # Return file for streaming
        mimetype = get_mime_type(extension)
        return send_file(file_path, mimetype=mimetype)

    except AudioPlaybackError:
        # Re-raise custom exceptions
        raise
    except Exception as e:
        raise AudioPlaybackError(
            f"Error accessing audio file: {str(e)}",
            error_type="ACCESS_ERROR",
            details={"error": str(e)}
        )


def get_mime_type(extension):
    """
    Get the MIME type for an audio file extension

    Args:
        extension: File extension

    Returns:
        str: MIME type
    """
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac'
    }

    return mime_types.get(extension.lower(), 'application/octet-stream')


def create_audio_route(app):
    """
    Create a route for audio file playback

    Args:
        app: Flask application
    """

    @app.route('/api/audio/<path:filename>')
    def serve_audio(filename):
        """Serve audio file"""
        from flask import request, jsonify
        from ..security import token_required

        # Require authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Unauthorized'}), 401

        try:
            # Get upload directory
            upload_dir = config.get_upload_directory()
            file_path = os.path.join(upload_dir, filename)

            # Check if file exists
            if not os.path.exists(file_path):
                return jsonify({'message': 'Audio file not found'}), 404

            # Return file for streaming
            return get_audio_file(file_path)

        except AudioPlaybackError as e:
            return jsonify({
                'message': str(e),
                'error_type': e.error_type,
                'details': e.details
            }), 400
        except Exception as e:
            logger.error(f"Error serving audio file: {str(e)}")
            return jsonify({'message': 'Internal server error'}), 500


def register_audio_routes(app):
    """
    Register audio-related routes

    Args:
        app: Flask application
    """
    # Create audio playback route
    create_audio_route(app)

    # Add route for TTS audio playback
    @app.route('/api/tts/<path:filename>')
    def serve_tts_audio(filename):
        """Serve TTS-generated audio file"""
        from flask import request, jsonify

        try:
            # Get TTS output directory
            tts_dir = config.get_tts_output_directory()
            file_path = os.path.join(tts_dir, filename)

            # Check if file exists
            if not os.path.exists(file_path):
                return jsonify({'message': 'Audio file not found'}), 404

            # Return file for streaming
            return get_audio_file(file_path)

        except AudioPlaybackError as e:
            return jsonify({
                'message': str(e),
                'error_type': e.error_type,
                'details': e.details
            }), 400
        except Exception as e:
            logger.error(f"Error serving TTS audio file: {str(e)}")
            return jsonify({'message': 'Internal server error'}), 500