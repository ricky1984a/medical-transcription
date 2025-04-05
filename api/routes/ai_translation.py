"""
Enhanced translation routes with AI integration
"""
import logging
from flask import Blueprint, request, jsonify, g, current_app
from ..utils.rate_limiter import get_rate_limit
from ..db import db
from ..models.transcript import Transcription
from ..models.translation import Translation
from ..security import token_required
from ..services.security_service import log_data_access

# Create blueprint for AI translation routes
ai_translation_bp = Blueprint('ai_translation', __name__, url_prefix='/api')


# Import AI translation service with fallback
def get_translation_service():
    """Get the best available translation service"""
    logger = current_app.logger if current_app else logging.getLogger(__name__)

    # Try each service in order of preference
    services = [
        ('AI-enhanced translation',
         lambda: __import__('app.services.ai_service', fromlist=['enhanced_translation']).enhanced_translation),
        ('Improved translation',
         lambda: __import__('app.services.improved_translation', fromlist=['translate_text']).translate_text),
        (
        'Basic translation', lambda: __import__('app.services.translation', fromlist=['translate_text']).translate_text)
    ]

    for service_name, import_func in services:
        try:
            logger.info(f"Attempting to load {service_name} service")
            translation_service = import_func()
            logger.info(f"Successfully loaded {service_name} service")
            return translation_service
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load {service_name} service: {str(e)}")
            continue

    # If all else fails, provide a simple fallback
    logger.error("All translation services failed to load. Using emergency fallback.")

    def emergency_fallback_translation(text, source_lang=None, target_lang=None):
        """Very basic translation fallback that just returns the original text"""
        logger.warning(f"Using emergency fallback translation from {source_lang} to {target_lang}")
        return f"[Translation from {source_lang} to {target_lang} unavailable] {text}"

    return emergency_fallback_translation


@ai_translation_bp.route('/ai/translations', methods=['POST'])
@token_required
def create_ai_translation():
    """Create a new translation using AI for enhanced accuracy"""
    # Apply rate limiting
    limiter = current_app.limiter
    limiter.limit(get_rate_limit("api.translations"))(lambda: None)()

    # Get logger
    logger = current_app.logger

    # Log the incoming request for debugging
    logger.info(f"Translation request received")

    # Get data
    data = request.get_json(force=True, silent=True)
    logger.info(f"Processed request data: {data}")

    if not data:
        return jsonify({
            'message': 'No input data provided or invalid JSON format',
            'error_type': 'INVALID_DATA'
        }), 400

    # Handle both API formats - direct text or transcription reference
    target_language = data.get('target_language')
    high_quality = data.get('high_quality', True)

    if not target_language:
        return jsonify({
            'message': 'Missing required field: target_language',
            'error_type': 'MISSING_FIELDS'
        }), 400

    # Check if we're working with a transcription or direct text
    transcription_id = data.get('transcription_id')
    text = data.get('text')
    source_language = data.get('source_language', 'en')

    if transcription_id:
        # Handle translation via transcription reference
        # Try to convert transcription_id to int if it's a string
        if isinstance(transcription_id, str):
            try:
                transcription_id = int(transcription_id)
            except ValueError:
                logger.error(f"Invalid transcription_id format: {transcription_id}")
                return jsonify({
                    'message': 'Invalid transcription ID format',
                    'error_type': 'INVALID_ID'
                }), 400

        # Check if transcription exists and belongs to user
        transcription = (
            Transcription.query
            .filter_by(id=transcription_id, user_id=g.current_user.id)
            .first()
        )

        if not transcription:
            return jsonify({
                'message': 'Transcription not found or does not belong to current user',
                'error_type': 'NOT_FOUND'
            }), 404

        # Check if transcription has content
        if not transcription.content or not transcription.content.strip():
            return jsonify({
                'message': 'Transcription has no content to translate',
                'error_type': 'EMPTY_CONTENT'
            }), 400

        # Get text and source language from transcription
        text = transcription.content
        source_language = transcription.language

        # Create translation record
        translation = Translation(
            transcription_id=transcription.id,
            source_language=source_language,
            target_language=target_language,
            status="processing"
        )
    elif text:
        # Handle direct text translation without transcription reference
        # Create a temporary transcription to hold the text
        temp_transcription = Transcription(
            title=f"Direct Translation {source_language} -> {target_language}",
            language=source_language,
            user_id=g.current_user.id,
            status='completed',
            content=text
        )

        db.session.add(temp_transcription)
        db.session.commit()

        # Create translation record
        translation = Translation(
            transcription_id=temp_transcription.id,
            source_language=source_language,
            target_language=target_language,
            status="processing"
        )
    else:
        return jsonify({
            'message': 'Missing required field: either transcription_id or text must be provided',
            'error_type': 'MISSING_FIELDS'
        }), 400

    # Save the translation record
    db.session.add(translation)
    db.session.commit()

    try:
        # Get the translation service
        translate_text_service = get_translation_service()

        # Log message about which service is being used
        if high_quality:
            logger.info(f"Using enhanced AI translation for translation {translation.id}")
        else:
            logger.info(f"Using standard translation for translation {translation.id}")

        # Translate the content
        translated_text = translate_text_service(
            text,
            source_lang=source_language,
            target_lang=target_language
        )

        if not translated_text:
            raise Exception("Translation failed: empty result")

        # Update translation with content
        translation.content = translated_text
        translation.status = "completed"

        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='translation',
            resource_id=translation.id,
            action='create'
        )

        db.session.commit()

        return jsonify(translation.to_dict()), 201

    except Exception as e:
        # Update status to failed
        translation.status = "failed"
        db.session.commit()

        logger.error(f"Translation error: {str(e)}", exc_info=True)

        return jsonify({
            'message': f'Translation failed: {str(e)}',
            'error_type': 'TRANSLATION_ERROR'
        }), 500


@ai_translation_bp.route('/ai/medical-glossary/<string:source_lang>/<string:target_lang>', methods=['GET'])
@token_required
def get_medical_glossary(source_lang, target_lang):
    """Get a medical terminology glossary for the specified language pair"""
    try:
        # This would typically come from a database, but for this example
        # we'll return a small sample of common medical terms

        # Only support a few language pairs for this example
        if source_lang == 'en' and target_lang == 'es':
            glossary = {
                "anesthesia": "anestesia",
                "biopsy": "biopsia",
                "cardiologist": "cardiólogo",
                "diagnosis": "diagnóstico",
                "electrocardiogram": "electrocardiograma",
                "fever": "fiebre",
                "glucose": "glucosa",
                "hypertension": "hipertensión",
                "infection": "infección",
                "jaundice": "ictericia"
            }
            return jsonify(glossary)

        elif source_lang == 'en' and target_lang == 'fr':
            glossary = {
                "anesthesia": "anesthésie",
                "biopsy": "biopsie",
                "cardiologist": "cardiologue",
                "diagnosis": "diagnostic",
                "electrocardiogram": "électrocardiogramme",
                "fever": "fièvre",
                "glucose": "glucose",
                "hypertension": "hypertension",
                "infection": "infection",
                "jaundice": "jaunisse"
            }
            return jsonify(glossary)

        else:
            return jsonify({
                'message': f'Medical glossary not available for language pair: {source_lang} to {target_lang}',
                'error_type': 'UNSUPPORTED_LANGUAGE_PAIR'
            }), 404

    except Exception as e:
        current_app.logger.error(f"Error retrieving medical glossary: {str(e)}", exc_info=True)
        return jsonify({
            'message': 'Failed to retrieve medical glossary',
            'error_type': 'GLOSSARY_ERROR'
        }), 500


@ai_translation_bp.route('/ai/translations/<int:translation_id>/quality-check', methods=['GET'])
@token_required
def check_translation_quality(translation_id):
    """Check the quality of a translation using AI"""
    # Get the translation
    translation = (
        Translation.query
        .join(Transcription)
        .filter(
            Translation.id == translation_id,
            Transcription.user_id == g.current_user.id
        )
        .first()
    )

    if not translation:
        return jsonify({'message': 'Translation not found'}), 404

    # Check if translation has content
    if not translation.content or not translation.content.strip():
        return jsonify({
            'message': 'Translation has no content to check',
            'error_type': 'EMPTY_CONTENT'
        }), 400

    try:
        # Get the transcription
        transcription = Transcription.query.get(translation.transcription_id)

        # Check if the AI service is available
        try:
            from ..services.ai_service import enhanced_translation
        except ImportError:
            return jsonify({
                'message': 'AI quality check service not available',
                'error_type': 'SERVICE_UNAVAILABLE'
            }), 503

        # For this example, we'll simulate a quality check with some metrics
        # In a real implementation, you would use AI to analyze the translation

        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='translation',
            resource_id=translation_id,
            action='quality-check'
        )

        # Simple quality metrics (would be AI-generated in production)
        quality_metrics = {
            "fluency_score": 0.85,
            "accuracy_score": 0.92,
            "terminology_score": 0.88,
            "overall_quality": "good",
            "suggestions": [
                "Consider reviewing medical terminology for more precise translations",
                "Check formatting of numbered lists to ensure consistency"
            ]
        }

        return jsonify({
            'translation_id': translation_id,
            'quality_check': quality_metrics
        })

    except Exception as e:
        current_app.logger.error(f"Error checking translation quality: {str(e)}", exc_info=True)
        return jsonify({
            'message': f'Quality check failed: {str(e)}',
            'error_type': 'QUALITY_CHECK_ERROR'
        }), 500