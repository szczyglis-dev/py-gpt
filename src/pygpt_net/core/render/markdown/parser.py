#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.11 22:00:00                  #
# ================================================== #

import markdown
from bs4 import BeautifulSoup

from pygpt_net.utils import trans


class Parser:

    def __init__(self, window=None):
        """
        Markdown parser core

        :param window: Window instance
        """
        self.window = window
        self.md = None
        self.code_blocks = {}
        self.block_idx = 1

    def init(self):
        """
        Initialize markdown parser
        """
        if self.md is None:
            self.md = markdown.Markdown(extensions=['fenced_code'])

    def reset(self):
        """
        Reset parser
        """
        self.code_blocks = {}
        self.block_idx = 1

    def get_code_blocks(self):
        """
        Get code blocks

        :return: code blocks
        """
        return self.code_blocks

    def parse(self, text: str) -> str:
        """
        Convert markdown to html and then convert lists to paragraphs using BeautifulSoup

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        try:
            html = self.md.convert(text.strip())
            soup = BeautifulSoup(html, 'html.parser')
            self.convert_lists_to_paragraphs(soup)  # convert lists to paragraphs
            self.strip_whitespace_codeblocks(soup)  # strip whitespace from codeblocks
            if self.window.core.config.get('ctx.copy_code'):
                self.parse_code_blocks(soup)  # parse code blocks
            self.format_images(soup)  # add width to img tags
            text = str(soup)
        except Exception as e:
            pass
        return text

    def strip_whitespace_codeblocks(self, soup):
        """
        Strip whitespace from codeblocks

        :param soup: BeautifulSoup instance
        """
        for el in soup.find_all('code'):
            el.string = el.string.strip()

    def parse_code_blocks(self, soup):
        """
        Add copy code button to code blocks

        :param soup: BeautifulSoup instance
        """
        for el in soup.find_all('pre'):
            header = soup.new_tag('a', href='extra-code-copy:{}'.format(self.block_idx))
            header['class'] = "code-copy"
            header.string = trans('ctx.extra.copy_code')
            el['id'] = f"code-{self.block_idx}"
            el.string = el.string.strip()
            el.insert_before(header)
            self.code_blocks[self.block_idx] = el.string
            self.block_idx += 1

    def convert_lists_to_paragraphs(self, soup):
        """
        Convert lists to paragraphs

        :param soup: BeautifulSoup instance
        """
        for ul in soup.find_all('ul'):
            self.convert_list(soup, ul, ordered=False)
        for ol in soup.find_all('ol'):
            self.convert_list(soup, ol, ordered=True)

        for element in soup.find_all(['ul', 'ol']):
            element.decompose()

    def convert_list(self, soup, list_element, ordered=False):
        """
        Convert list to paragraphs

        :param soup: BeautifulSoup instance
        :param list_element: Element to convert
        :param ordered: Is ordered list
        """
        list_items = list_element.find_all('li')
        for index, li in enumerate(list_items, start=1):
            p = soup.new_tag('p')
            p['class'] = "list"
            prefix = f"{index}. " if ordered else "- "
            p.string = f"{prefix}{li.get_text().strip()}"
            list_element.insert_before(p)

    def format_images(self, soup):
        """
        Add width to img tags

        :param soup: BeautifulSoup instance
        """
        images = soup.find_all('img')
        for index, img in enumerate(images):
            img['width'] = "400"
