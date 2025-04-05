"""
Generative AI service for enhanced translation and coding assistance
"""
import os
import logging
import json
from openai import OpenAI
from ..config import config

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Custom exception for AI service errors"""

    def __init__(self, message, error_type=None, details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details


def get_openai_client():
    """Get an initialized OpenAI client"""
    # Get API key from config or environment variable
    api_key = os.environ.get('OPENAI_API_KEY') or config.config.get('services', {}).get('openai', {}).get('api_key')

    if not api_key:
        raise AIServiceError(
            "OpenAI API key not configured",
            error_type="MISSING_API_KEY",
            details={"help": "Set OPENAI_API_KEY environment variable or configure in config.yaml"}
        )

    return OpenAI(api_key=api_key)


def enhanced_translation(text, source_lang, target_lang):
    """
    Translate text using OpenAI's advanced language model

    Args:
        text: Text to translate
        source_lang: Source language code or name
        target_lang: Target language code or name

    Returns:
        str: Translated text

    Raises:
        AIServiceError: If translation fails
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for translation")
        return ""

    try:
        client = get_openai_client()

        # Format the prompt for translation
        prompt = f"""Translate the following text from {source_lang} to {target_lang}.
        Maintain the original formatting, including line breaks and paragraphs.
        For medical terminology, prioritize accuracy and use standard medical terminology in the target language.

        Text to translate:
        {text}
        """

        logger.info(f"Requesting AI translation from {source_lang} to {target_lang}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # You can adjust the model as needed
            messages=[
                {"role": "system", "content": "You are a professional medical translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent translations
            max_tokens=3000,
            top_p=1.0
        )

        # Extract the translation from the response
        translation = response.choices[0].message.content.strip()

        if not translation:
            raise AIServiceError(
                "AI service returned empty translation",
                error_type="EMPTY_RESPONSE"
            )

        logger.info(f"AI translation complete: {len(translation)} characters")
        return translation

    except AIServiceError:
        # Re-raise custom exceptions
        raise
    except Exception as e:
        logger.error(f"Error in AI translation service: {str(e)}", exc_info=True)
        raise AIServiceError(
            f"AI translation failed: {str(e)}",
            error_type="AI_SERVICE_ERROR",
            details={"error": str(e)}
        )


def medical_coding_assistance(transcription_text):
    """
    Use AI to extract medical codes and key information from transcription

    Args:
        transcription_text: The transcribed medical text

    Returns:
        dict: Extracted medical codes and information

    Raises:
        AIServiceError: If code extraction fails
    """
    if not transcription_text or not transcription_text.strip():
        logger.warning("Empty text provided for medical coding")
        return {
            "suggested_codes": [],
            "detected_conditions": [],
            "medications": [],
            "summary": ""
        }

    try:
        client = get_openai_client()

        # Format the prompt for medical coding assistance
        prompt = f"""Analyze the following medical transcription and extract:
        1. Suggested medical codes (ICD-10, CPT) with their descriptions
        2. Detected medical conditions
        3. Medications mentioned
        4. A brief summary of the transcription

        Format the response as a JSON object with these keys:
        "suggested_codes", "detected_conditions", "medications", "summary"

        Medical transcription:
        {transcription_text}
        """

        logger.info("Requesting AI medical coding assistance")
        response = client.chat.completions.create(
            model="gpt-4",  # Using a more advanced model for medical coding
            messages=[
                {"role": "system",
                 "content": "You are a medical coding specialist with expertise in ICD-10 and CPT codes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        # Extract and parse the JSON response
        result_text = response.choices[0].message.content.strip()

        try:
            result = json.loads(result_text)

            # Ensure all expected keys are present
            expected_keys = ["suggested_codes", "detected_conditions", "medications", "summary"]
            for key in expected_keys:
                if key not in result:
                    result[key] = []

            logger.info("AI medical coding complete")
            return result

        except json.JSONDecodeError:
            # If JSON parsing fails, return a structured error response
            logger.error("Failed to parse AI response as JSON")
            raise AIServiceError(
                "Failed to parse AI response as JSON",
                error_type="INVALID_RESPONSE_FORMAT"
            )

    except AIServiceError:
        # Re-raise custom exceptions
        raise
    except Exception as e:
        logger.error(f"Error in AI medical coding service: {str(e)}", exc_info=True)
        raise AIServiceError(
            f"AI medical coding failed: {str(e)}",
            error_type="AI_SERVICE_ERROR",
            details={"error": str(e)}
        )


def summarize_transcription(transcription_text):
    """
    Generate a concise summary of a medical transcription

    Args:
        transcription_text: The transcribed medical text

    Returns:
        str: Summarized text

    Raises:
        AIServiceError: If summarization fails
    """
    if not transcription_text or not transcription_text.strip():
        logger.warning("Empty text provided for summarization")
        return ""

    try:
        client = get_openai_client()

        # Format the prompt for summarization
        prompt = f"""Summarize the following medical transcription in a concise but comprehensive way.
        Include key medical findings, diagnoses, and treatment plans.

        Medical transcription:
        {transcription_text}
        """

        logger.info("Requesting AI transcription summarization")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "You are a medical professional who creates concise summaries of patient encounters."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        # Extract the summary from the response
        summary = response.choices[0].message.content.strip()

        if not summary:
            raise AIServiceError(
                "AI service returned empty summary",
                error_type="EMPTY_RESPONSE"
            )

        logger.info(f"AI summarization complete: {len(summary)} characters")
        return summary

    except AIServiceError:
        # Re-raise custom exceptions
        raise
    except Exception as e:
        logger.error(f"Error in AI summarization service: {str(e)}", exc_info=True)
        raise AIServiceError(
            f"AI summarization failed: {str(e)}",
            error_type="AI_SERVICE_ERROR",
            details={"error": str(e)}
        )