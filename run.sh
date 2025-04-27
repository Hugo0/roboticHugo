#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the virtual environment directory name
VENV_DIR="venv"

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
  echo "Error: Virtual environment directory '$VENV_DIR' not found."
  echo "Please create and activate it first (e.g., python -m venv $VENV_DIR && source $VENV_DIR/bin/activate)"
  exit 1
fi

# Activate the virtual environment
# Use source or . depending on the shell
if [ -f "$VENV_DIR/bin/activate" ]; then
  echo "Activating virtual environment..."
  source "$VENV_DIR/bin/activate"
else
  echo "Error: Activation script not found in $VENV_DIR/bin/"
  exit 1
fi

# Check if requirements are installed
echo "Checking requirements..."
if ! pip freeze | grep -q -f requirements.txt; then
  echo "Installing requirements..."
  pip install -r requirements.txt
else
  echo "Requirements already installed."
fi

# Run the main bot script using the python module execution
echo "Running the bot (main.py)..."
python -m src.main

# Note: The script will keep running until the bot exits or is interrupted (Ctrl+C).
# Deactivation of venv happens automatically when the script exits.
echo "Bot script finished or was interrupted."