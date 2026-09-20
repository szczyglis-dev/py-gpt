#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 09:00:00                  #
# ================================================== #

IPYTHON_DOCKERFILE_LEGACY = """
# Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes(Menu -> Tools -> Rebuild IPython Docker Image)

FROM python:3.9

# You can customize the packages installed by default here:
# ========================================================
RUN pip install jupyter ipykernel
# ========================================================

RUN mkdir /data

# Expose the necessary ports for Jupyter kernel communication
EXPOSE 5555 5556 5557 5558 5559

# Data directory, bound as a volume to the local 'data' directory
WORKDIR /data

# Start the IPython kernel with specified ports and settings
CMD ["ipython", "kernel",         "--ip=0.0.0.0",         "--transport=tcp",         "--shell=5555",         "--iopub=5556",         "--stdin=5557",         "--control=5558",         "--hb=5559",         "--Session.key=19749810-8febfa748186a01da2f7b28c",         "--Session.signature_scheme=hmac-sha256"]
""".strip()

IPYTHON_DOCKERFILE_PRE_BUNDLED = r"""
# Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes (Tools -> Docker -> Rebuild IPython Docker Image).

FROM python:3.12-slim

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Small set of commonly useful command-line tools plus passwordless sudo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    tree \
    ca-certificates \
    passwd \
    sudo \
    zip \
    unzip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    jq \
    file \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    group_name="$(getent group "$PYGPT_GID" | cut -d: -f1 || true)"; \
    if [ -z "$group_name" ]; then \
        groupadd --gid "$PYGPT_GID" pygpt; \
        group_name=pygpt; \
    fi; \
    useradd --uid "$PYGPT_UID" --gid "$group_name" --create-home --shell /bin/bash pygpt; \
    echo 'pygpt ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/pygpt; \
    chmod 0440 /etc/sudoers.d/pygpt; \
    mkdir -p /data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /data /opt/pygpt-venv

# Python environment required by the IPython sandbox. It is owned by the
# unprivileged user, so ordinary `pip install` does not need root privileges.
USER pygpt
RUN python -m venv /opt/pygpt-venv \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir jupyter ipykernel
ENV PATH="/opt/pygpt-venv/bin:/home/pygpt/.local/bin:${PATH}"

# Expose the necessary ports for Jupyter kernel communication.
EXPOSE 5555 5556 5557 5558 5559

# Data directory, bound as a volume to the local 'data' directory.
WORKDIR /data

# Start the IPython kernel with specified ports and settings.
CMD ["ipython", "kernel", \
"--ip=0.0.0.0", \
"--transport=tcp", \
"--shell=5555", \
"--iopub=5556", \
"--stdin=5557", \
"--control=5558", \
"--hb=5559", \
"--Session.key=19749810-8febfa748186a01da2f7b28c", \
"--Session.signature_scheme=hmac-sha256"]
""".strip()

IPYTHON_DOCKERFILE_PRE_NODEJS = r"""
# Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes (Tools -> Docker -> Rebuild IPython Docker Image).

FROM python:3.12-slim

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Common command-line tools used by the sandbox, including PDF text extraction
# utilities and fonts required for reliable chart rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    tree \
    ca-certificates \
    passwd \
    sudo \
    zip \
    unzip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    jq \
    file \
    procps \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    group_name="$(getent group "$PYGPT_GID" | cut -d: -f1 || true)"; \
    if [ -z "$group_name" ]; then \
        groupadd --gid "$PYGPT_GID" pygpt; \
        group_name=pygpt; \
    fi; \
    useradd --uid "$PYGPT_UID" --gid "$group_name" --create-home --shell /bin/bash pygpt; \
    echo 'pygpt ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/pygpt; \
    chmod 0440 /etc/sudoers.d/pygpt; \
    mkdir -p /data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /data /opt/pygpt-venv

# Python environment required by the IPython sandbox. It is owned by the
# unprivileged user, so ordinary `pip install` does not need root privileges.
# The stock image includes a practical data/science/document toolkit so agents
# can analyze files and generate charts without installing common packages first.
USER pygpt
RUN python -m venv /opt/pygpt-venv \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir \
        jupyter \
        ipykernel \
        numpy \
        pandas \
        matplotlib \
        scipy \
        sympy \
        scikit-learn \
        pillow \
        openpyxl \
        xlsxwriter \
        pypdf \
        pdfminer.six \
        pdfplumber \
        pymupdf \
        reportlab \
        python-docx \
        python-pptx \
        requests \
        beautifulsoup4 \
        lxml \
        tabulate \
        pyyaml
ENV PATH="/opt/pygpt-venv/bin:/home/pygpt/.local/bin:${PATH}"

# Expose the necessary ports for Jupyter kernel communication.
EXPOSE 5555 5556 5557 5558 5559

# Data directory, bound as a volume to the local 'data' directory.
WORKDIR /data

# Start the IPython kernel with specified ports and settings.
CMD ["ipython", "kernel", \
"--ip=0.0.0.0", \
"--transport=tcp", \
"--shell=5555", \
"--iopub=5556", \
"--stdin=5557", \
"--control=5558", \
"--hb=5559", \
"--Session.key=19749810-8febfa748186a01da2f7b28c", \
"--Session.signature_scheme=hmac-sha256"]
""".strip()

IPYTHON_DOCKERFILE = r"""
# Tip: After making changes to this Dockerfile, you must rebuild the image to apply the changes (Tools -> Docker -> Rebuild IPython Docker Image).

FROM python:3.12-slim

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Common command-line tools used by the sandbox, including PDF text extraction
# utilities and fonts required for reliable chart rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    tree \
    ca-certificates \
    passwd \
    sudo \
    zip \
    unzip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    jq \
    file \
    procps \
    nodejs \
    npm \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    group_name="$(getent group "$PYGPT_GID" | cut -d: -f1 || true)"; \
    if [ -z "$group_name" ]; then \
        groupadd --gid "$PYGPT_GID" pygpt; \
        group_name=pygpt; \
    fi; \
    useradd --uid "$PYGPT_UID" --gid "$group_name" --create-home --shell /bin/bash pygpt; \
    echo 'pygpt ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/pygpt; \
    chmod 0440 /etc/sudoers.d/pygpt; \
    mkdir -p /mnt/data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /mnt/data /opt/pygpt-venv

# Python environment required by the IPython sandbox. It is owned by the
# unprivileged user, so ordinary `pip install` does not need root privileges.
# The stock image includes a practical data/science/document toolkit so agents
# can analyze files and generate charts without installing common packages first.
USER pygpt
RUN python -m venv /opt/pygpt-venv \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir \
        jupyter \
        ipykernel \
        pytest \
        numpy \
        pandas \
        matplotlib \
        scipy \
        sympy \
        scikit-learn \
        pillow \
        openpyxl \
        xlsxwriter \
        pypdf \
        pdfminer.six \
        pdfplumber \
        pymupdf \
        reportlab \
        python-docx \
        python-pptx \
        requests \
        beautifulsoup4 \
        lxml \
        tabulate \
        pyyaml
ENV PATH="/opt/pygpt-venv/bin:/home/pygpt/.local/bin:${PATH}"

# Expose the necessary ports for Jupyter kernel communication.
EXPOSE 5555 5556 5557 5558 5559

# Data directory, bound as a volume to the local 'data' directory.
WORKDIR /mnt/data

# Start the IPython kernel with specified ports and settings.
CMD ["ipython", "kernel", \
"--ip=0.0.0.0", \
"--transport=tcp", \
"--shell=5555", \
"--iopub=5556", \
"--stdin=5557", \
"--control=5558", \
"--hb=5559", \
"--Session.key=19749810-8febfa748186a01da2f7b28c", \
"--Session.signature_scheme=hmac-sha256"]
""".strip()

PYTHON_LEGACY_DOCKERFILE_39 = """
FROM python:3.9-alpine

RUN mkdir /data

# Data directory, bound as a volume to the local 'data/' directory
WORKDIR /data
""".strip()

PYTHON_LEGACY_DOCKERFILE_PRE_BUNDLED = r"""
FROM python:3.12-alpine

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Small set of commonly useful command-line tools plus passwordless sudo.
RUN apk add --no-cache git curl wget ca-certificates sudo bash zip tree unzip tar gzip bzip2 xz jq file coreutils findutils

RUN set -eux; \
    group_name="$(awk -F: -v gid="$PYGPT_GID" '$3 == gid {print $1; exit}' /etc/group)"; \
    if [ -z "$group_name" ]; then \
        addgroup -g "$PYGPT_GID" pygpt; \
        group_name=pygpt; \
    fi; \
    adduser -D -u "$PYGPT_UID" -G "$group_name" pygpt; \
    echo 'pygpt ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/pygpt; \
    chmod 0440 /etc/sudoers.d/pygpt; \
    mkdir -p /data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /data /opt/pygpt-venv

# Keep Python packages installed at runtime outside the system interpreter.
USER pygpt
RUN python -m venv /opt/pygpt-venv
ENV PATH="/opt/pygpt-venv/bin:/home/pygpt/.local/bin:${PATH}"

# Data directory, bound as a volume to the local 'data/' directory.
WORKDIR /data
""".strip()

PYTHON_LEGACY_DOCKERFILE = r"""
FROM python:3.12-slim

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Common command-line tools used by the sandbox, including PDF text extraction
# utilities and fonts required for reliable chart rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    tree \
    ca-certificates \
    passwd \
    sudo \
    zip \
    unzip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    jq \
    file \
    procps \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    group_name="$(getent group "$PYGPT_GID" | cut -d: -f1 || true)"; \
    if [ -z "$group_name" ]; then \
        groupadd --gid "$PYGPT_GID" pygpt; \
        group_name=pygpt; \
    fi; \
    useradd --uid "$PYGPT_UID" --gid "$group_name" --create-home --shell /bin/bash pygpt; \
    echo 'pygpt ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/pygpt; \
    chmod 0440 /etc/sudoers.d/pygpt; \
    mkdir -p /mnt/data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /mnt/data /opt/pygpt-venv

# Keep Python packages installed at runtime outside the system interpreter.
# The stock image includes the same practical data/science/document toolkit as
# the IPython sandbox so both execution paths have predictable capabilities.
USER pygpt
RUN python -m venv /opt/pygpt-venv \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && /opt/pygpt-venv/bin/pip install --no-cache-dir \
        numpy \
        pandas \
        matplotlib \
        scipy \
        sympy \
        scikit-learn \
        pillow \
        openpyxl \
        xlsxwriter \
        pypdf \
        pdfminer.six \
        pdfplumber \
        pymupdf \
        reportlab \
        python-docx \
        python-pptx \
        requests \
        beautifulsoup4 \
        lxml \
        tabulate \
        pyyaml
ENV PATH="/opt/pygpt-venv/bin:/home/pygpt/.local/bin:${PATH}"

# Data directory, bound as a volume to the local 'data/' directory.
WORKDIR /mnt/data
""".strip()
