#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Optional, List, Dict

from pygpt_net.utils import trans


class Body:

    def __init__(self, window=None):
        """
        Plain-text body

        :param window: Window instance
        """
        self.window = window

    def get_image_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
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
        return """\n{prefix}{num}: {path}\n""". \
            format(prefix=trans('chat.prefix.img'),
                   path=path,
                   num=num_str)

    def get_url_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get URL HTML

        :param url: external URL
        :param num: number of URL
        :param num_all: number of all URLs
        :return: HTML
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        return """{prefix}{num}: {url}""". \
            format(prefix=trans('chat.prefix.url'),
                   url=url,
                   num=num_str)

    def get_docs_html(self, docs: List[Dict]) -> str:
        """
        Get Llama-index doc metadata HTML

        :param docs: list of document metadata
        :return: HTML code
        """
        html = ""
        html_sources = ""
        num = 1
        max = 3
        try:
            for item in docs:
                for uuid, doc_json in item.items():
                    """
                    Example doc (file metadata):
                    {'a2c7af6d-3c34-4c28-bf2d-6161e7fb525e': {
                        'file_path': '/home/user/.config/pygpt-net/data/my_cars.txt',
                        'file_name': '/home/user/.config/pygpt-net/data/my_cars.txt', 'file_type': 'text/plain',
                        'file_size': 28, 'creation_date': '2024-03-03', 'last_modified_date': '2024-03-03',
                        'last_accessed_date': '2024-03-03'}}
                    """
                    doc_parts = []
                    for key in doc_json:
                        doc_parts.append("{}: {}".format(key, doc_json[key]))
                    html_sources += "\n[{}] {}: {}".format(num, uuid, ", ".join(doc_parts))
                    num += 1
                if num >= max:
                    break
        except Exception as e:
            pass

        if html_sources != "":
            html += "\n----------\n{prefix}:\n".format(prefix=trans('chat.prefix.doc'))
            html += html_sources
        return html

    def get_file_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get file HTML

        :param url: URL to file
        :param num: number of file
        :param num_all: number of all files
        :return: HTML
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """\n{prefix}{num}: {path}\n""". \
            format(prefix=trans('chat.prefix.file'),
                   path=path,
                   num=num_str)
