#!/bin/bash
# This script is used to recursive remove the __pycache__ directories
TARGET_DIR="./src" # clear '__pycache__'

find "$TARGET_DIR" -type d -name "__pycache__" | while read -r dir
do
    echo "Removing $dir"
    rm -rf "${dir}"
done