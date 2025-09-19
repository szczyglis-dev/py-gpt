#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   chmod +x bin/build_app_js.sh
#   ./bin/build_app_js.sh
#
# Creates a local venv (bin/.venv-jsbuild), installs rjsmin, and runs minify_js.py.

# https://codebeautify.org/jsviewer  <<< minify JS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-${SCRIPT_DIR}/.venv-jsbuild}"
PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON_BIN} not found. Set PYTHON env var or install Python 3." >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating virtual environment: ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

PY="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"

# Upgrade pip and install rjsmin
echo "Installing/upgrading rjsmin in venv..."
"${PIP}" install --upgrade pip wheel >/dev/null
"${PIP}" install --upgrade rjsmin >/dev/null

echo "Minifying and concatenating JS files..."
"${PY}" "${SCRIPT_DIR}/minify.py"

echo "Done."