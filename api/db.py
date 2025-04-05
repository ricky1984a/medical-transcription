"""
Database connection setup
"""
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base, clear_mappers

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy without a model class
db = SQLAlchemy()

def reset_sqlalchemy():
    """Reset SQLAlchemy mappers to avoid conflicts during reinitialization"""
    try:
        logger.info("Clearing SQLAlchemy mappers")
        clear_mappers()
        logger.info("SQLAlchemy mappers cleared")
    except Exception as e:
        logger.error(f"Error clearing SQLAlchemy mappers: {e}")