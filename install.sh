#!/bin/bash

python -m venv ./venv
pip install -r requirements.txt
python3 run.py "$@"