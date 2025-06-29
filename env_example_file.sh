# SmartProposal Engine Environment Variables
# Copy this file to .env and update with your actual values

# ===================================
# API Keys and Authentication
# ===================================

# Google Gemini API Key (Required)
# Get your API key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Alternative: Use internal API key file (set in app_config.ini)
# If using internal key file, leave GOOGLE_API_KEY empty

# ===================================
# Application Settings
# ===================================

# Environment (development, staging, production)
ENVIRONMENT=development

# Debug mode (true/false)
DEBUG=false

# Application port (default: 8501 for Streamlit)
PORT=8501

# ===================================
# File Storage Settings
# ===================================

# Temporary files directory (default: temp/)
TEMP_DIR=temp/

# Output files directory (default: output/)
OUTPUT_DIR=output/

# Maximum file size in MB (default: 200)
MAX_FILE_SIZE_MB=200

# Auto cleanup temporary files (true/false)
AUTO_CLEANUP_TEMP_FILES=true

# ===================================
# Model Configuration
# ===================================

# Default models for different tasks
# Available models: gemini-2.5-pro, gemini-2.5-flash, gemini-1.5-pro, gemini-1.5-flash
DEFAULT_TRANSCRIPTION_MODEL=models/gemini-2.5-flash
DEFAULT_ANALYSIS_MODEL=models/gemini-2.5-pro
DEFAULT_PROPOSAL_MODEL=models/gemini-2.5-pro

# Model temperature settings (0.0 - 1.0)
MODEL_TEMPERATURE=0.7
MODEL_TOP_P=0.95

# Maximum tokens per request
MAX_OUTPUT_TOKENS=16384

# ===================================
# Feature Flags
# ===================================

# Enable/disable features
ENABLE_TEXT_OPTIMIZATION=true
ENABLE_SPEAKER_DIARIZATION=true
ENABLE_CUSTOM_PROMPTS=true
ENABLE_BATCH_PROCESSING=true
ENABLE_CAPABILITY_DOCS=true

# ===================================
# Performance Settings
# ===================================

# Request timeout in seconds
REQUEST_TIMEOUT=900

# Maximum concurrent requests
MAX_CONCURRENT_REQUESTS=3

# Retry configuration
MAX_RETRIES=3
RETRY_DELAY_SECONDS=2

# Cache settings
ENABLE_CACHE=true
CACHE_TTL_HOURS=24

# ===================================
# Security Settings
# ===================================

# Session secret key (generate a random string)
SESSION_SECRET_KEY=your_secret_key_here_change_in_production

# Enable HTTPS redirect (for production)
FORCE_HTTPS=false

# Allowed file extensions (comma-separated)
ALLOWED_AUDIO_EXTENSIONS=.m4a,.mp3,.wav,.aac,.ogg,.flac,.mp4
ALLOWED_DOCUMENT_EXTENSIONS=.docx,.pdf,.txt,.doc,.rtf,.odt

# ===================================
# Logging Configuration
# ===================================

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file path
LOG_FILE=logs/app.log

# Enable console logging
CONSOLE_LOGGING=true

# ===================================
# External Services (Future Extensions)
# ===================================

# Database URL (for future persistence features)
# DATABASE_URL=postgresql://user:password@localhost:5432/smartproposal

# Redis URL (for future caching/queuing)
# REDIS_URL=redis://localhost:6379

# Email settings (for future notifications)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your_email@gmail.com
# SMTP_PASSWORD=your_app_password

# Cloud storage (for future cloud integration)
# AWS_ACCESS_KEY_ID=your_aws_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret
# AWS_S3_BUCKET=smartproposal-uploads

# ===================================
# Analytics and Monitoring (Optional)
# ===================================

# Google Analytics
# GA_TRACKING_ID=UA-XXXXXXXXX-X

# Sentry error tracking
# SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id

# ===================================
# Development Settings
# ===================================

# Enable hot reload (for development)
HOT_RELOAD=true

# Show detailed error messages (disable in production)
SHOW_ERROR_DETAILS=true

# Enable profiling (for performance debugging)
ENABLE_PROFILING=false

# ===================================
# Notes
# ===================================
# 1. Never commit the actual .env file to version control
# 2. Keep your API keys secure and rotate them regularly
# 3. Use different API keys for different environments
# 4. Set appropriate values for production deployment
# 5. Some settings can also be configured in app_config.ini
