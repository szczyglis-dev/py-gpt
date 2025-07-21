#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
INI_FILES_DIR="$SCRIPT_DIR/../src/pygpt_net/data/locale"
ENGLISH_FILE="$INI_FILES_DIR/locale.en.ini"

if [ ! -f "$ENGLISH_FILE" ]; then
    echo "Missing .en file: $ENGLISH_FILE"
    exit 1
fi

mapfile -t en_lines < <(sed '1d;/^\s*$/d' "$ENGLISH_FILE")

declare -a en_keys
declare -A english_map

for line in "${en_lines[@]}"; do
    key="${line%%=*}"
    value="${line#*=}"
    en_keys+=( "$key" )
    english_map["$key"]="$value"
done

declare -A global_missing_count
total_lang_count=0

for file in "$INI_FILES_DIR"/locale.*.ini; do
    base=$(basename "$file")
    if [[ "$base" == "locale.en.ini" ]]; then
        continue
    fi

    total_lang_count=$(( total_lang_count + 1 ))

    lang="${base#locale.}"
    lang="${lang%.ini}"

    declare -A trans_keys=()
    while IFS= read -r line; do
         [[ -z "$line" ]] && continue
         key="${line%%=*}"
         trans_keys["$key"]=1
    done < <(sed '1d;/^\s*$/d' "$file")

    missing_keys=()
    for key in "${en_keys[@]}"; do
         if [[ -z "${trans_keys[$key]}" ]]; then
              missing_keys+=( "$key=${english_map[$key]}" )
              global_missing_count["$key"]=$(( ${global_missing_count["$key"]:-0} + 1 ))
         fi
    done

    if [ ${#missing_keys[@]} -gt 0 ]; then
         echo "[$lang]"
         for k in "${missing_keys[@]}"; do
              echo "$k"
         done
         echo ""
    fi
done

if [ "$total_lang_count" -gt 0 ]; then
    shared_keys=()
    for key in "${en_keys[@]}"; do
         if [ "${global_missing_count[$key]:-0}" -eq "$total_lang_count" ]; then
              shared_keys+=( "$key=${english_map[$key]}" )
         fi
    done

    if [ ${#shared_keys[@]} -gt 0 ]; then
         echo "[ALL]"
         for k in "${shared_keys[@]}"; do
              echo "$k"
         done
         echo ""
    fi
fi