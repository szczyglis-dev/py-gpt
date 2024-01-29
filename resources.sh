#!/bin/bash

source ./venv/bin/activate
python3 scripts/resources.py "$@"
cd "$(dirname "$0")"/src/pygpt_net
pyside6-rcc icons.qrc -o icons_rc.py
echo "Resources compiled to: src/pygpt_net/icons_rc.py"