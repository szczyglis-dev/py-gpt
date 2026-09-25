#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .base import UpdatePayload, UpdateResult, UpdateError, UpdateCancelled


# Global kill switch for the in-app automatic update mechanism.
# Set to False to keep version checking/manual update information only.
AUTO_UPDATER_ENABLED = True


__all__ = [
    "AUTO_UPDATER_ENABLED",
    "AutoUpdater",
    "UpdatePayload",
    "UpdateResult",
    "UpdateError",
    "UpdateCancelled",
]


def __getattr__(name):
    # Keep the package lightweight for helper/test imports. Qt is only required
    # when the actual UI coordinator is requested by the application core.
    if name == "AutoUpdater":
        from .manager import AutoUpdater
        return AutoUpdater
    raise AttributeError(name)
