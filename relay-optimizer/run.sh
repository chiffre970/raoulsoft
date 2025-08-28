#!/bin/bash

# Relay Optimizer Launch Script

# Use Python with tkinter if available
if command -v /opt/homebrew/bin/python3.13 &> /dev/null; then
    PYTHON_CMD=/opt/homebrew/bin/python3.13
elif ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
else
    PYTHON_CMD=python3
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Run the application
echo "Starting Relay Optimizer..."
python src/main.py

# Deactivate virtual environment when done
deactivate