#!/bin/bash

echo "Starting build process for medical-transcription API"

if [ -z "$VERCEL" ]; then
  echo "Running in local mode - using virtual environment"
  if [ ! -d "venv" ]; then
    python3.9 -m venv venv_py39
  fi
  source venv_py39/bin/activate
  pip install -r requirements.txt
  echo "🛠 Running database initialization script..."
  python3 api/create_postgres_tables.py
else
  echo "Running in Vercel deployment mode"
  
  # Create necessary directories
  mkdir -p uploads
  mkdir -p tts_output
  mkdir -p tmp
  
  echo "Created required directories"
  
  # Print Python version
  python --version
  
  # For Vercel, we'll use the default pip install from vercel.json
  echo "Dependencies will be installed by Vercel's build process"
  
  # Set up .env file for Vercel if not exists
  if [ ! -f ".env" ]; then
    echo "Creating minimal .env file for Vercel"
    cat > .env << EOL
FLASK_APP=run.py
FLASK_ENV=production
FLASK_DEBUG=0
PORT=2000
EOL
  fi
  
  echo "✅ Build script completed"
fi

# Exit with success
exit 0