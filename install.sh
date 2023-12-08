#!/bin/bash

python -m venv ./venv
pip install -r requirements.txt
python3 ./src/pygpt_net/app.py