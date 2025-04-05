"""
Enhanced translation service with improved error handling
"""
import logging
from deep_translator import GoogleTranslator
from ..config import config

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Custom exception for translation errors"""

    def __init__(self, message, error_type=None, details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details


def get_supported_languages():
    """
    Get a list of supported languages for translation

    Returns:
        dict: Dictionary mapping language codes to language names
    """
    try:
        translator = GoogleTranslator()
        languages = translator.get_supported_languages(as_dict=True)
        return languages
    except Exception as e:
        logger.error(f"Error getting supported languages: {str(e)}")
        # Fallback to basic language list
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "zh": "Chinese (Simplified)",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic"
        }


def validate_language_code(lang_code, supported_languages=None):
    """
    Validate that a language code is supported

    Args:
        lang_code: Language code to validate
        supported_languages: Dictionary of supported languages (optional)

    Raises:
        TranslationError: If language code is invalid or unsupported
    """
    if not lang_code:
        raise TranslationError(
            "Language code is required",
            error_type="MISSING_LANGUAGE"
        )

    if supported_languages is None:
        supported_languages = get_supported_languages()

    # Check if the language is supported
    if lang_code not in supported_languages:
        raise TranslationError(
            f"Unsupported language code: {lang_code}",
            error_type="UNSUPPORTED_LANGUAGE",
            details={"supported_languages": list(supported_languages.keys())}
        )


def translate_text(text, source_lang=None, target_lang=None):
    """
    Translate text with enhanced error handling

    Args:
        text: Text to translate
        source_lang: Source language code (default from config)
        target_lang: Target language code (default from config)

    Returns:
        str: Translated text

    Raises:
        TranslationError: If translation fails
    """
    # Use default values from config if not specified
    if source_lang is None:
        source_lang = config.get_default_translation_source()
        logger.info(f"Using default source language: {source_lang}")

    if target_lang is None:
        target_lang = config.get_default_translation_target()
        logger.info(f"Using default target language: {target_lang}")

    # Get supported languages
    supported_languages = get_supported_languages()

    # Validate language codes
    validate_language_code(source_lang, supported_languages)
    validate_language_code(target_lang, supported_languages)

    # Don't translate if source and target languages are the same
    if source_lang == target_lang:
        logger.info(f"Source and target languages are the same ({source_lang}). Skipping translation.")
        return text

    # Check if text is empty
    if not text or not text.strip():
        logger.warning("Empty text provided for translation")
        return ""

    # Check if text is too long (some services have character limits)
    MAX_CHARS = 5000  # Adjust this based on your translation API limits
    if len(text) > MAX_CHARS:
        logger.warning(f"Text exceeds maximum character limit ({len(text)} > {MAX_CHARS})")
        # Handle large text by splitting into chunks
        return translate_large_text(text, source_lang, target_lang, MAX_CHARS)

    try:
        logger.debug(f"Translating text ({len(text)} chars) from {source_lang} to {target_lang}")

        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated_text = translator.translate(text)

        if not translated_text:
            raise TranslationError(
                "Translation returned empty result",
                error_type="EMPTY_TRANSLATION"
            )

        logger.info(f"Translation successful: {len(translated_text)} characters")
        return translated_text

    except ConnectionError as e:
        raise TranslationError(
            f"Connection error during translation: {str(e)}",
            error_type="CONNECTION_ERROR",
            details={"error": str(e)}
        )
    except ValueError as e:
        # This might occur if there's an issue with the language codes
        raise TranslationError(
            f"Invalid parameters for translation: {str(e)}",
            error_type="INVALID_PARAMETERS",
            details={"error": str(e)}
        )
    except Exception as e:
        raise TranslationError(
            f"Unexpected error during translation: {str(e)}",
            error_type="UNKNOWN_ERROR",
            details={"error": str(e)}
        )


def translate_large_text(text, source_lang, target_lang, chunk_size=5000):
    """
    Translate a large text by splitting it into smaller chunks

    Args:
        text: Large text to translate
        source_lang: Source language code
        target_lang: Target language code
        chunk_size: Maximum size of each chunk

    Returns:
        str: Translated text

    Raises:
        TranslationError: If translation fails
    """
    logger.info(f"Splitting large text ({len(text)} chars) into chunks for translation")

    # Split text into sentences to preserve context better
    # This is a simple sentence splitter - you might want to use nltk or spaCy for better results
    sentences = text.replace('!', '.').replace('?', '.').split('.')

    chunks = []
    current_chunk = ""

    # Build chunks of sentences up to the chunk size
    for sentence in sentences:
        if sentence.strip():
            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                chunks.append(current_chunk)
                current_chunk = sentence + "."
            else:
                current_chunk += sentence + "."

    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk)

    logger.info(f"Split text into {len(chunks)} chunks for translation")

    # Translate each chunk
    translated_chunks = []
    translator = GoogleTranslator(source=source_lang, target=target_lang)

    for i, chunk in enumerate(chunks):
        try:
            logger.debug(f"Translating chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")
            translated_chunk = translator.translate(chunk)
            translated_chunks.append(translated_chunk)
        except Exception as e:
            raise TranslationError(
                f"Error translating chunk {i + 1}/{len(chunks)}: {str(e)}",
                error_type="CHUNK_TRANSLATION_ERROR",
                details={"chunk_index": i, "error": str(e)}
            )

    # Combine translated chunks
    full_translation = "".join(translated_chunks)
    logger.info(f"Successfully translated all chunks: {len(full_translation)} characters")

    return full_translation