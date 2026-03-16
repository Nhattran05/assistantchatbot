#!/bin/bash
set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PORT=${PORT:-8000}

echo "Starting Multi-Agent API server on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port "$PORT" --reload
