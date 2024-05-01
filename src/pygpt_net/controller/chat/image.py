#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

from PySide6.QtWidgets import  QApplication

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event
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
            prev_ctx: CtxItem = None,
            parent_id: int = None,
    ) -> CtxItem:
        """
        Send prompt for image generate

        :param text: prompt for image generation
        :param prev_ctx: previous ctx item
        :param parent_id: parent ctx id
        :return: ctx item
        """
        num = int(self.window.ui.config['global']['img_variants'].input.text() or 1)
        if num < 1:
            num = 1
        elif num > 4:
            num = 4

        # force 1 image if dall-e-3 model is used
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)
        if model_data.id == 'dall-e-3':
            num = 1

        self.window.ui.status(trans('status.sending'))

        # create ctx item
        ctx = CtxItem()
        ctx.set_input(text, self.window.core.config.get('user_name'))
        ctx.prev_ctx = prev_ctx  # store previous context item

        # event: context before
        event = Event(Event.CTX_BEFORE)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # add ctx to DB
        self.window.core.ctx.add(ctx)
        self.window.controller.chat.render.append_input(ctx)

        # process events to update UI
        QApplication.processEvents()

        # handle ctx name (generate title from summary if not initialized)
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.ctx.prepare_name(ctx)

        # generate image
        bridge_context = BridgeContext(
            ctx=ctx,
            mode="image",
            model=model_data,  # model instance
            prompt=text,
        )
        extra = {
            "num": num,
        }
        try:
            self.window.core.bridge.call(
                context=bridge_context,
                extra=extra,
            )
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            self.window.ui.status(trans('status.error'))

        return ctx

    def handle_response(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle response

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        string = ""
        i = 1
        for path in paths:
            string += "{}) `{}`".format(i, path) + "\n"
            i += 1

        if self.window.core.config.get('img_dialog_open'):
            self.window.tools.get("viewer").open_images(paths)  # use viewer tool

        if not self.window.core.config.get('img_raw'):
            string += "\nPrompt: "
            string += prompt

        local_urls = self.window.core.filesystem.make_local_list(paths)
        ctx.images = local_urls  # save images paths
        ctx.set_output(string.strip())

        # event: after context
        event = Event(Event.CTX_AFTER)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # store last mode (in text mode this is handled in send_text)
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.
        self.window.controller.chat.render.append_output(ctx)
        self.window.core.ctx.store()  # save current ctx to DB
        self.window.ui.status(trans('status.img.generated'))

        # update ctx in DB
        self.window.core.ctx.update_item(ctx)

        # append extra output to chat
        self.window.controller.chat.render.append_extra(ctx)
        self.window.controller.chat.render.end_extra()

        self.window.stateChanged.emit(self.window.STATE_IDLE)  # set state to idle

    def handle_response_inline(self, ctx: CtxItem, paths: list, prompt: str):
        """
        Handle inline response

        :param ctx: ctx item
        :param paths: list with paths to downloaded images
        :param prompt: prompt used to generate images
        """
        string = ""
        i = 1
        for path in paths:
            string += "{}) `{}`".format(i, path) + "\n"
            i += 1

        local_urls = self.window.core.filesystem.make_local_list(paths)
        ctx.images = local_urls  # save images paths in ctx item here
        self.window.core.ctx.update_item(ctx)  # update in DB
        self.window.ui.status(trans('status.img.generated'))  # update status

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
            ctx.reply = True
            self.window.controller.chat.render.append_extra(ctx)  # show image first
            self.window.controller.chat.render.end_extra()
            self.window.core.dispatcher.reply(ctx, flush=True)
            return

        # NOT internal-mode, user called, so append only img output to chat (show images now)
        self.window.controller.chat.render.append_extra(ctx)
        self.window.controller.chat.render.end_extra()

        self.window.stateChanged.emit(self.window.STATE_IDLE)  # set state to idle
