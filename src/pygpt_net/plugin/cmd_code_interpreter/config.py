#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 16:30:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


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
    mkdir -p /data /opt/pygpt-venv; \
    chown -R "$PYGPT_UID:$PYGPT_GID" /data /opt/pygpt-venv

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
WORKDIR /data
""".strip()


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        dockerfile = IPYTHON_DOCKERFILE
        dockerfile_legacy = PYTHON_LEGACY_DOCKERFILE

        plugin.add_option(
            "sandbox_ipython",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_run_as_root",
            type="bool",
            value=False,
            label="Run as root",
            description="Run the IPython Docker sandbox as root. When disabled, the stock sandbox image runs as "
                        "the unprivileged 'pygpt' user and passwordless sudo can be used for commands that require "
                        "root privileges.",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_dockerfile",
            type="textarea",
            value=dockerfile,
            label="Dockerfile for IPython kernel",
            description="Dockerfile used to build IPython kernel container image",
            tooltip="Dockerfile",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_image_name",
            type="text",
            value='pygpt_ipython_kernel',
            label="Docker image name",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_container_name",
            type="text",
            value='pygpt_ipython_kernel_container',
            label="Docker container name",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_session_key",
            type="text",
            value='19749810-8febfa748186a01da2f7b28c',
            label="Session Key",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_conn_addr",
            type="text",
            value='127.0.0.1',
            label="Connection Address",
            tab="ipython",
        )
        plugin.add_cmd(
            "ipython_execute",
            instruction="execute Python code in IPython interpreter (in current kernel) and get output. "
                        "Tip: when generating plots or other image data always print path to generated image at "
                        "the end and provide local path (prefixed with file://, not sandbox:) to the user.",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in current kernel)",
            tab="ipython",
        )
        plugin.add_cmd(
            "ipython_sys_exec",
            instruction="execute a system/shell command in the Code Interpreter environment. "
                        "When the IPython Docker sandbox is enabled, execute the command inside the same "
                        "running IPython container. When the sandbox is disabled, execute it on the host. "
                        "Use this for operating-system commands and command-line tools; use ipython_execute "
                        "for Python code.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system/shell command to execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution in the IPython environment",
            tab="ipython",
        )
        """
        plugin.add_cmd(
            "ipython_execute_new",
            instruction="execute Python code in the IPython interpreter in a new kernel and get the output. Use this option only if a kernel restart is required; otherwise, use `ipython_execute` to run the code in the current session",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to execute in IPython interpreter, usage of !magic commands is allowed",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows Python code execution in IPython interpreter (in new kernel)",
            tab="ipython",
        )
        """

        volumes_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "text",
        }
        volumes_items = [
            {
                "enabled": True,
                "docker": "/data",
                "host": "{workdir}",
            },
        ]
        ports_keys = {
            "enabled": "bool",
            "docker": "text",
            "host": "int",
        }
        ports_items = []

        plugin.add_cmd(
            "ipython_kernel_restart",
            instruction="restart IPython kernel",
            params=[],
            enabled=True,
            description="Allows to restart IPython kernel",
            tab="ipython",
        )
        plugin.add_option(
            "ipython_port_shell",
            type="int",
            value=5555,
            label="Port: shell",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_iopub",
            type="int",
            value=5556,
            label="Port: iopub",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_stdin",
            type="int",
            value=5557,
            label="Port: stdin",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_control",
            type="int",
            value=5558,
            label="Port: control",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "ipython_port_hb",
            type="int",
            value=5559,
            label="Port: hb",
            tab="ipython",
            advanced=True,
        )
        plugin.add_option(
            "sandbox_docker",
            type="bool",
            value=False,
            label="Sandbox (docker container)",
            description="Executes commands in sandbox (docker container). "
                        "Docker must be installed and running.",
            tab="python_legacy",
        )
        plugin.add_option(
            "docker_run_as_root",
            type="bool",
            value=False,
            label="Run as root",
            description="Run the Python Docker sandbox as root. When disabled, the stock sandbox image runs as "
                        "the unprivileged 'pygpt' user and passwordless sudo can be used for commands that require "
                        "root privileges.",
            tab="python_legacy",
        )
        plugin.add_option(
            "python_cmd_tpl",
            type="text",
            value="python3 {filename}",
            label="Python command template",
            description="Python command template to execute, use {filename} for filename placeholder",
            tab="python_legacy",
        )
        plugin.add_option(
            "dockerfile",
            type="textarea",
            value=dockerfile_legacy,
            label="Dockerfile",
            description="Dockerfile",
            tooltip="Dockerfile",
            tab="python_legacy",
        )
        plugin.add_option(
            "image_name",
            type="text",
            value='pygpt_python_legacy',
            label="Docker image name",
            tab="python_legacy",
        )
        plugin.add_option(
            "container_name",
            type="text",
            value='pygpt_python_legacy_container',
            label="Docker container name",
            tab="python_legacy",
        )
        plugin.add_option(
            "docker_entrypoint",
            type="text",
            value='tail -f /dev/null',
            label="Docker run command",
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "docker_volumes",
            type="dict",
            value=volumes_items,
            label="Docker volumes",
            description="Docker volumes mapping",
            tooltip="Docker volumes mapping",
            keys=volumes_keys,
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "docker_ports",
            type="dict",
            value=ports_items,
            label="Docker ports",
            description="Docker ports mapping",
            tooltip="Docker ports mapping",
            keys=ports_keys,
            tab="python_legacy",
            advanced=True,
        )
        plugin.add_option(
            "attach_output",
            type="bool",
            value=True,
            label="Connect to the Python code interpreter window",
            description="Attach code input/output to the Python code interpreter window.",
            tab="general",
        )
        plugin.add_option(
            "output_max_entries",
            type="int",
            value=30,
            min=0,
            max=10000,
            label="Max interpreter window entries",
            description="Maximum number of input/output blocks kept in the Python code interpreter window. Set to 0 for no limit.",
            tab="general",
        )
        plugin.add_option(
            "fresh_kernel",
            type="bool",
            value=False,
            label="Always run code in a fresh kernel",
            description="Always run code using Run in a fresh kernel.",
            tab="general",
        )

        # commands
        plugin.add_cmd(
            "python_sys_exec",
            instruction="execute a system/shell command in the legacy Python Code Interpreter environment. "
                        "When the legacy Python Docker sandbox is enabled, execute the command inside the same "
                        "Python container. When the sandbox is disabled, execute it on the host. Use this for "
                        "operating-system commands and command-line tools; use code_execute/code_execute_file "
                        "for Python code.",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "system/shell command to execute",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows system commands execution in the legacy Python environment",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "code_execute",
            instruction="save generated Python code and execute it",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "path to save",
                    "default": ".interpreter.current.py",
                    "required": True,
                },
                {
                    "name": "code",
                    "type": "str",
                    "description": "code",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "code_execute_file",
            instruction="execute Python code from existing file",
            params=[
                {
                    "name": "path",
                    "type": "str",
                    "description": "file path",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution from existing file",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "code_execute_all",
            instruction="run all Python code from my interpreter",
            params=[
                {
                    "name": "code",
                    "type": "str",
                    "description": "code to append and execute",
                    "required": True,
                },
            ],
            enabled=False,
            description="Allows Python code execution (generate and execute from file)",
            tab="python_legacy",
        )
        plugin.add_cmd(
            "get_python_output",
            instruction="get output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get output from last executed code",
            tab="general",
        )
        plugin.add_cmd(
            "get_python_input",
            instruction="get all input code from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to get input from Python interpreter",
            tab="general",
        )
        plugin.add_cmd(
            "clear_python_output",
            instruction="clear output from my Python interpreter",
            params=[],
            enabled=True,
            description="Allows to clear output from last executed code",
            tab="general",
        )
        plugin.add_cmd(
            "render_html_output",
            instruction="send HTML/JS code to HTML built-in browser (HTML Canvas) and render it",
            params=[
                {
                    "name": "html",
                    "type": "str",
                    "description": "HTML/JS code",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows to render HTML/JS code in HTML Canvas",
            tab="html_canvas",
        )
        plugin.add_cmd(
            "get_html_output",
            instruction="get current output from HTML Canvas",
            params=[],
            enabled=True,
            description="Allows to get current output from HTML Canvas",
            tab="html_canvas",
        )