#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 16:00:00                  #
# ================================================== #

import os
from typing import Optional, List

from PySide6.QtCore import Slot

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types import MODE_IMAGE
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Image controller

        :param window: Window instance
        """
        self.window = window

    def send(
            self,
            text: str,
            prev_ctx: Optional[CtxItem] = None,
    ) -> CtxItem:
        """
        Send prompt for image generate

        :param text: prompt for image generation
        :param prev_ctx: previous ctx item
        :return: ctx item
        """
        core = self.window.core
        controller = self.window.controller
        update_status = self.window.update_status
        dispatch = self.window.dispatch

        num = int(self.window.ui.config['global']['img_variants'].text() or 1)
        if num < 1:
            num = 1
        elif num > 4:
            num = 4

        # force 1 image if dall-e-3 model is used
        mode = core.config.get('mode')
        model = core.config.get('model')
        model_data = core.models.get(model)
        extra_prompt = self.window.ui.nodes['input_extra'].toPlainText().strip()
        if (model_data and model_data.id
                and (model_data.id == 'dall-e-3' or model_data.id.startswith('gpt-image-1'))):
            num = 1

        update_status(trans('status.sending'))

        # create ctx item
        ctx = CtxItem()
        ctx.current = True  # mark as current context item
        ctx.meta = core.ctx.get_current_meta()  # CtxMeta (owner object)
        ctx.set_input(text, core.config.get('user_name'))
        ctx.prev_ctx = prev_ctx  # store previous context item
        ctx.live = True

        # prepare previous image_id and video_id from last context (for variations)
        image_id = None
        video_id = None

        if core.config.get("video.remix") or core.config.get("img.remix"):
            items = core.ctx.get_items()
            reversed_items = reversed(items)
            for item in reversed_items:
                if isinstance(item.extra, dict):
                    if core.config.get("video.remix"):
                        tmp_video_id = item.extra.get('video_id')
                        if video_id is None and tmp_video_id:
                            video_id = tmp_video_id
                    if core.config.get("img.remix"):
                        tmp_image_id = item.extra.get('image_id')
                        if image_id is None and tmp_image_id:
                            image_id = tmp_image_id
                if image_id and video_id:
                    break

        # event: context before
        event = Event(Event.CTX_BEFORE)
        event.ctx = ctx
        dispatch(event)

        # add ctx to DB
        core.ctx.add(ctx)

        # render: begin
        dispatch(RenderEvent(RenderEvent.STREAM_BEGIN, {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": False,
        }))

        # render: append input
        dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))

        # handle ctx name (generate title from summary if not initialized)
        if core.config.get('ctx.auto_summary'):
            controller.ctx.prepare_name(ctx)

        # get attachments
        files = core.attachments.get_all(mode)
        num_files = len(files)
        if num_files > 0:
            controller.chat.log(f"Attachments ({mode}): {num_files}")

        # generate image
        context = BridgeContext(
            ctx=ctx,
            mode=MODE_IMAGE,
            model=model_data,  # model instance
            prompt=text,
            attachments=files,
        )
        try:
            dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
                "id": "chat",
            }))
            dispatch(KernelEvent(KernelEvent.REQUEST, {
                'context': context,
                'extra': {
                    "num": num,
                    "image_id": image_id,  # pass previous image_id for variations
                    "video_id": video_id, # pass previous video_id for variations
                    "extra_prompt": extra_prompt,
                },
            }))
        except Exception as e:
            core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            update_status(trans('status.error'))
            dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                "id": "chat",
            }))
        return ctx

    @Slot(object, list, str)
    def handle_response(
            self,
            ctx: CtxItem,
            paths: List[str],
            prompt: str
    ):
        """
        Handle response

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        core = self.window.core
        dispatch = self.window.dispatch

        dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "img",
        }))
        string = ""
        i = 1
        urls = []
        ico_dir = os.path.join("%appdir%", "data", "icons")
        ico_download = os.path.join(ico_dir, "download.svg")
        ico_preview = os.path.join(ico_dir, "view.svg")
        for path in paths:
            safe_path = self.window.core.filesystem.make_local(path)
            """
            urls.append(f"![image]({ico_preview}) [**{trans('action.preview')}**]({safe_path})  "
                        f"![image]({ico_download})[**{trans('action.download')}**](bridge://download/{safe_path})")
            """
            urls.append(f"[**{trans('action.open')}**]({safe_path}) | "
                        f"[**{trans('action.download')}**](bridge://download/{safe_path})")
            i += 1
        string += "\n".join(urls)

        if not core.config.get('img_raw'):
            string += f"\nPrompt: {prompt}"

        local_urls = core.filesystem.make_local_list(paths)
        ctx.images = local_urls  # save images paths
        ctx.set_output(string.strip())

        # event: after context
        event = Event(Event.CTX_AFTER)
        event.ctx = ctx
        dispatch(event)

        # store last mode (in text mode this is handled in send_text)
        mode = core.config.get('mode')
        core.ctx.post_update(mode)  # post update context, store last mode, etc.
        core.ctx.store()  # save current ctx to DB
        self.window.update_status(trans('status.img.generated'))

        # update ctx in DB
        core.ctx.update_item(ctx)

        self.window.controller.chat.common.unlock_input()  # unlock input

    @Slot(object, list, str)
    def handle_response_inline(
            self,
            ctx: CtxItem,
            paths: List[str],
            prompt: str
    ):
        """
        Handle inline response

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch

        dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "img",
        }))
        string = ""
        i = 1
        for path in paths:
            string += f"{i}) `{path}`\n"
            i += 1

        local_urls = core.filesystem.make_local_list(paths)
        ctx.images = local_urls  # save images paths in ctx item here
        
        core.ctx.update_item(ctx)  # update in DB
        self.window.update_status(trans('status.img.generated'))  # update status

        # WARNING:
        # if internal (sync) mode, then re-send OK status response, if not, append only img result
        # it will only inform system that image was generated, user will see it in chat with image after render
        # of ctx item (link to images are appended to ctx item)
        if ctx.internal:
            ctx.results.append(
                {
                    "request": {
                        "cmd": "image",
                    },
                    "result": "OK. Generated {} image(s).".format(len(paths)),
                    "paths": paths,
                }
            )
            ctx.reply = False
            data = {
                "meta": ctx.meta,
                "ctx": ctx,
            }
            dispatch(RenderEvent(RenderEvent.EXTRA_APPEND, data))  # show image first
            dispatch(RenderEvent(RenderEvent.EXTRA_APPEND, data))  # end extra

            context = BridgeContext()
            context.ctx = ctx
            dispatch(KernelEvent(KernelEvent.REPLY_ADD, {
                'context': context,
                'extra': {
                    "flush": True,
                },
            }))
            controller.chat.common.unlock_input()  # unlock input
            dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, data))  # end of tool, hide spinner icon
            return

        # NOT internal-mode, user called, so append only img output to chat (show images now):
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        dispatch(RenderEvent(RenderEvent.EXTRA_APPEND, data))  # show image first
        dispatch(RenderEvent(RenderEvent.EXTRA_END, data))  # end extra

        controller.chat.common.unlock_input()  # unlock input
        dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, data))  # end of tool, hide spinner icon
