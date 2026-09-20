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

SYSTEM_DOCKERFILE_39 = """
FROM python:3.9-alpine

RUN mkdir /data

# Data directory, bound as a volume to the local 'data/' directory
WORKDIR /data
""".strip()

SYSTEM_DOCKERFILE = r"""
FROM python:3.12-alpine

# IDs are supplied by PyGPT while building the stock image. On Linux they
# match the desktop user so bind-mounted files keep the correct ownership.
ARG PYGPT_UID=1000
ARG PYGPT_GID=1000

# Small set of commonly useful command-line tools plus passwordless sudo.
RUN apk add --no-cache git curl wget ca-certificates sudo bash zip unzip tar gzip bzip2 xz jq file tree coreutils findutils

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
