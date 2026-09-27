#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 10:00:00                  #
# ================================================== #

import json
import os
from typing import Optional

from packaging.version import parse as parse_version, Version

from ..utils import safe_copy_preset


class Patch:
    """Migrate retired OpenAI-agent preset files to LlamaIndex agent presets."""

    VERSION = parse_version("2.8.33")
    OLD_PREFIX = "agent_openai_"
    NEW_PREFIX = "agent_"
    REMOVE_FILES = (
        "agent_openai.json",
        "agent_react.json",
    )

    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate presets introduced before 2.8.33.

        The migration is file based on purpose: preset filenames are part of the
        user profile and have to be renamed on disk, not only in the in-memory
        registry.

        :param version: current app version
        :return: True if any user preset was changed
        """
        if version < self.VERSION:
            return False

        presets_dir = self.window.core.config.get_user_dir("presets")
        if not os.path.isdir(presets_dir):
            return False

        migrated = False
        planner_source = os.path.join(presets_dir, "agent_openai_planner.json")

        # Remove retired standalone presets first.
        for filename in self.REMOVE_FILES:
            path = os.path.join(presets_dir, filename)
            if os.path.isfile(path):
                os.remove(path)
                print("Removed retired preset: {}.".format(path))
                migrated = True

        # The old Llama planner used the same filename as the new canonical
        # planner. Remove it only while it is actually the retired workflow (or
        # when an agent_openai_planner source is waiting to replace it). This
        # keeps the migration idempotent on every later startup.
        planner_target = os.path.join(presets_dir, "agent_planner.json")
        remove_old_planner = os.path.isfile(planner_source)
        if os.path.isfile(planner_target) and not remove_old_planner:
            planner_data = self._load_json(planner_target)
            remove_old_planner = bool(
                planner_data is not None
                and planner_data.get("agent_provider") == "planner"
            )
        if remove_old_planner and os.path.isfile(planner_target):
            os.remove(planner_target)
            print("Removed retired preset: {}.".format(planner_target))
            migrated = True

        # Rename every agent_openai_* user preset to agent_* while preserving
        # the user's actual JSON payload (including fields unknown to this
        # version of PresetItem). Existing canonical targets are overwritten:
        # install() may have just copied a stock 2.8.33 target before this patch
        # gets a chance to migrate the user's customized legacy source.
        for filename in list(os.listdir(presets_dir)):
            if not (filename.startswith(self.OLD_PREFIX) and filename.endswith(".json")):
                continue

            src = os.path.join(presets_dir, filename)
            suffix = filename[len(self.OLD_PREFIX):]
            target_filename = self.NEW_PREFIX + suffix
            dst = os.path.join(presets_dir, target_filename)

            data = self._load_json(src)
            if data is None:
                continue

            self._migrate_data(data)
            data["filename"] = os.path.splitext(target_filename)[0]
            self._touch_meta(data)
            self._save_json(dst, data)
            os.remove(src)
            print("Renamed preset: {} -> {}.".format(src, dst))
            migrated = True

        # Migrate OpenAI-agent flags/providers also in custom presets whose
        # filenames do not follow agent_openai_*. Persist the old ReAct
        # provider cleanup at the same time instead of relying on runtime-only
        # compatibility mapping.
        for filename in list(os.listdir(presets_dir)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(presets_dir, filename)
            data = self._load_json(path)
            if data is None:
                continue
            if self._migrate_data(data):
                self._touch_meta(data)
                self._save_json(path, data)
                print("Migrated agent preset: {}.".format(path))
                migrated = True

        # A profile old enough not to contain agent_openai_planner.json still
        # needs the canonical planner after the retired legacy planner was
        # removed. Copy the 2.8.33 stock preset in that case.
        planner_target = os.path.join(presets_dir, "agent_planner.json")
        if not os.path.isfile(planner_target):
            if safe_copy_preset(self.window, "agent_planner.json"):
                migrated = True

        if migrated:
            self.window.core.presets.load()

        return migrated

    @staticmethod
    def _load_json(path: str) -> Optional[dict]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception as e:
            print("Failed to load preset {}: {}".format(path, e))
            return None

    @staticmethod
    def _save_json(path: str, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _touch_meta(self, data: dict):
        data["__meta__"] = self.window.core.config.append_meta()

    @staticmethod
    def _migrate_data(data: dict) -> bool:
        # Local import avoids pulling the agents package while preset provider
        # modules are still being imported during application bootstrap.
        from pygpt_net.core.agents.compatibility import (
            OPENAI_TO_LLAMA,
            RETIRED_LLAMA_PROVIDERS,
        )

        updated = False
        source = data.get("agent_provider_openai")
        target = OPENAI_TO_LLAMA.get(source)

        if data.get("agent_openai") and target:
            if data.get("agent_provider") != target:
                data["agent_provider"] = target
                updated = True
            if not data.get("agent_llama"):
                data["agent_llama"] = True
                updated = True
            if data.get("agent_openai"):
                data["agent_openai"] = False
                updated = True

            extra = data.get("extra")
            if isinstance(extra, dict) and source in extra and target not in extra:
                # JSON round-trip already gives us an independent structure.
                extra[target] = extra[source]
                updated = True

        if data.get("agent_provider") in RETIRED_LLAMA_PROVIDERS:
            data["agent_provider"] = "llama_agent_base"
            updated = True

        return updated
