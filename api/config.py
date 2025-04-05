"""
Updated configuration loader to use pg8000 dialect by default for Vercel compatibility
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager class for the application
    Loads settings from config.yaml and environment variables
    Environment variables take precedence over config file settings
    """

    def __init__(self, config_path: Optional[str] = None):
        # Default config path
        if config_path is None:
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(base_dir, 'config', 'config.yaml')

        # Load configuration from file
        self.config = self._load_config(config_path)

        # Get environment (development, testing, production)
        self.env = os.environ.get('FLASK_ENV', 'development')

        # Override with environment variables
        self._override_from_env()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Args:
            config_path: Path to the config.yaml file

        Returns:
            Dict: Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            return {}

    def _override_from_env(self):
        """Override configuration values from environment variables"""
        # Database URL
        if db_url := os.environ.get('DATABASE_URL'):
            if 'database' not in self.config:
                self.config['database'] = {}
            if self.env not in self.config['database']:
                self.config['database'][self.env] = {}
            self.config['database'][self.env]['url'] = db_url

        # JWT Secret Key
        if jwt_key := os.environ.get('SECRET_KEY'):
            if 'auth' not in self.config:
                self.config['auth'] = {}
            self.config['auth']['jwt_secret_key'] = jwt_key

        # Flask Secret Key
        if flask_key := os.environ.get('FLASK_SECRET_KEY'):
            if 'security' not in self.config:
                self.config['security'] = {}
            self.config['security']['secret_key'] = flask_key

        # Port
        if port := os.environ.get('PORT'):
            if 'environment' not in self.config:
                self.config['environment'] = {}
            if self.env not in self.config['environment']:
                self.config['environment'][self.env] = {}
            self.config['environment'][self.env]['port'] = int(port)

        # Engine options
        if 'database' not in self.config:
            self.config['database'] = {}
        if self.env not in self.config['database']:
            self.config['database'][self.env] = {}
        if 'engine_options' not in self.config['database'][self.env]:
            self.config['database'][self.env]['engine_options'] = {}

        # Add engine options from environment
        engine_options = self.config['database'][self.env]['engine_options']
        if pool_size := os.environ.get('SQLALCHEMY_POOL_SIZE'):
            engine_options['pool_size'] = int(pool_size)
        if max_overflow := os.environ.get('SQLALCHEMY_MAX_OVERFLOW'):
            engine_options['max_overflow'] = int(max_overflow)
        if pool_recycle := os.environ.get('SQLALCHEMY_POOL_RECYCLE'):
            engine_options['pool_recycle'] = int(pool_recycle)

    def get_secret(self, secret_name, default=None):
        """Get a secret from the environment or secrets manager"""
        # In production, you might use a secrets manager
        if self.env == "production":
            # This is a placeholder for a production secrets manager
            # Example for AWS Secrets Manager implementation would go here
            pass

        # Fallback to environment variables
        return os.environ.get(secret_name, default)

    def get_db_url(self) -> str:
        """Get the database URL with proper SSL config"""
        # First try to get from environment directly
        db_url = self.get_secret("DATABASE_URL")

        # Log the original URL for debugging
        logger.info(f"Original DATABASE_URL: {db_url}")

        # Clean up the URL if needed - make sure we don't try to use string operations on a non-string
        if db_url and isinstance(db_url, str):
            # Remove all SSL parameters and Supabase specific parameters
            if "?" in db_url:
                # Remove all query parameters completely
                db_url = db_url.split("?")[0]

            if "&supa=base-pooler.x" in db_url:
                db_url = db_url.replace("&supa=base-pooler.x", "")

            logger.info(f"Cleaned DATABASE_URL: {db_url}")

        # If not in environment, try config file
        if not db_url:
            try:
                db_url = self.config['database'][self.env]['url']
            except (KeyError, TypeError):
                return "sqlite:///app.db"  # Default fallback

        # For PostgreSQL URLs, convert for SQLAlchemy with pg8000 driver
        if isinstance(db_url, str):
            if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
                # Replace postgres:// with postgresql+pg8000:// for SQLAlchemy with pg8000 driver
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
                else:
                    db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

        return db_url

    def get_db_engine_options(self) -> Dict[str, Any]:
        """Get optimized database engine options"""
        # Default options
        base_options = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }

        # Production needs higher capacity
        if self.env == "production":
            base_options.update({
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
            })

        try:
            # Get options from config file
            config_options = self.config['database'][self.env].get('engine_options', {})
            base_options.update(config_options)
        except (KeyError, TypeError):
            pass

        # For pg8000 connections, don't add any SSL parameters
        db_url = self.get_db_url()
        if db_url and "postgresql+pg8000" in db_url:
            # Don't add any connect_args for pg8000
            # Your successful test shows the connection works without them
            pass

        return base_options

    def get_jwt_secret_key(self) -> str:
        """Get the JWT secret key"""
        # Try to get from environment first
        secret_key = self.get_secret("SECRET_KEY")
        if secret_key:
            return secret_key

        # Fallback to config
        try:
            return self.config['auth']['jwt_secret_key']
        except (KeyError, TypeError):
            return "your-jwt-secret-key-change-this-in-production"

    def get_secret_key(self) -> str:
        """Get the Flask secret key"""
        # Try to get from environment first
        secret_key = self.get_secret("FLASK_SECRET_KEY")
        if secret_key:
            return secret_key

        # Fallback to config
        try:
            return self.config['security']['secret_key']
        except (KeyError, TypeError):
            return "your-secret-key-change-this-in-production"

    def get_port(self) -> int:
        """Get the port for the current environment"""
        # Try to get from environment first
        port = self.get_secret("PORT")
        if port:
            try:
                return int(port)
            except (ValueError, TypeError):
                pass

        # Fallback to config
        try:
            return self.config['environment'][self.env]['port']
        except (KeyError, TypeError):
            return 5000  # Default port

    def get_debug(self) -> bool:
        """Get debug mode for the current environment"""
        # Try to get from environment first
        debug = self.get_secret("FLASK_DEBUG")
        if debug is not None:
            return debug.lower() in ('true', '1', 't', 'y', 'yes')

        # Fallback to config
        try:
            return self.config['environment'][self.env]['debug']
        except (KeyError, TypeError):
            return self.env == 'development'  # Default debug mode

    def get_static_folder(self) -> str:
        """Get the static folder path"""
        try:
            return self.config['app']['static_folder']
        except (KeyError, TypeError):
            return '../frontend/dist'

    def get_static_url_path(self) -> str:
        """Get the static URL path"""
        try:
            return self.config['app']['static_url_path']
        except (KeyError, TypeError):
            return ''

    def get_upload_directory(self) -> str:
        """Get the upload directory path"""
        # Try to get from environment first
        upload_dir = self.get_secret("UPLOAD_DIRECTORY")
        if upload_dir:
            return upload_dir

        # Fallback to config
        try:
            return self.config['storage']['upload_directory']
        except (KeyError, TypeError):
            return 'uploads'

    def get_tts_output_directory(self) -> str:
        """Get the TTS output directory path"""
        try:
            return self.config['services']['tts']['output_directory']
        except (KeyError, TypeError):
            return 'tts_output'

    def get_allowed_audio_extensions(self) -> list:
        """Get the list of allowed audio file extensions"""
        try:
            return self.config['storage']['allowed_audio_extensions']
        except (KeyError, TypeError):
            return ['.wav', '.mp3', '.m4a', '.flac']

    def get_max_upload_size(self) -> int:
        """Get the maximum upload file size in bytes"""
        # Try to get from environment first
        max_size = self.get_secret("MAX_UPLOAD_SIZE")
        if max_size:
            try:
                return int(max_size)
            except (ValueError, TypeError):
                pass

        # Fallback to config
        try:
            return self.config['storage']['max_upload_size']
        except (KeyError, TypeError):
            return 50000000  # 50MB default

    def get_speech_recognition_language(self) -> str:
        """Get the default speech recognition language"""
        try:
            return self.config['services']['speech_recognition']['default_language']
        except (KeyError, TypeError):
            return 'en-US'

    def get_default_translation_source(self) -> str:
        """Get the default translation source language"""
        try:
            return self.config['services']['translation']['default_source_language']
        except (KeyError, TypeError):
            return 'en'

    def get_default_translation_target(self) -> str:
        """Get the default translation target language"""
        try:
            return self.config['services']['translation']['default_target_language']
        except (KeyError, TypeError):
            return 'es'

    def get_logging_config(self) -> Dict[str, Any]:
        """Get the logging configuration"""
        try:
            return self.config['logging']
        except (KeyError, TypeError):
            return {
                'level': 'INFO',
                'format': '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
                'file': 'logs/app.log',
                'max_size': 10240,
                'backup_count': 10
            }

    def get_swagger_config(self) -> Dict[str, Any]:
        """Get the Swagger documentation configuration"""
        try:
            return self.config['swagger']
        except (KeyError, TypeError):
            return {
                'title': 'Medical Transcription API',
                'version': '1.0.0',
                'description': 'API for medical audio transcription and translation',
                'openapi_version': '3.0.2',
                'contact_email': 'contact@example.com'
            }

    def get_api_base_url(self) -> str:
        """Get the API base URL"""
        try:
            return self.config['api']['base_url']
        except (KeyError, TypeError):
            return '/api'

    def get_jwt_algorithm(self) -> str:
        """Get the JWT algorithm"""
        try:
            return self.config['auth']['algorithm']
        except (KeyError, TypeError):
            return 'HS256'

    def get_jwt_expire_minutes(self) -> int:
        """Get the JWT expiration time in minutes"""
        # Try to get from environment first
        expire_minutes = self.get_secret("JWT_EXPIRE_MINUTES")
        if expire_minutes:
            try:
                return int(expire_minutes)
            except (ValueError, TypeError):
                pass

        # Fallback to config
        try:
            return self.config['auth']['access_token_expire_minutes']
        except (KeyError, TypeError):
            return 30

    def get_jwt_refresh_expire_days(self) -> int:
        """Get the JWT refresh token expiration time in days"""
        # Try to get from environment first
        expire_days = self.get_secret("JWT_REFRESH_EXPIRE_DAYS")
        if expire_days:
            try:
                return int(expire_days)
            except (ValueError, TypeError):
                pass

        # Fallback to config
        try:
            return self.config['auth']['refresh_token_expire_days']
        except (KeyError, TypeError):
            return 7  # Default 7 days

    def get_redis_url(self) -> str:
        """Get the Redis URL"""
        # Try to get from environment first
        redis_url = self.get_secret("REDIS_URL")
        if redis_url:
            return redis_url

        # Fallback to config
        try:
            return self.config['services']['redis']['url']
        except (KeyError, TypeError):
            return 'redis://localhost:6379/0'


# Create a global config instance
config = Config()