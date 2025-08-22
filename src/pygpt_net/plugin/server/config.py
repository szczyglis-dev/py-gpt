#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.22 10:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        keys = {
            "enabled": "bool",
            "name": "text",
            "host": "text",
            "login": "text",
            "password": "text",
            "port": "int",
            "desc": "textarea",
        }
        items = [
            {
                "enabled": True,
                "name": "my server",
                "host": "my.server.com",
                "login": "my_login",
                "password": "my_password",
                "port": 22,
                "desc": "This is a test configuration for SSH/SFTP connections. You can add your own servers here.",
            },
        ]
        desc = "Add your server configurations here. The model will not see any credentials, only the server name and port fields."
        plugin.add_option(
            "servers",
            type="dict",
            value=items,
            label="Servers",
            description=desc,
            tooltip=desc,
            keys=keys,
        )

        # Network / timeouts
        plugin.add_option(
            "net_timeout",
            type="int",
            value=30,
            label="Network timeout (s)",
            description="Network operations timeout.",
        )

        # SSH / SFTP (system/native and Paramiko)
        plugin.add_option(
            "prefer_system_ssh",
            type="bool",
            value=False,
            label="Prefer system ssh/scp/sftp",
            description="Use native ssh/scp/sftp binaries with system keys.",
        )
        plugin.add_option(
            "ssh_binary",
            type="text",
            value="ssh",
            label="ssh binary",
            description="Path to ssh binary.",
        )
        plugin.add_option(
            "scp_binary",
            type="text",
            value="scp",
            label="scp binary",
            description="Path to scp binary.",
        )
        plugin.add_option(
            "sftp_binary",
            type="text",
            value="sftp",
            label="sftp binary",
            description="Path to sftp binary.",
        )
        plugin.add_option(
            "ssh_options",
            type="text",
            value="",
            label="Extra ssh options",
            description="Extra options appended to ssh/scp (e.g. -o StrictHostKeyChecking=no).",
        )
        plugin.add_option(
            "ssh_auto_add_hostkey",
            type="bool",
            value=True,
            label="Paramiko: Auto add host keys",
            description="Set AutoAddPolicy for Paramiko SSHClient.",
        )

        # FTP/FTPS
        plugin.add_option(
            "ftp_use_tls_default",
            type="bool",
            value=False,
            label="FTP TLS default",
            description="Use FTP over TLS (explicit) by default.",
        )
        plugin.add_option(
            "ftp_passive_default",
            type="bool",
            value=True,
            label="FTP passive mode",
            description="Default passive mode for FTP.",
        )

        # Telnet
        plugin.add_option(
            "telnet_login_prompt",
            type="text",
            value="login:",
            label="Telnet: login prompt",
            description="Prompt text expected for username.",
        )
        plugin.add_option(
            "telnet_password_prompt",
            type="text",
            value="Password:",
            label="Telnet: password prompt",
            description="Prompt text expected for password.",
        )
        plugin.add_option(
            "telnet_prompt",
            type="text",
            value="$ ",
            label="Telnet: shell prompt",
            description="Prompt used to delimit command output.",
        )

        # SMTP
        plugin.add_option(
            "smtp_use_tls_default",
            type="bool",
            value=True,
            label="SMTP STARTTLS default",
            description="Use STARTTLS by default (e.g. port 587).",
        )
        plugin.add_option(
            "smtp_use_ssl_default",
            type="bool",
            value=False,
            label="SMTP SSL default",
            description="Use SMTP over SSL (e.g. port 465).",
        )
        plugin.add_option(
            "smtp_from_default",
            type="text",
            value="",
            label="Default From address",
            description="Used if 'from_addr' not provided in smtp_send.",
        )

        # ---------------- Commands ----------------

        # Exec
        plugin.add_cmd(
            "srv_exec",
            instruction="Execute remote shell command (SSH or Telnet).",
            params=[
                {"name": "server", "type": "str", "required": True,
                 "description": "Server name/host (from local config)"},
                {"name": "port", "type": "int", "required": True, "description": "Service port (ssh=22, telnet=23)"},
                {"name": "command", "type": "str", "required": True, "description": "Shell command to run"},
                {"name": "cwd", "type": "str", "required": False, "description": "Remote working directory"},
                {"name": "env", "type": "dict", "required": False, "description": "Environment variables dict"},
            ],
            enabled=True,
            description="Server: remote exec",
            tab="server",
        )

        # List
        plugin.add_cmd(
            "srv_ls",
            instruction="List remote directory (SFTP/FTP over data ports, SSH for 22).",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port (22/21/990)"},
                {"name": "path", "type": "str", "required": False, "description": "Remote path (default '.')"},
            ],
            enabled=True,
            description="Server: ls",
            tab="server",
        )

        # Download
        plugin.add_cmd(
            "srv_get",
            instruction="Download remote file to local data dir.",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port"},
                {"name": "remote_path", "type": "str", "required": True, "description": "Remote file path"},
                {"name": "local_path", "type": "str", "required": False, "description": "Local path (relative=./data)"},
                {"name": "overwrite", "type": "bool", "required": False,
                 "description": "Overwrite if exists (default True)"},
            ],
            enabled=True,
            description="Server: download file",
            tab="server",
        )

        # Upload
        plugin.add_cmd(
            "srv_put",
            instruction="Upload local file to remote.",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port"},
                {"name": "local_path", "type": "str", "required": True,
                 "description": "Local file path (relative=./data)"},
                {"name": "remote_path", "type": "str", "required": False,
                 "description": "Remote path (dest file path)"},
                {"name": "make_dirs", "type": "bool", "required": False, "description": "Create dirs (SFTP)"},
            ],
            enabled=True,
            description="Server: upload file",
            tab="server",
        )

        # Remove
        plugin.add_cmd(
            "srv_rm",
            instruction="Remove remote file or empty dir (non-recursive).",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port"},
                {"name": "remote_path", "type": "str", "required": True, "description": "Remote file/dir path"},
            ],
            enabled=True,
            description="Server: remove",
            tab="server",
        )

        # Mkdir
        plugin.add_cmd(
            "srv_mkdir",
            instruction="Create remote directory.",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port"},
                {"name": "remote_path", "type": "str", "required": True, "description": "Remote directory path"},
                {"name": "exist_ok", "type": "bool", "required": False, "description": "Ignore if exists"},
            ],
            enabled=True,
            description="Server: mkdir",
            tab="server",
        )

        # Stat
        plugin.add_cmd(
            "srv_stat",
            instruction="Get remote path info (type/size/mtime if available).",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "Server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "Service port"},
                {"name": "remote_path", "type": "str", "required": True, "description": "Remote path"},
            ],
            enabled=True,
            description="Server: stat",
            tab="server",
        )

        # SMTP
        plugin.add_cmd(
            "smtp_send",
            instruction="Send email via SMTP (uses local server config).",
            params=[
                {"name": "server", "type": "str", "required": True, "description": "SMTP server name/host"},
                {"name": "port", "type": "int", "required": True, "description": "SMTP port (25/465/587)"},
                {"name": "from_addr", "type": "str", "required": False,
                 "description": "From address (default from options/login)"},
                {"name": "to", "type": "list", "required": True, "description": "Recipient list"},
                {"name": "cc", "type": "list", "required": False, "description": "CC recipients"},
                {"name": "bcc", "type": "list", "required": False, "description": "BCC recipients"},
                {"name": "subject", "type": "str", "required": False, "description": "Subject"},
                {"name": "body", "type": "str", "required": False, "description": "Body (text or HTML)"},
                {"name": "html", "type": "bool", "required": False, "description": "Body is HTML"},
                {"name": "attachments", "type": "list", "required": False,
                 "description": "Local file paths (relative=./data)"},
                {"name": "use_tls", "type": "bool", "required": False, "description": "STARTTLS override"},
                {"name": "use_ssl", "type": "bool", "required": False, "description": "SSL override"},
            ],
            enabled=True,
            description="SMTP: send email",
            tab="smtp",
        )