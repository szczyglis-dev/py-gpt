#!/bin/bash

cd "$(dirname "$0")"
DIR_CURRENT="$(pwd)"
DIR_PARENT="$(dirname "$DIR_CURRENT")"

cd $DIR_PARENT

source ./venv/bin/activate
python3 bin/resources.py "$@"

cd $DIR_PARENT/src/pygpt_net
pyside6-rcc icons.qrc -o icons_rc.py
pyside6-rcc js.qrc -o js_rc.py
pyside6-rcc css.qrc -o css_rc.py
pyside6-rcc fonts.qrc -o fonts_rc.py

echo "Resources compiled to: src/pygpt_net/icons_rc.py"
echo "Resources compiled to: src/pygpt_net/js_rc.py"
echo "Resources compiled to: src/pygpt_net/css_rc.py"
echo "Resources compiled to: src/pygpt_net/fonts_rc.py"