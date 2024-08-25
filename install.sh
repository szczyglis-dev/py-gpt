#!/bin/bash
# This script is used to install the app dependencies and run the app using the virtual environment
python -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
python3 run.py "$@"