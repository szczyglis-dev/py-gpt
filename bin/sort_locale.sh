#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
INI_FILES_DIR="$SCRIPT_DIR/../src/pygpt_net/data/locale"

sort_ini_file_script='
sort_ini_file() {
    local ini_file="$1"
    first_line=$(sed -n "1p" "$ini_file")
    (echo "$first_line"; sed "1d;/^$/d" "$ini_file" | sort) > "${ini_file}.sorted"
    mv "${ini_file}.sorted" "$ini_file"
}
sort_ini_file "$0"
'

find "$INI_FILES_DIR" -type f -name "*.ini" -exec bash -c "$sort_ini_file_script" {} \;

echo "All .ini files in $INI_FILES_DIR have been processed."
