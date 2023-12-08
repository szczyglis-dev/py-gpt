#!/bin/bash

source ./venv/bin/activate
python -m build
twine check dist/*
pyinstaller linux.spec

# twine upload dist/*