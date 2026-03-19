#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

export WANGP_HOST="${WANGP_HOST:-0.0.0.0}"
export WANGP_PORT="${WANGP_PORT:-8100}"
export WANGP_UPLOAD_DIR="${WANGP_UPLOAD_DIR:-uploads}"
export WANGP_OUTPUT_DIR="${WANGP_OUTPUT_DIR:-output}"

if [ -z "${WANGP_API_KEY:-}" ]; then
    echo "WARNING: WANGP_API_KEY is not set. The server will accept unauthenticated requests."
fi

PYTHON="${WANGP_PYTHON:-python}"

if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
fi

echo "Starting Wan2GP REST API on ${WANGP_HOST}:${WANGP_PORT}..."
exec "$PYTHON" -m server.main
