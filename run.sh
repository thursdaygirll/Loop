#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# Create venv if it doesn't exist
if [ ! -f "$PYTHON" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install/update dependencies
echo "Installing dependencies..."
"$PIP" install -r "$PROJECT_DIR/requirements.txt" -q

# Load .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Check for Firebase credentials
if [ -z "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    DEFAULT_CREDS="$PROJECT_DIR/loopapp-13b10-firebase-adminsdk-fbsvc-879b0aa064.json"
    if [ ! -f "$DEFAULT_CREDS" ]; then
        echo ""
        echo "ERROR: Firebase credentials not found."
        echo "Place your service account JSON at:"
        echo "  $DEFAULT_CREDS"
        echo "Or export the path:"
        echo "  export FIREBASE_SERVICE_ACCOUNT_JSON=/path/to/credentials.json"
        echo ""
        exit 1
    fi
fi

# Run migrations and start server
echo "Running migrations..."
"$PYTHON" "$PROJECT_DIR/manage.py" migrate --run-syncdb 2>/dev/null || true

echo "Starting server at http://127.0.0.1:8000"
"$PYTHON" "$PROJECT_DIR/manage.py" runserver
