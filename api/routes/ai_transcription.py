"""
Enhanced transcription routes with AI integration
"""
import os
from flask import Blueprint, request, jsonify, g, current_app
from ..db import db
from ..models.transcript import Transcription
from ..security import token_required
from ..services.security_service import log_data_access, generate_secure_filename
from ..utils.rate_limiter import get_rate_limit

# Create blueprint for AI transcription routes
ai_transcription_bp = Blueprint('ai_transcription', __name__, url_prefix='/api')


# Import services with fallbacks
def get_transcription_service():
    """Get the best available transcription service"""
    try:
        # Try Google Speech API first
        from ..services.google_speech_recognition import transcribe_audio_google
        return transcribe_audio_google
    except ImportError:
        # Fall back to standard speech recognition
        try:
            from ..services.improved_speech_recognition import transcribe_audio
            return transcribe_audio
        except ImportError:
            from ..services.speech_recognition import transcribe_audio
            return transcribe_audio


def get_ai_services():
    """Get AI services if available"""
    try:
        from ..services.ai_service import (
            medical_coding_assistance,
            summarize_transcription
        )
        return medical_coding_assistance, summarize_transcription
    except ImportError:
        return None, None


# Add the basic transcriptions route
@ai_transcription_bp.route('/transcriptions', methods=['GET', 'POST'])
@token_required
def transcriptions():
    """Get all transcriptions or create a new one"""
    if request.method == 'GET':
        # Get all transcriptions for the current user
        transcriptions = (
            Transcription.query
            .filter_by(user_id=g.current_user.id)
            .order_by(Transcription.created_at.desc())
            .all()
        )

        # Convert to dictionary representation
        result = [t.to_dict() for t in transcriptions]

        return jsonify(result)

    elif request.method == 'POST':
        # Create a new transcription
        data = request.get_json()

        if not data:
            return jsonify({
                'message': 'No data provided',
                'error_type': 'MISSING_DATA'
            }), 400

        # Extract data with defaults
        title = data.get('title', f'Transcription {Transcription.query.count() + 1}')
        language = data.get('language', 'en')  # Default to English

        # Create new transcription
        transcription = Transcription(
            title=title,
            language=language,
            user_id=g.current_user.id,
            status='pending',
            content=''  # Empty content initially
        )

        # Save to database
        db.session.add(transcription)
        db.session.commit()

        # Log creation
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription.id,
            action='create'
        )

        return jsonify(transcription.to_dict()), 201


@ai_transcription_bp.route('/transcriptions/<int:transcription_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def transcription(transcription_id):
    """Get, update or delete a specific transcription"""
    # Get the transcription
    transcription = (
        Transcription.query
        .filter_by(id=transcription_id, user_id=g.current_user.id)
        .first()
    )

    if not transcription:
        return jsonify({'message': 'Transcription not found'}), 404

    if request.method == 'GET':
        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='retrieve'
        )

        return jsonify(transcription.to_dict())

    elif request.method == 'PUT':
        # Update the transcription
        data = request.get_json()

        if not data:
            return jsonify({
                'message': 'No data provided',
                'error_type': 'MISSING_DATA'
            }), 400

        # Update fields if provided
        if 'title' in data:
            transcription.title = data['title']

        if 'content' in data:
            transcription.content = data['content']

        if 'status' in data:
            transcription.status = data['status']

        # Save changes
        db.session.commit()

        # Log update
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='update'
        )

        return jsonify(transcription.to_dict())

    elif request.method == 'DELETE':
        # Delete the transcription
        db.session.delete(transcription)
        db.session.commit()

        # Log deletion
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='delete'
        )

        return jsonify({'message': 'Transcription deleted successfully'})


@ai_transcription_bp.route('/ai/transcriptions/<int:transcription_id>/analysis', methods=['GET'])
@token_required
def analyze_transcription(transcription_id):
    """Analyze transcription with AI to extract medical codes and information"""
    # Get the transcription
    transcription = (
        Transcription.query
        .filter_by(id=transcription_id, user_id=g.current_user.id)
        .first()
    )

    if not transcription:
        return jsonify({'message': 'Transcription not found'}), 404

    # Check if transcription has content
    if not transcription.content or not transcription.content.strip():
        return jsonify({
            'message': 'Transcription has no content to analyze',
            'error_type': 'EMPTY_CONTENT'
        }), 400

    try:
        # Get AI coding assistance service
        medical_coding_assistance, _ = get_ai_services()

        if not medical_coding_assistance:
            return jsonify({
                'message': 'AI analysis service not available',
                'error_type': 'SERVICE_UNAVAILABLE'
            }), 503

        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='analyze'
        )

        # Analyze the transcription
        result = medical_coding_assistance(transcription.content)

        # Return the analysis results
        return jsonify({
            'transcription_id': transcription_id,
            'analysis': result
        })

    except Exception as e:
        current_app.logger.error(f"Error analyzing transcription: {str(e)}", exc_info=True)
        return jsonify({
            'message': f'AI analysis failed: {str(e)}',
            'error_type': 'ANALYSIS_ERROR'
        }), 500


@ai_transcription_bp.route('/ai/transcriptions/<int:transcription_id>/summarize', methods=['GET'])
@token_required
def summarize_transcription_route(transcription_id):
    """Generate a concise summary of the transcription using AI"""
    # Get the transcription
    transcription = (
        Transcription.query
        .filter_by(id=transcription_id, user_id=g.current_user.id)
        .first()
    )

    if not transcription:
        return jsonify({'message': 'Transcription not found'}), 404

    # Check if transcription has content
    if not transcription.content or not transcription.content.strip():
        return jsonify({
            'message': 'Transcription has no content to summarize',
            'error_type': 'EMPTY_CONTENT'
        }), 400

    try:
        # Get AI summarization service
        _, summarize_transcription = get_ai_services()

        if not summarize_transcription:
            return jsonify({
                'message': 'AI summarization service not available',
                'error_type': 'SERVICE_UNAVAILABLE'
            }), 503

        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='summarize'
        )

        # Summarize the transcription
        summary = summarize_transcription(transcription.content)

        # Return the summary
        return jsonify({
            'transcription_id': transcription_id,
            'summary': summary
        })

    except Exception as e:
        current_app.logger.error(f"Error summarizing transcription: {str(e)}", exc_info=True)
        return jsonify({
            'message': f'AI summarization failed: {str(e)}',
            'error_type': 'SUMMARIZATION_ERROR'
        }), 500


@ai_transcription_bp.route('/ai/transcriptions/<int:transcription_id>/upload', methods=['POST'])
@token_required
def enhanced_upload_and_transcribe(transcription_id):
    """Upload audio file and transcribe it using the best available service"""
    # Apply rate limiting
    limiter = current_app.limiter
    limiter.limit(get_rate_limit("api.transcriptions"))(lambda: None)()

    # Get logger
    logger = current_app.logger

    # Check if transcription exists and belongs to user
    transcription = (
        Transcription.query
        .filter_by(id=transcription_id, user_id=g.current_user.id)
        .first()
    )

    if not transcription:
        return jsonify({'message': 'Transcription not found'}), 404

    # Check if file was uploaded
    if 'audio_file' not in request.files:
        return jsonify({
            'message': 'No audio file provided',
            'error_type': 'MISSING_FILE'
        }), 400

    audio_file = request.files['audio_file']

    if audio_file.filename == '':
        return jsonify({
            'message': 'No selected file',
            'error_type': 'EMPTY_FILENAME'
        }), 400

    # Log file information for debugging
    logger.info(f"Received audio file: {audio_file.filename}, mimetype: {audio_file.mimetype}")

    # Update status to processing
    transcription.status = "processing"
    db.session.commit()

    try:
        # Generate secure filename
        secure_filename = generate_secure_filename(
            original_filename=audio_file.filename,
            file_type='audio'
        )

        # Get upload directory
        upload_dir = os.path.join(
            current_app.root_path,
            '..',
            'uploads'
        )

        # Ensure directory exists
        os.makedirs(upload_dir, exist_ok=True)

        # Save file path
        file_path = os.path.join(upload_dir, secure_filename)

        # Save file
        audio_file.save(file_path)

        # Get the best available transcription service
        transcribe_audio = get_transcription_service()

        # Transcribe the audio
        logger.info(f"Starting transcription for file: {file_path}")

        # Use language from transcription
        language_code = transcription.language

        # Transcribe with the selected service
        transcribed_text = transcribe_audio(file_path, language_code)

        # Check if transcription was successful
        if not transcribed_text:
            # Update transcription with empty content but specific status
            transcription.content = ""
            transcription.status = "no_speech_detected"
            transcription.file_path = file_path
            db.session.commit()

            logger.warning(f"No speech detected in audio file: {file_path}")

            return jsonify({
                'message': 'No speech was detected in the uploaded audio file. Please check that the file contains clear speech audio.',
                'error_type': 'NO_SPEECH_DETECTED',
                'transcription': transcription.to_dict()
            }), 422  # Unprocessable Entity status code

        # Update transcription with content
        transcription.content = transcribed_text
        transcription.status = "completed"
        transcription.file_path = file_path

        # Log access
        log_data_access(
            user_id=g.current_user.id,
            resource_type='transcription',
            resource_id=transcription_id,
            action='transcribe'
        )

        db.session.commit()
        logger.info(f"Transcription successful: {len(transcribed_text)} characters")

        # Check if user wants AI analysis
        if request.args.get('analyze', 'false').lower() == 'true':
            # Get AI coding assistance service
            medical_coding_assistance, _ = get_ai_services()

            if medical_coding_assistance:
                try:
                    # Analyze the transcription
                    analysis = medical_coding_assistance(transcribed_text)

                    # Return transcription with analysis
                    return jsonify({
                        'transcription': transcription.to_dict(),
                        'analysis': analysis
                    })
                except Exception as e:
                    logger.error(f"AI analysis failed, but transcription successful: {str(e)}")
                    # Continue with just the transcription

        # Return just the transcription if analysis not requested or failed
        return jsonify(transcription.to_dict())

    except Exception as e:
        # Update status to failed
        transcription.status = "failed"
        db.session.commit()

        logger.error(f"Transcription error: {str(e)}", exc_info=True)

        return jsonify({
            'message': f'Transcription failed: {str(e)}',
            'error_type': 'TRANSCRIPTION_ERROR'
        }), 500