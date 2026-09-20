#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.20 13:00:00                  #
# ================================================== #

"""Packages provisioned into uv-managed Built-in sandbox environments.

Keep these lists declarative so the stock sandbox can be changed without
modifying the runtime/provisioning implementation. Updating a list also changes
the environment marker, therefore PyGPT recreates the affected venv on the next
startup/first use.
"""

# Base packaging tools installed/upgraded in every Built-in venv. This mirrors
# the bootstrap step used by the stock Docker Python environments.
BUILTIN_BASE_PACKAGES = [
    "pip",
    "setuptools",
    "wheel",
]

# Mirrors the stock ordinary-Python Docker sandbox (PYTHON_LEGACY_DOCKERFILE).
# Built-in mode intentionally uses CPython rather than IPython/Jupyter, hence
# jupyter/ipykernel are not part of this list.
BUILTIN_PYTHON_PACKAGES = [
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "sympy",
    "scikit-learn",
    "pillow",
    "openpyxl",
    "xlsxwriter",
    "pypdf",
    "pdfminer.six",
    "pdfplumber",
    "pymupdf",
    "reportlab",
    "python-docx",
    "python-pptx",
    "requests",
    "beautifulsoup4",
    "lxml",
    "tabulate",
    "pyyaml",
]

# The stock System/OS Docker image creates a venv but does not pre-install
# additional Python packages. Add packages here if the Built-in OS sandbox
# should provide them by default.
BUILTIN_OS_PACKAGES = []

BUILTIN_SANDBOX_PACKAGES = {
    "python": BUILTIN_PYTHON_PACKAGES,
    "os": BUILTIN_OS_PACKAGES,
}


def get_builtin_packages(name: str) -> list[str]:
    """Return a copy of backend-specific default packages."""
    return list(BUILTIN_SANDBOX_PACKAGES.get(name, []))


def get_builtin_environment_packages(name: str) -> list[str]:
    """Return the complete package spec used to version a Built-in venv."""
    return [*BUILTIN_BASE_PACKAGES, *get_builtin_packages(name)]
