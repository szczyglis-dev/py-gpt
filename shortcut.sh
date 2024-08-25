#!/bin/bash
# This script is used to run the app using the virtual environment
cd "$(dirname "$0")"
source ./venv/bin/activate
python3 run.py "$@"