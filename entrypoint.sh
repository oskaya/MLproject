#!/bin/bash
# Guard Vision V2 - Web Application Container Startup Script

set -e

echo "🛡️ Starting Guard Vision V2 Web Application..."
echo "📋 Environment: ${FLASK_ENV:-development}"
echo "🌐 Host: ${FLASK_HOST:-0.0.0.0}"
echo "🔌 Port: ${FLASK_PORT:-5000}"
echo "🤖 ML API: ${ML_API_URL:-http://localhost:8000/predict}"
echo "📷 Camera: External script (camera_app.py)"

# Wait for ML API to be ready
echo "⏳ Waiting for ML API to be ready..."
while ! curl -s "${ML_API_URL}" >/dev/null 2>&1; do
    echo "   Waiting for ML API at ${ML_API_URL}..."
    sleep 5
done
echo "✅ ML API is responding!"

# Validate required environment variables
if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ]; then
    echo "❌ ERROR: GitHub OAuth credentials not provided!"
    echo "   Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "development_secret_key_change_in_production" ]; then
    echo "⚠️  WARNING: Using development SECRET_KEY in production!"
    echo "   Please set a secure SECRET_KEY environment variable"
fi

# Create required directories
mkdir -p /app/logs /app/data

# Set permissions
chmod 755 /app/logs /app/data

echo "ℹ️  Note: Start camera_app.py separately to enable camera functionality"
echo "🚀 Starting Guard Vision V2 Web Application..."

# Start the application
exec python main.py