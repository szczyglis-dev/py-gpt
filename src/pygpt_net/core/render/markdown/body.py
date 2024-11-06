#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

import os

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Body:

    def __init__(self, window=None):
        """
        Markdown Body

        :param window: Window instance
        """
        self.window = window
        self.img_width = 400

    def get_image_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get image HTML

        :param url: URL to image
        :param num: number of image
        :param num_all: number of all images
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """<a href="{url}"><img src="{path}" width="{img_width}" class="image"></a>
        <p><b>{prefix}{num}:</b> <a href="{url}">{path}</a></p>""". \
            format(prefix=trans('chat.prefix.img'),
                   url=url,
                   path=path,
                   img_width=self.img_width,
                   num=num_str)

    def get_url_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get URL HTML

        :param url: external URL
        :param num: number of URL
        :param num_all: number of all URLs
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        return """<b>{prefix}{num}:</b> <a href="{url}">{url}</a>""". \
            format(prefix=trans('chat.prefix.url'),
                   url=url,
                   num=num_str)

    def get_docs_html(self, docs: list) -> str:
        """
        Get Llama-index doc metadata HTML

        :param docs: list of document metadata
        :return: HTML code
        """
        html = ""
        html_sources = ""
        num = 1
        for doc_json in docs:
            try:
                """
                Example doc (file metadata):
                {'a2c7af6d-3c34-4c28-bf2d-6161e7fb525e': {
                    'file_path': '/home/user/.config/pygpt-net/data/my_cars.txt',
                    'file_name': '/home/user/.config/pygpt-net/data/my_cars.txt', 'file_type': 'text/plain',
                    'file_size': 28, 'creation_date': '2024-03-03', 'last_modified_date': '2024-03-03',
                    'last_accessed_date': '2024-03-03'}}
                """
                doc_id = list(doc_json.keys())[0]
                doc_parts = []
                for key in doc_json[doc_id]:
                    doc_parts.append("<b>{}:</b> {}".format(key, doc_json[doc_id][key]))
                html_sources += "[{}] {}: {}".format(num, doc_id, ", ".join(doc_parts))
                num += 1
            except Exception as e:
                pass

        if html_sources != "":
            html += "<p><b>{prefix}:</b></p>".format(prefix=trans('chat.prefix.doc'))
            html += "<div class=\"cmd\">"
            html += "<p>" + html_sources + "</p>"
            html += "</div> "
        return html

    def get_file_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get file HTML

        :param url: URL to file
        :param num: number of file
        :param num_all: number of all files
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """<div><b>{prefix}{num}:</b> <a href="{url}">{path}</a></div>""". \
            format(prefix=trans('chat.prefix.file'),
                   url=url,
                   path=path,
                   num=num_str)

    def get_action_icons(self, ctx: CtxItem, all: bool = False) -> list:
        """
        Get action icons for context item

        :param ctx: context item
        :param all: True to show all icons
        :return: list of icons
        """
        icons = []

        # audio read
        if ctx.output is not None and ctx.output != "":
            icons.append(
                '<a href="extra-audio-read:{}"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    self.get_icon("audio", trans("ctx.extra.audio"))
                )
            )
            # copy ctx
            icons.append(
                '<a href="extra-copy:{}"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    self.get_icon("copy", trans("ctx.extra.copy"))
                )
            )
            # regen link
            icons.append(
                '<a href="extra-replay:{}"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    self.get_icon("reload", trans("ctx.extra.reply"))
                )
            )
            if all:
                # edit link
                icons.append(
                    '<a href="extra-edit:{}"><span class="cmd">{}</span></a>'.format(
                        ctx.id,
                        self.get_icon("edit", trans("ctx.extra.edit"))
                    )
                )
                # delete link
                icons.append(
                    '<a href="extra-delete:{}"><span class="cmd">{}</span></a>'.format(
                        ctx.id,
                        self.get_icon("delete", trans("ctx.extra.delete"))
                    )
                )

                # join link
                if not self.window.core.ctx.is_first_item(ctx.id):
                    icons.append(
                        '<a href="extra-join:{}"><span class="cmd">{}</span></a>'.format(
                            ctx.id,
                            self.get_icon("join", trans("ctx.extra.join"))
                        )
                    )
        return icons

    def get_icon(self, icon: str, title: str = None) -> str:
        """
        Get icon

        :param icon: icon name
        :param title: icon title
        :return: icon HTML
        """
        icon = os.path.join(self.window.core.config.get_app_path(), "data", "icons", "chat", icon + ".png")
        return '<img src="{}" width="20" height="20" title="{}" alt="{}">'.format(icon, title, title)
        # return '<img src=":/icons/{}.svg" width="25" title="{}">'.format(icon, title)
