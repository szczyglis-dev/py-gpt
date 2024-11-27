#!/bin/bash
# This script is used to recursive remove the __pycache__ directories

cd "$(dirname "$0")"
DIR_CURRENT="$(pwd)"
DIR_PARENT="$(dirname "$DIR_CURRENT")"
TARGET_DIR="$DIR_PARENT/src" # clear '__pycache__'

find "$TARGET_DIR" -type d -name "__pycache__" | while read -r dir
do
    echo "Removing $dir"
    rm -rf "${dir}"
done