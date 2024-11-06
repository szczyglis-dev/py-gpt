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

import markdown
from bs4 import BeautifulSoup
from bs4.element import NavigableString

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
        Parse markdown text

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        try:
            html = self.md.convert(text.strip())
            soup = BeautifulSoup(html, 'html.parser')
            self.strip_whitespace_lists(soup)  # strip whitespace from codeblocks
            if self.window.core.config.get("ctx.convert_lists"):
                self.convert_lists_to_paragraphs(soup)  # convert lists to paragraphs
            self.strip_whitespace_codeblocks(soup)  # strip whitespace from codeblocks
            self.parse_code_blocks(soup)  # parse code blocks
            self.format_images(soup)  # add width to img tags
            text = " " + str(soup) + " "
        except Exception as e:
            pass
        return text

    def strip_whitespace_lists(self, soup):
        """
        Strip whitespace from lists

        :param soup: BeautifulSoup instance
        """
        for li in soup.find_all('li'):
            for item in li.contents:
                if isinstance(item, NavigableString) and item.strip() == '':
                    item.replace_with('')

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
            content = el.get_text(strip=True)
            self.code_blocks[self.block_idx] = content

            header = soup.new_tag('div', **{'class': "code-header-wrapper"})
            link_wrapper = soup.new_tag('div')
            a = soup.new_tag('a', href=f'extra-code-copy:{self.block_idx}')  # extra action link
            a['class'] = "code-header-copy"
            a.string = trans('ctx.extra.copy_code')

            code = el.find('code')
            language = code['class'][0] if code.has_attr('class') else ''
            if language:
                lang = soup.new_tag('span', **{'class': "code-header-lang"})
                lang['class'] = "code-header-lang"
                lang.string = language.replace('language-', '') + "   "
                link_wrapper.append(lang)

            link_wrapper.append(a)
            header.append(link_wrapper)
            wrapper = soup.new_tag('div', **{'class': "code-wrapper"})
            wrapper.append(header)

            new_pre = soup.new_tag('code')
            new_code = soup.new_tag('div')
            new_pre.string = content
            new_code.append(new_pre)
            wrapper.append(new_code)
            el.replace_with(wrapper)

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
