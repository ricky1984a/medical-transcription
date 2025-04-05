"""
Google Speech Recognition Service
"""
import os
from pydub import AudioSegment
import wave
from google.cloud import speech
import io
import logging

# Set up logger
logger = logging.getLogger(__name__)


class GoogleSpeechError(Exception):
    """Custom exception for Google Speech API errors"""
    pass


def detect_audio_format(file_path):
    """Detect audio format from file extension"""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    format_map = {
        '.wav': 'wav',
        '.mp3': 'mp3',
        '.flac': 'flac',
        '.ogg': 'ogg',
        '.m4a': 'mp4',
        '.aac': 'aac',
        '.wma': 'wma'
    }

    return format_map.get(ext, None)


def check_audio_quality(file_path):
    """
    Check if audio file contains actual speech or just silence/noise.
    Returns True if audio seems to contain speech, False otherwise.
    """
    try:
        # Load audio file
        audio = AudioSegment.from_file(file_path)

        # Calculate audio statistics
        duration_ms = len(audio)
        if duration_ms < 500:  # Less than half a second
            logger.warning(f"Audio file too short: {duration_ms}ms")
            return False

        # Check volume levels
        max_volume = max(abs(s) for s in audio.get_array_of_samples())
        if max_volume < 500:  # Very quiet audio
            logger.warning(f"Audio level too low: max volume {max_volume}")
            return False

        # Calculate average volume
        avg_volume = sum(abs(s) for s in audio.get_array_of_samples()) / len(audio.get_array_of_samples())
        if avg_volume < 100:  # Background noise level
            logger.warning(f"Average audio level too low: {avg_volume}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking audio quality: {str(e)}")
        return True  # Default to true on error, let the Speech API try


def convert_to_wav(file_path, sample_rate=16000):
    """Convert audio file to WAV format suitable for Google Speech API"""
    logger.info(f"Converting audio file: {file_path}")

    try:
        # Detect original format from extension
        audio_format = detect_audio_format(file_path)
        logger.info(f"Detected format from extension: {audio_format}")

        # If it's a wav file, try to check if it already meets requirements
        if audio_format == 'wav':
            try:
                with wave.open(file_path, 'rb') as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    width = wf.getsampwidth()
                    logger.info(f"WAV file properties: channels={channels}, rate={rate}, width={width}")
                    if channels == 1 and rate == sample_rate and width == 2:  # Check for 16-bit (2 bytes)
                        return file_path  # File already in correct format
            except wave.Error as e:
                logger.warning(f"File has .wav extension but is not a valid WAV file: {str(e)}")
                # Not a valid WAV file, continue with conversion
                audio_format = None

        # Load the audio file with pydub
        try:
            if audio_format:
                logger.info(f"Loading audio using format: {audio_format}")
                audio = AudioSegment.from_file(file_path, format=audio_format)
            else:
                logger.info("Trying to load audio with auto-detection")
                audio = AudioSegment.from_file(file_path)
        except Exception as e:
            logger.error(f"Failed to load audio file: {str(e)}")
            raise GoogleSpeechError(
                f"Could not read audio file: {str(e)}. Please ensure the file is a valid audio format.")

        # Convert to mono, 16-bit PCM, and set sample rate
        logger.info("Converting audio to mono, 16-bit PCM, and setting sample rate")
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(sample_rate)
        audio = audio.set_sample_width(2)  # Set to 16-bit (2 bytes per sample)

        # Create temporary WAV file
        temp_path = f"{file_path}.temp.wav"
        logger.info(f"Exporting to temporary WAV file: {temp_path}")
        audio.export(temp_path, format="wav", parameters=["-acodec", "pcm_s16le"])  # Force 16-bit PCM

        # Verify the exported WAV file
        try:
            with wave.open(temp_path, 'rb') as wf:
                logger.info(
                    f"Exported WAV properties: channels={wf.getnchannels()}, rate={wf.getframerate()}, width={wf.getsampwidth()}")
                if wf.getsampwidth() != 2:
                    logger.error(f"Failed to set correct sample width: got {wf.getsampwidth()} bytes, expected 2 bytes")
                    raise GoogleSpeechError(
                        "Could not convert audio to 16-bit PCM format required by Google Speech API")
        except Exception as e:
            logger.error(f"Failed to verify exported WAV file: {str(e)}")
            raise GoogleSpeechError(f"Failed to create valid WAV file: {str(e)}")

        return temp_path

    except GoogleSpeechError:
        # Re-raise the custom error
        raise
    except Exception as e:
        logger.error(f"Unexpected error in convert_to_wav: {str(e)}", exc_info=True)
        raise GoogleSpeechError(f"Error converting audio: {str(e)}")


def transcribe_audio_google(file_path, language_code="en-US"):
    """
    Transcribe audio using Google Cloud Speech API with enhanced error handling
    and audio format detection
    """
    temp_file = None

    try:
        logger.info(f"Starting transcription for file: {file_path}, language: {language_code}")

        # Initialize Speech client
        client = speech.SpeechClient()

        # Convert to WAV format if needed
        temp_file = convert_to_wav(file_path)
        logger.info(f"Using audio file for transcription: {temp_file}")

        # Check audio quality before proceeding
        if not check_audio_quality(temp_file):
            logger.warning("Audio quality check failed - likely silence or noise")
            return ""  # Return empty string to indicate no speech

        # Get sample rate from WAV file
        with wave.open(temp_file, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            logger.info(f"WAV properties: sample_rate={sample_rate}")

        # Use LINEAR16 encoding (which is what we ensured in convert_to_wav)
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        logger.info(f"Using encoding: {encoding}")

        # Read audio file
        with open(temp_file, "rb") as audio_file:
            content = audio_file.read()

        logger.info(f"Audio file size: {len(content)} bytes")

        # Configure audio recognition
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=encoding,
            sample_rate_hertz=sample_rate,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )

        # Make API request
        logger.info("Sending request to Google Speech-to-Text API")
        response = client.recognize(config=config, audio=audio)

        # Process results
        if not response.results:
            logger.warning("No transcription results returned from Google API")
            return ""

        logger.info(f"Received {len(response.results)} result segments")
        transcript = ""
        for i, result in enumerate(response.results):
            logger.info(f"Result {i + 1} has {len(result.alternatives)} alternatives")
            transcript += result.alternatives[0].transcript + " "

        final_transcript = transcript.strip()
        logger.info(f"Transcription completed: {len(final_transcript)} characters")

        return final_transcript

    except GoogleSpeechError:
        # Re-raise existing GoogleSpeechError
        raise
    except Exception as e:
        logger.error(f"Unexpected error in transcribe_audio_google: {str(e)}", exc_info=True)
        raise GoogleSpeechError(f"Error processing audio: {str(e)}")
    finally:
        # Clean up temp file if created
        if temp_file and temp_file != file_path and os.path.exists(temp_file):
            try:
                logger.info(f"Cleaning up temporary file: {temp_file}")
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {str(e)}")