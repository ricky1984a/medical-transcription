"""
Logging configuration for the Medical Transcription App
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from .config import config


def setup_logging(app):
    """
    Configure logging for the application

    Args:
        app: Flask application instance

    Returns:
        Logger: Configured logger instance
    """
    # Get logging configuration from config
    log_config = config.get_logging_config()
    log_level_name = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    log_file = log_config.get('file', '/tmp/app.log')
    log_max_size = log_config.get('max_size', 10240)  # 10 MB
    log_backup_count = log_config.get('backup_count', 10)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Convert log level string to logging constant
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(level=log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Create file handler for logging to a file
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Create console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Get the app logger and configure it
    app_logger = logging.getLogger('app')
    app_logger.setLevel(log_level)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)

    # Configure Flask app logger
    app.logger.setLevel(log_level)
    # Remove default handlers and add our custom handlers
    app.logger.handlers = []
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Configure SQLAlchemy logger
    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.setLevel(logging.WARNING)  # Set to INFO to log all SQL queries
    sql_logger.addHandler(file_handler)

    # Log application startup
    app.logger.info(f"Medical Transcription App starting up - Logging to {log_file}")

    return app_logger