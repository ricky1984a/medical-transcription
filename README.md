# medical-transcription

A Flask application for transcribing medical audio recordings and translating them to different languages.

## Features

- Audio transcription service
- Text translation 
- User authentication with JWT
- API rate limiting
- Interactive API documentation (Swagger & ReDoc)

## Setup Instructions

### Prerequisites

- Python 3.9
- PostgreSQL (for production, SQLite for development)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ricky1984a/medical-transcription.git
   cd medical-transcription
   ```

2. Create and activate a virtual environment:
   ```
python -m venv venv_py39
source venv_py39/bin/activate  # On Windows: venv_py39\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create configuration file:
   Create a `config` directory in the project root and add a `config.yaml` file:
   ```
   mkdir -p config
   touch config/config.yaml
   ```

5. Add configuration to `config.yaml` (example):
   ```yaml
   database:
     development:
       url: "sqlite:///app.db"
       engine_options:
         pool_recycle: 300
         pool_pre_ping: true
     production:
       url: "postgresql://username:password@localhost/medical_transcription_db"
       engine_options:
         pool_recycle: 3600
         pool_pre_ping: true
   
   auth:
     jwt_secret_key: "your-secure-jwt-secret-key"
     algorithm: "HS256"
     access_token_expire_minutes: 30
   
   security:
     secret_key: "your-flask-secret-key-for-session-management"
   
   environment:
     development:
       port: 5000
       debug: true
     production:
       port: 8000
       debug: false
   
   storage:
     upload_directory: "uploads"
     allowed_audio_extensions: [".wav", ".mp3", ".m4a", ".flac"]
     max_upload_size: 50000000  # 50MB
   
   services:
     speech_recognition:
       default_language: "en-US"
     
     translation:
       default_source_language: "en"
       default_target_language: "es"
     
     tts:
       output_directory: "tts_output"
   
   logging:
     level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
     format: "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
     file: "logs/app.log"
     max_size: 10240  # 10MB
     backup_count: 10
   
   app:
     static_folder: "../frontend/dist"
     static_url_path: ""

   rate_limits:
     auth.token: "5 per minute"
     api.transcriptions: "10 per minute"
     api.default: "100 per day"
   ```

### Database Setup

For SQLite (development):
- The database will be created automatically when you run the app

For PostgreSQL (production):
1. Create the database:
   ```
   createdb medical_transcription_db
   ```

2. Run the database setup script:
   ```
   python create_postgres_tables.py
   ```

## Running the Application

### Development Mode

```
python run.py
```

The application will be available at http://localhost:5000

### Production Mode

Set the environment to production:

```
export FLASK_ENV=production
python run.py
```

## API Documentation

Once the application is running:

- Swagger UI: http://localhost:5000/api/docs
- ReDoc: http://localhost:5000/api/redoc
- OpenAPI Spec: http://localhost:5000/api/openapi.json

## Project Structure

```
medical-transcription-app/
+-- backend/
¦   +-- api/
¦   ¦   +-- __init__.py          # App factory and initialization
¦   ¦   +-- config.py            # Configuration loader
¦   ¦   +-- db.py                # Database setup
¦   ¦   +-- logging_setup.py     # Logging configuration
¦   ¦   +-- main.py              # Main application entry
¦   ¦   +-- security.py          # JWT authentication
¦   ¦   +-- swagger.py           # API documentation
¦   ¦   +-- utils/               # Utility functions
¦   ¦   ¦   +-- rate_limiter.py  # Rate limiting utilities
¦   ¦   +-- models/              # SQLAlchemy models
¦   ¦   ¦   +-- user.py          # User model
¦   ¦   ¦   +-- transcript.py    # Transcription model
¦   ¦   ¦   +-- translation.py   # Translation model
¦   ¦   +-- routes/              # API routes
¦   ¦   ¦   +-- __init__.py      # Routes package initialization
¦   ¦   ¦   +-- auth.py          # Authentication routes
¦   ¦   ¦   +-- transcription.py # Transcription routes
¦   ¦   ¦   +-- translation.py   # Translation routes
¦   ¦   +-- services/            # Business logic services
¦   ¦       +-- speech_recognition.py  # Audio transcription
¦   ¦       +-- translation.py         # Text translation
¦   ¦       +-- tts.py                 # Text-to-speech
¦   +-- config/                 # Configuration files
¦   ¦   +-- config.yaml         # App configuration 
¦   +-- logs/                   # Log files
¦   +-- uploads/                # Uploaded audio files
¦   +-- tts_output/             # Generated audio files
¦   +-- create_postgres_tables.py  # Database setup script
¦   +-- requirements.txt        # Python dependencies
¦   +-- run.py                  # App entry poin
+-- README.md                   # Project documentation
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
