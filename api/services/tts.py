"""
Text-to-Speech service for converting text to speech
"""
import os
import uuid
import logging
from gtts import gTTS
from ..config import config

logger = logging.getLogger(__name__)


def text_to_speech(text, language=None, output_dir=None):
    """
    Convert text to speech using gTTS

    Args:
        text: Text to convert to speech
        language: Language code for speech (default from config)
        output_dir: Directory to save the audio file (default from config)

    Returns:
        str: Path to the generated audio file or None if failed
    """
    # Use default values from config if not specified
    if language is None:
        language = config.get_default_translation_source()
        logger.info(f"Using default language for TTS: {language}")

    if output_dir is None:
        output_dir = config.get_tts_output_directory()
        logger.info(f"Using default output directory: {output_dir}")

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        logger.debug(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)

    # Check if text is empty
    if not text or not text.strip():
        logger.warning("Empty text provided for TTS conversion")
        return None

    try:
        # Generate a unique filename
        filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(output_dir, filename)

        logger.debug(f"Converting text ({len(text)} chars) to speech in {language}")

        # Generate speech
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(file_path)

        logger.info(f"TTS conversion successful, saved to: {file_path}")
        return file_path
    except ValueError as e:
        # This might occur if the language code is invalid
        logger.error(f"Invalid language code '{language}' for TTS: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error during text-to-speech conversion: {str(e)}", exc_info=True)
        return None


def get_supported_tts_languages():
    """
    Get a list of languages supported by the TTS service

    Returns:
        dict: Dictionary mapping language codes to language names
    """
    try:
        # This is a simplified list - in a real implementation,
        # you might want to get this from the gTTS API
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh-cn": "Chinese (Simplified)",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic"
        }
    except Exception as e:
        logger.error(f"Error getting supported TTS languages: {str(e)}")
        return {"en": "English"}  # Return at least English as fallback