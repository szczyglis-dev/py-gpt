#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 15:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Idx:
    def __init__(self, window=None):
        """
        Idx controller

        :param window: Window instance
        """
        self.window = window

    def send(self, text: str) -> CtxItem:
        """
        Send prompt for image generate

        :param text: prompt for image generation
        :return: ctx item
        """
        # get mode
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        sys_prompt = self.window.core.config.get('prompt')

        # create ctx item
        ctx = CtxItem()
        ctx.current = True  # mark as current context item
        ctx.mode = mode
        ctx.model = model

        # create ctx item
        ctx = CtxItem()
        ctx.set_input(text, self.window.core.config.get('user_name'))

        # event: ctx.before
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        # process events to update UI
        QApplication.processEvents()

        # render: begin
        self.window.controller.chat.render.begin(stream=False)

        # append text from input to chat window
        self.window.controller.chat.render.append_input(ctx)

        # add ctx to DB here and only update it after response, MUST BE REMOVED NEXT AS FIRST MSG (LAST ON LIST)!
        self.window.core.ctx.add(ctx)

        # update ctx list, but not reload all to prevent focus out on lists
        self.window.controller.ctx.update(reload=True, all=False)

        # process events to update UI
        QApplication.processEvents()

        try:
            # make query to llama index
            try:
                self.window.controller.chat.common.lock_input()  # lock input
                idx = self.window.controller.idx.current_idx
                ctx.output = self.window.core.idx.query(ctx.input, idx=idx, model=model, sys_prompt=sys_prompt)  # query

                # update context in DB
                ctx.current = False  # reset current state
                self.window.core.ctx.update_item(ctx)

            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))
                self.window.ui.status(trans('status.error'))
                print("Error when querying Llama-index: " + str(e))

            self.window.controller.chat.output.handle(ctx, mode, False)

        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))
            self.window.ui.status(trans('status.error'))
            print("Error in sending query: " + str(e))

        # render: end
        self.window.controller.chat.render.end(stream=False)

        self.window.controller.chat.common.unlock_input()  # unlock

        # handle ctx name (generate title from summary if not initialized)
        if self.window.core.config.get('ctx.auto_summary'):
            self.window.controller.ctx.prepare_name(ctx)

        return ctx
