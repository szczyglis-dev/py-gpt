#!/bin/bash
# This script is used to build the app using pyinstaller
source ./venv/bin/activate
python -m build
twine check dist/*
pyinstaller linux.spec

# twine upload dist/*