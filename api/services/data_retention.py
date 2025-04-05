"""
Data retention service for implementing HIPAA data lifecycle policies
"""
import os
import logging
from datetime import datetime, timedelta
from flask import current_app
from ..db import db
from ..models.transcript import Transcription
from ..models.translation import Translation
from ..models.audit_log import AuditLog
from ..services.file_service import delete_file

logger = logging.getLogger(__name__)


def get_retention_period(data_type):
    """
    Get the retention period for a specific data type

    Args:
        data_type: Type of data (e.g., 'transcription', 'translation', 'audit')

    Returns:
        int: Retention period in days
    """
    # Default retention periods (in days)
    default_periods = {
        'transcription': 365,  # 1 year
        'translation': 365,  # 1 year
        'audit': 2190,  # 6 years (HIPAA requires minimum of 6 years)
        'default': 90  # 90 days
    }

    # Get from environment or config
    env_var = f"{data_type.upper()}_RETENTION_DAYS"
    config_key = f"retention_periods.{data_type}"

    # Try environment variable
    if env_var in os.environ:
        try:
            return int(os.environ[env_var])
        except (ValueError, TypeError):
            pass

    # Try config
    try:
        return current_app.config.get(config_key, default_periods.get(data_type, default_periods['default']))
    except (AttributeError, KeyError):
        return default_periods.get(data_type, default_periods['default'])


def cleanup_expired_data():
    """
    Delete data that has exceeded its retention period

    Returns:
        dict: Summary of cleanup operation
    """
    logger.info("Starting data retention cleanup task")

    summary = {
        'transcriptions_deleted': 0,
        'translations_deleted': 0,
        'files_deleted': 0,
        'errors': []
    }

    try:
        # Get retention periods
        transcription_days = get_retention_period('transcription')
        translation_days = get_retention_period('translation')

        # Calculate cutoff dates
        transcription_cutoff = datetime.utcnow() - timedelta(days=transcription_days)
        translation_cutoff = datetime.utcnow() - timedelta(days=translation_days)

        logger.info(
            f"Retention periods: Transcriptions={transcription_days} days, Translations={translation_days} days")
        logger.info(
            f"Cutoff dates: Transcriptions={transcription_cutoff.isoformat()}, Translations={translation_cutoff.isoformat()}")

        # Find expired transcriptions
        expired_transcriptions = Transcription.query.filter(
            Transcription.created_at < transcription_cutoff
        ).all()

        # Process expired transcriptions
        for transcription in expired_transcriptions:
            try:
                # Delete associated file if it exists
                if transcription.file_path and os.path.exists(transcription.file_path):
                    if delete_file(transcription.file_path):
                        summary['files_deleted'] += 1

                # Log the deletion for audit
                AuditLog.log_phi_access(
                    user_id=0,  # System user
                    resource_type='transcription',
                    resource_id=transcription.id,
                    action='delete',
                    description=f"Deleted due to retention policy ({transcription_days} days)"
                )

                # Delete from database
                db.session.delete(transcription)
                summary['transcriptions_deleted'] += 1

            except Exception as e:
                error_msg = f"Error deleting transcription {transcription.id}: {str(e)}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)

        # Find expired translations not associated with retained transcriptions
        expired_translations = Translation.query.filter(
            Translation.created_at < translation_cutoff,
            ~Translation.transcription_id.in_([t.id for t in expired_transcriptions])
        ).all()

        # Process expired translations
        for translation in expired_translations:
            try:
                # Log the deletion for audit
                AuditLog.log_phi_access(
                    user_id=0,  # System user
                    resource_type='translation',
                    resource_id=translation.id,
                    action='delete',
                    description=f"Deleted due to retention policy ({translation_days} days)"
                )

                # Delete from database
                db.session.delete(translation)
                summary['translations_deleted'] += 1

            except Exception as e:
                error_msg = f"Error deleting translation {translation.id}: {str(e)}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)

        # Commit all changes
        db.session.commit()

    except Exception as e:
        logger.error(f"Error in cleanup_expired_data: {str(e)}", exc_info=True)
        db.session.rollback()
        summary['errors'].append(f"Global error: {str(e)}")

    logger.info(f"Data retention cleanup complete: {summary}")
    return summary


def register_data_retention_commands(app):
    """
    Register CLI commands for data retention management

    Args:
        app: Flask application
    """

    @app.cli.command("cleanup-expired-data")
    def cleanup_command():
        """Delete data that has exceeded its retention period"""
        result = cleanup_expired_data()
        print(
            f"Cleaned up {result['transcriptions_deleted']} transcriptions, {result['translations_deleted']} translations, and {result['files_deleted']} files")
        if result['errors']:
            print(f"Errors occurred: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")