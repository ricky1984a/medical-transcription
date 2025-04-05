FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create directories for uploads, logs and TTS output
RUN mkdir -p uploads tts_output logs /tmp

# Expose the application port
EXPOSE 2000

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV PORT=2000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:2000", "--workers", "2", "--timeout", "60", "run:app"]