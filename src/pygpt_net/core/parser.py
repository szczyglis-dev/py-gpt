#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 12:00:00                  #
# ================================================== #

import markdown
from bs4 import BeautifulSoup


class Parser:

    def __init__(self, window=None):
        """
        Markdown parser core

        :param window: Window instance
        """
        self.window = window
        self.md = None

    def init(self):
        """
        Initialize markdown parser
        """
        if self.md is None:
            self.md = markdown.Markdown(extensions=['fenced_code'])

    def parse(self, text: str) -> str:
        """
        Convert markdown to html and then convert lists to paragraphs using BeautifulSoup

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        html = self.md.convert(text.strip())
        soup = BeautifulSoup(html, 'html.parser')
        self.convert_lists_to_paragraphs(soup)
        return str(soup)

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
            p.string = f"{prefix}{li.get_text()}"
            list_element.insert_before(p)
