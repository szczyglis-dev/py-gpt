#!/bin/bash

cd "$(dirname "$0")"
source ./venv/bin/activate
cd ./src/pygpt_net
python3 -m app