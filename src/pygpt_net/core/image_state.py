#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 14:20:00                  #
# ================================================== #

import os
from typing import Optional

from pygpt_net.item.ctx import CtxItem


LAST_GENERATED_IMAGE_PATH = "image_generation_last_path"
LAST_USER_REFERENCE_IMAGE_PATH = "image_generation_reference_path"


def resolve_local_image_path(core, value: Optional[str], ctx: Optional[CtxItem] = None) -> Optional[str]:
    """
    Resolve a workdir/local image reference and make sure it points to an
    existing image file.

    :param core: application core
    :param value: local path or path containing the %workdir% placeholder
    :return: absolute local image path or None
    """
    if not value:
        return None

    path = str(value).strip()
    if not path or path.startswith(("http://", "https://", "gs://")):
        return None

    try:
        path = core.filesystem.normalize_local_path(path, ctx=ctx)
    except Exception:
        try:
            path = core.filesystem.to_workdir(path, auto_prefix=False, ctx=ctx)
        except Exception:
            return None

    if not os.path.isfile(path):
        return None
    if not core.filesystem.types.is_image(path):
        return None
    return os.path.normpath(path)


def make_portable_image_path(core, value: Optional[str], ctx: Optional[CtxItem] = None) -> Optional[str]:
    """Return an existing local image path using the %workdir% placeholder when possible."""
    path = resolve_local_image_path(core, value, ctx=ctx)
    if path is None:
        return None
    return core.filesystem.make_local(path, ctx=ctx)


def remember_generated_image_path(core, ctx: Optional[CtxItem], paths: list) -> Optional[str]:
    """
    Persist the last generated local image path in the context item's ``extra``
    payload. ``CtxItem.extra`` is serialized to the context database, so this
    survives application restarts without adding a schema migration.

    :param core: application core
    :param ctx: context item used by image generation
    :param paths: generated image paths
    :return: stored portable path or None
    """
    if ctx is None or not paths:
        return None

    for value in reversed(paths):
        path = make_portable_image_path(core, value, ctx=ctx)
        if path is None:
            continue
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra[LAST_GENERATED_IMAGE_PATH] = path
        return path
    return None


def remember_user_reference_image_path(
        core,
        ctx: Optional[CtxItem],
        value: Optional[str]
) -> Optional[str]:
    """
    Persist the image attached/referenced by the user for reuse after the
    transient attachment queue is cleared.

    :param core: application core
    :param ctx: current context item
    :param value: image path
    :return: stored portable path or None
    """
    if ctx is None:
        return None
    path = make_portable_image_path(core, value, ctx=ctx)
    if path is None:
        return None
    if not isinstance(ctx.extra, dict):
        ctx.extra = {}
    ctx.extra[LAST_USER_REFERENCE_IMAGE_PATH] = path

    # Keep the user-provided reference in the regular image context as well.
    # ``ctx.extra`` is enough for resolving a later image-tool reference, but
    # the chat history renderer restores visible image attachments from
    # ``ctx.images`` (persisted in ``images_json``). Without this, an image used
    # only by the Image generation plugin is visible during the live turn but
    # disappears after reloading the conversation.
    if not isinstance(ctx.images, list):
        ctx.images = []
    if path not in ctx.images:
        ctx.images.append(path)

    return path


def _get_generated_path_from_ctx(core, ctx: Optional[CtxItem]) -> tuple[bool, Optional[str]]:
    """Return (is_image_generation_ctx, reusable_local_path)."""
    if ctx is None or not isinstance(ctx.extra, dict):
        return False, None

    is_generation = (
        LAST_GENERATED_IMAGE_PATH in ctx.extra
        or "image_id" in ctx.extra
    )
    if not is_generation:
        return False, None

    # New explicit cache written by the image response controller.
    path = make_portable_image_path(core, ctx.extra.get(LAST_GENERATED_IMAGE_PATH), ctx=ctx)
    if path:
        return True, path

    # Backward compatibility: OpenAI/Google image providers already persisted
    # image_id in older contexts. Use it only when it resolves to a local image.
    path = make_portable_image_path(core, ctx.extra.get("image_id"), ctx=ctx)
    if path:
        return True, path

    # Google Imagen may persist a remote image_id while the locally saved image
    # is still present in ctx.images. The presence of image_id identifies this as
    # an image-generation context rather than an arbitrary image attachment.
    if ctx.extra.get("image_id") and getattr(ctx, "images", None):
        for value in reversed(ctx.images):
            path = make_portable_image_path(core, value, ctx=ctx)
            if path:
                return True, path
    return True, None


def get_last_generated_image_path(core, ctx: Optional[CtxItem] = None) -> Optional[str]:
    """
    Find the newest reusable generated image in the current conversation.
    The live ``ctx`` is checked first so agent/tool chains can reuse an image
    generated earlier in the same turn.
    """
    is_generation, path = _get_generated_path_from_ctx(core, ctx)
    if is_generation:
        return path

    try:
        items = core.ctx.get_items()
    except Exception:
        items = []

    for item in reversed(items or []):
        if item is ctx:
            continue
        is_generation, path = _get_generated_path_from_ctx(core, item)
        if is_generation:
            # Do not fall back to an older generated image when the newest one
            # was removed from disk. "Previously generated" means the latest
            # generation result in the conversation.
            return path
    return None


def _get_user_reference_path_from_ctx(core, ctx: Optional[CtxItem]) -> tuple[bool, Optional[str]]:
    """Return (has_reference_marker, reusable_local_path)."""
    if ctx is None or not isinstance(ctx.extra, dict):
        return False, None
    if LAST_USER_REFERENCE_IMAGE_PATH not in ctx.extra:
        return False, None
    return True, make_portable_image_path(core, ctx.extra.get(LAST_USER_REFERENCE_IMAGE_PATH), ctx=ctx)


def get_last_user_reference_image_path(core, ctx: Optional[CtxItem] = None) -> Optional[str]:
    """
    Find the most recent user-attached/reference image cached in this
    conversation. If that newest reference no longer exists on disk, do not
    silently fall back to an older attachment.
    """
    has_reference, path = _get_user_reference_path_from_ctx(core, ctx)
    if has_reference:
        return path

    try:
        items = core.ctx.get_items()
    except Exception:
        items = []

    for item in reversed(items or []):
        if item is ctx:
            continue
        has_reference, path = _get_user_reference_path_from_ctx(core, item)
        if has_reference:
            return path
    return None


def get_current_user_image_path(core, mode: str, ctx: Optional[CtxItem] = None) -> Optional[str]:
    """
    Return the most recently attached image from the current user input.
    Only the active attachment queue is inspected; historical context
    attachments are intentionally ignored here.
    """
    try:
        attachments = core.attachments.get_all(mode)
    except Exception:
        return None

    if not attachments:
        return None

    for attachment in reversed(list(attachments.values())):
        path = make_portable_image_path(core, getattr(attachment, "path", None), ctx=ctx)
        if path:
            return path
    return None
