"""
Service monitoring and status checking for core functionality
"""
import logging
import time
import os
import speech_recognition as sr
from deep_translator import GoogleTranslator
from ..config import config

logger = logging.getLogger(__name__)


class ServiceStatus:
    """Service status container"""

    def __init__(self, name, status=False, message="", response_time=0):
        self.name = name
        self.status = status
        self.message = message
        self.response_time = response_time
        self.timestamp = time.time()

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "status": "available" if self.status else "unavailable",
            "message": self.message,
            "response_time_ms": round(self.response_time * 1000, 2),
            "timestamp": self.timestamp
        }


def check_speech_recognition_service():
    """Check if speech recognition service is available"""
    start_time = time.time()
    try:
        # Create a recognizer instance
        recognizer = sr.Recognizer()

        # Create a simple audio source
        with sr.AudioFile(get_test_audio_file()) as source:
            # Record a small sample to test service
            audio = recognizer.record(source, duration=1)

            # Just check if the service is responsive
            # We're not checking the transcription accuracy here
            recognizer.recognize_google(audio, language="en-US", show_all=True)

        response_time = time.time() - start_time
        return ServiceStatus(
            name="speech_recognition",
            status=True,
            message="Service is available",
            response_time=response_time
        )
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Speech recognition service check failed: {str(e)}")
        return ServiceStatus(
            name="speech_recognition",
            status=False,
            message=f"Service unavailable: {str(e)}",
            response_time=response_time
        )


def check_translation_service():
    """Check if translation service is available"""
    start_time = time.time()
    try:
        # Set up a simple test phrase
        test_phrase = "Hello, how are you?"

        # Create translator instance
        translator = GoogleTranslator(source='en', target='es')

        # Attempt a simple translation
        result = translator.translate(test_phrase)

        # Check if translation was successful
        if result and len(result) > 0:
            response_time = time.time() - start_time
            return ServiceStatus(
                name="translation",
                status=True,
                message="Service is available",
                response_time=response_time
            )
        else:
            response_time = time.time() - start_time
            return ServiceStatus(
                name="translation",
                status=False,
                message="Service returned empty translation",
                response_time=response_time
            )
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Translation service check failed: {str(e)}")
        return ServiceStatus(
            name="translation",
            status=False,
            message=f"Service unavailable: {str(e)}",
            response_time=response_time
        )


def check_database_service(db):
    """Check if database is available"""
    start_time = time.time()
    try:
        # Attempt a simple query
        db.session.execute("SELECT 1")

        response_time = time.time() - start_time
        return ServiceStatus(
            name="database",
            status=True,
            message="Service is available",
            response_time=response_time
        )
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Database service check failed: {str(e)}")
        return ServiceStatus(
            name="database",
            status=False,
            message=f"Service unavailable: {str(e)}",
            response_time=response_time
        )


def check_file_storage():
    """Check if file storage is available and writeable"""
    start_time = time.time()
    try:
        # Check upload directory
        upload_dir = config.get_upload_directory()

        # Check if directory exists
        if not os.path.exists(upload_dir):
            try:
                os.makedirs(upload_dir)
            except Exception as e:
                response_time = time.time() - start_time
                return ServiceStatus(
                    name="file_storage",
                    status=False,
                    message=f"Could not create upload directory: {str(e)}",
                    response_time=response_time
                )

        # Check if directory is writeable
        test_file = os.path.join(upload_dir, "test_write.tmp")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceStatus(
                name="file_storage",
                status=False,
                message=f"Upload directory not writeable: {str(e)}",
                response_time=response_time
            )

        response_time = time.time() - start_time
        return ServiceStatus(
            name="file_storage",
            status=True,
            message="Service is available",
            response_time=response_time
        )
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"File storage service check failed: {str(e)}")
        return ServiceStatus(
            name="file_storage",
            status=False,
            message=f"Service unavailable: {str(e)}",
            response_time=response_time
        )


def get_test_audio_file():
    """Get path to a test audio file for monitoring purposes"""
    # Check for an existing test file
    test_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "tests",
        "test_audio.wav"
    )

    if os.path.exists(test_file_path):
        return test_file_path

    # If no test file exists, create a minimal WAV file
    try:
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

        with open(test_file_path, "wb") as f:
            # Write a minimal valid WAV file (44 bytes header + 1s silence)
            # WAV header (44 bytes)
            header = (
                    b'RIFF' +  # ChunkID
                    (36).to_bytes(4, 'little') +  # ChunkSize (file size - 8)
                    b'WAVE' +  # Format
                    b'fmt ' +  # Subchunk1ID
                    (16).to_bytes(4, 'little') +  # Subchunk1Size
                    (1).to_bytes(2, 'little') +  # AudioFormat (1 = PCM)
                    (1).to_bytes(2, 'little') +  # NumChannels (1 = mono)
                    (8000).to_bytes(4, 'little') +  # SampleRate (8000 Hz)
                    (8000).to_bytes(4, 'little') +  # ByteRate (SampleRate * NumChannels * BitsPerSample/8)
                    (1).to_bytes(2, 'little') +  # BlockAlign (NumChannels * BitsPerSample/8)
                    (8).to_bytes(2, 'little') +  # BitsPerSample (8 bits)
                    b'data' +  # Subchunk2ID
                    (0).to_bytes(4, 'little')  # Subchunk2Size (data size)
            )
            f.write(header)

        return test_file_path
    except Exception as e:
        logger.error(f"Failed to create test audio file: {str(e)}")
        raise


def check_all_services(db):
    """Check all services and return status"""
    results = {
        "speech_recognition": check_speech_recognition_service().to_dict(),
        "translation": check_translation_service().to_dict(),
        "database": check_database_service(db).to_dict(),
        "file_storage": check_file_storage().to_dict()
    }

    # Calculate overall status
    all_available = all(service["status"] == "available" for service in results.values())

    return {
        "status": "healthy" if all_available else "degraded",
        "services": results
    }


def register_monitoring_routes(app):
    """Register monitoring routes"""
    from flask import jsonify

    @app.route('/api/monitor/status')
    def service_status():
        """Get current status of all services"""
        from ..db import db

        # Check if this is an internal request (for security)
        is_internal = True  # In production, check if request comes from allowed IPs

        if is_internal:
            # Full status with all service details
            return jsonify(check_all_services(db))
        else:
            # Limited status for public
            services = check_all_services(db)
            return jsonify({"status": services["status"]})

    @app.route('/api/monitor/ping')
    def ping():
        """Simple ping endpoint for health checks"""
        return jsonify({"status": "ok"})