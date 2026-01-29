#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

mkdir -p ../data/source ../data/temp ../data/config

export DIETTUBE_SOURCE_DIR="../data/source"
export DIETTUBE_TEMP_DIR="../data/temp"
export DIETTUBE_CONFIG_DIR="../data/config"

echo "Starting backend on http://localhost:8000"
uvicorn app.main:app --reload --port 8000
