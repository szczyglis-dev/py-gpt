#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 20:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # Endpoints / HTTP
        plugin.add_option(
            "api_base",
            type="text",
            value="https://openapi.tuyaeu.com",
            label="API base",
            description="Tuya API base (eu/us/cn/in: https://openapi.tuyaeu.com / tuyaus / tuyacn / tuyain).",
        )
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )
        plugin.add_option(
            "lang",
            type="text",
            value="en",
            label="Language",
            description="Language header (e.g., en, pl).",
        )

        # Credentials
        plugin.add_option(
            "tuya_client_id",
            type="text",
            value="",
            label="Tuya Client ID",
            description="Client ID from Tuya IoT Platform Cloud project.",
            secret=True,
        )
        plugin.add_option(
            "tuya_client_secret",
            type="text",
            value="",
            label="Tuya Client Secret",
            description="Client secret from Tuya IoT Platform Cloud project.",
            secret=True,
        )
        plugin.add_option(
            "tuya_uid",
            type="text",
            value="",
            label="Tuya UID (App Account)",
            description="UID of linked Tuya App account (required for listing devices).",
        )

        # Tokens (auto)
        plugin.add_option(
            "tuya_access_token",
            type="textarea",
            value="",
            label="(auto) Access token",
            description="Stored Tuya access token.",
            secret=True,
        )
        plugin.add_option(
            "tuya_refresh_token",
            type="textarea",
            value="",
            label="(auto) Refresh token",
            description="Stored Tuya refresh token (not always used).",
            secret=True,
        )
        plugin.add_option(
            "tuya_token_expires_in",
            type="text",
            value="",
            label="(auto) Expires in (s)",
            description="Token lifetime seconds.",
        )
        plugin.add_option(
            "tuya_token_expire_at",
            type="text",
            value="0",
            label="(auto) Expire at (epoch s)",
            description="Timestamp when token is considered expired.",
        )

        # Cache
        plugin.add_option(
            "tuya_cached_devices",
            type="textarea",
            value="[]",
            label="(auto) Cached devices",
            description="Cached devices for quick search.",
        )

        # ---------------- Commands ----------------

        # Auth
        plugin.add_cmd(
            "tuya_set_keys",
            instruction="Set Tuya Cloud credentials.",
            params=[
                {"name": "client_id", "type": "str", "required": True, "description": "Tuya Client ID"},
                {"name": "client_secret", "type": "str", "required": True, "description": "Tuya Client Secret"},
            ],
            enabled=True,
            description="Auth: set keys",
            tab="auth",
        )
        plugin.add_cmd(
            "tuya_set_uid",
            instruction="Set Tuya App Account UID (for listing devices).",
            params=[
                {"name": "uid", "type": "str", "required": True, "description": "UID of linked Tuya account"},
            ],
            enabled=True,
            description="Auth: set UID",
            tab="auth",
        )
        plugin.add_cmd(
            "tuya_token_get",
            instruction="Obtain access token (grant_type=1).",
            params=[],
            enabled=True,
            description="Auth: get token",
            tab="auth",
        )

        # Devices
        plugin.add_cmd(
            "tuya_devices_list",
            instruction="List devices for UID.",
            params=[
                {"name": "uid", "type": "str", "required": False, "description": "Override UID (optional)"},
                {"name": "page_no", "type": "int", "required": False, "description": "Page number (default 1)"},
                {"name": "page_size", "type": "int", "required": False, "description": "Page size (default 100)"},
            ],
            enabled=True,
            description="Devices: list",
            tab="devices",
        )
        plugin.add_cmd(
            "tuya_device_get",
            instruction="Get device info.",
            params=[{"name": "device_id", "type": "str", "required": True, "description": "Device ID"}],
            enabled=True,
            description="Devices: get info",
            tab="devices",
        )
        plugin.add_cmd(
            "tuya_device_status",
            instruction="Get device status (DP values).",
            params=[{"name": "device_id", "type": "str", "required": True, "description": "Device ID"}],
            enabled=True,
            description="Devices: status",
            tab="devices",
        )
        plugin.add_cmd(
            "tuya_device_functions",
            instruction="Get device supported functions (DP codes).",
            params=[{"name": "device_id", "type": "str", "required": True, "description": "Device ID"}],
            enabled=True,
            description="Devices: functions",
            tab="devices",
        )
        plugin.add_cmd(
            "tuya_find_device",
            instruction="Find device(s) by name (uses cached device list).",
            params=[{"name": "name", "type": "str", "required": True, "description": "Substring match"}],
            enabled=True,
            description="Devices: find by name",
            tab="devices",
        )

        # Control
        plugin.add_cmd(
            "tuya_device_set",
            instruction="Set a device DP value or multiple values.",
            params=[
                {"name": "device_id", "type": "str", "required": True, "description": "Device ID"},
                {"name": "code", "type": "str", "required": False, "description": "DP code (if single)"},
                {"name": "value", "type": "str", "required": False, "description": "Value for 'code'"},
                {"name": "codes", "type": "dict", "required": False, "description": "Dict of {code: value}"},
            ],
            enabled=True,
            description="Control: set DP(s)",
            tab="control",
        )
        plugin.add_cmd(
            "tuya_device_send",
            instruction="Send raw commands list to device.",
            params=[
                {"name": "device_id", "type": "str", "required": True, "description": "Device ID"},
                {"name": "commands", "type": "list", "required": True, "description": "[{'code':'','value':..},...]"},
            ],
            enabled=True,
            description="Control: send commands",
            tab="control",
        )
        plugin.add_cmd(
            "tuya_device_on",
            instruction="Turn device ON (guesses switch code if not provided).",
            params=[
                {"name": "device_id", "type": "str", "required": True, "description": "Device ID"},
                {"name": "code", "type": "str", "required": False, "description": "Preferred switch code"},
            ],
            enabled=True,
            description="Control: on",
            tab="control",
        )
        plugin.add_cmd(
            "tuya_device_off",
            instruction="Turn device OFF (guesses switch code if not provided).",
            params=[
                {"name": "device_id", "type": "str", "required": True, "description": "Device ID"},
                {"name": "code", "type": "str", "required": False, "description": "Preferred switch code"},
            ],
            enabled=True,
            description="Control: off",
            tab="control",
        )
        plugin.add_cmd(
            "tuya_device_toggle",
            instruction="Toggle device state (reads current boolean DP).",
            params=[
                {"name": "device_id", "type": "str", "required": True, "description": "Device ID"},
                {"name": "code", "type": "str", "required": False, "description": "Preferred switch code"},
            ],
            enabled=True,
            description="Control: toggle",
            tab="control",
        )

        # Sensors
        plugin.add_cmd(
            "tuya_sensors_read",
            instruction="Read and normalize common sensor values.",
            params=[{"name": "device_id", "type": "str", "required": True, "description": "Sensor device ID"}],
            enabled=True,
            description="Sensors: read",
            tab="sensors",
        )