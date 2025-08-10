#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 00:00:00                  #
# ================================================== #

import os

import markdown
from mdx_math import MathExtension
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
        self.block_idx = 1
        # self._soup_parser = "lxml"
        self._soup_parser = "html.parser"
        self._soup_parser_checked = False
        self._icon_base = None
        self._icon_paths = None

    def _make_soup(self, html: str) -> BeautifulSoup:
        """
        Create BeautifulSoup instance from HTML string

        :param html: HTML string to parse
        :return: BeautifulSoup instance
        """
        return BeautifulSoup(html, self._soup_parser)

    def _get_icon_paths(self) -> dict:
        """
        Get icon paths for the parser

        :return: dictionary of icon paths
        """
        app_path = self.window.core.config.get_app_path()
        if app_path != self._icon_base or not self._icon_paths:
            join = os.path.join
            self._icon_paths = {
                "copy": join(app_path, "data", "icons", "copy.svg"),
                "preview": join(app_path, "data", "icons", "view.svg"),
                "run": join(app_path, "data", "icons", "play.svg"),
                "collapse": join(app_path, "data", "icons", "menu.svg"),
            }
            self._icon_base = app_path
        return self._icon_paths

    def init(self):
        """Initialize markdown parser"""
        if self.md is None:
            self.md = markdown.Markdown(extensions=[
                'fenced_code',
                'tables',
                'sane_lists',
                MathExtension(enable_dollar_delimiter=False)  # math formulas
            ])
            # disable code blocks parsing (without ` and ```)
            if 'code' in self.md.parser.blockprocessors:
                self.md.parser.blockprocessors.deregister('code')

    def reset(self):
        """
        Reset parser
        """
        self.block_idx = 1

    def get_code_blocks(self):
        """
        Get code blocks

        :return: code blocks
        """
        return {}

    def prepare_paths(self, text: str) -> str:
        """
        Prepare paths in markdown text

        :param text: markdown text
        :return: markdown text with prepared paths
        """
        # Replace sandbox paths with file paths
        return text.replace("](sandbox:", "](file://") if "](sandbox:" in text else text

    def parse(self, text: str) -> str:
        """
        Parse markdown text

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        try:
            text = (text or "").strip()
            if not text:
                return ""

            text = self.prepare_paths(text)
            html = self.md.convert(text)
            self.md.reset()

            soup = self._make_soup(html)
            self.strip_whitespace_lists(soup)
            self.strip_whitespace_codeblocks(soup)
            self.highlight_code_blocks(soup)
            self.format_images(soup)

            result = str(soup)
            soup.decompose()
            return result
        except Exception:
            return text

    def parse_code(self, text: str) -> str:
        """
        Parse code markdown text

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        try:
            soup = self._make_soup(self.md.convert(text.strip()))
            self.md.reset()
            self.strip_whitespace_lists(soup)  # strip whitespace from codeblocks
            self.strip_whitespace_codeblocks(soup)  # strip whitespace from codeblocks
            self.highlight_code_blocks(soup)  # parse code blocks
            result = str(soup)
            soup.decompose()
            return result
        except Exception as e:
            pass
        return text

    def to_plain_text(self, html: str) -> str:
        """
        Convert markdown to plain text

        :param html: html text
        :return: plain text
        """
        soup = self._make_soup(html)
        text = soup.get_text()
        soup.decompose()
        return text

    def strip_whitespace_codeblocks(self, soup):
        """
        Strip whitespace from codeblocks

        :param soup: BeautifulSoup instance
        """
        for el in soup.find_all('code'):
            el.string = el.string.strip()

    def strip_whitespace_lists(self, soup):
        """
        Strip whitespace from lists

        :param soup: BeautifulSoup instance
        """
        for li in soup.find_all('li'):
            for item in li.contents:
                if isinstance(item, NavigableString) and item.strip() == '':
                    item.replace_with('')

    def parse_code_blocks(self, soup: BeautifulSoup):
        """
        Add copy code button to code blocks (without syntax highlighting)

        :param soup: BeautifulSoup instance
        """
        t_copy = trans('ctx.extra.copy_code')

        for el in soup.find_all('pre'):
            content = el.get_text()
            if not content or not content.strip():
                continue

            header = soup.new_tag('p', **{'class': "code-header-wrapper"})
            link_wrapper = soup.new_tag('span')

            a = soup.new_tag('a', href=f'extra-code-copy:{self.block_idx}')  # extra action link
            a['class'] = "code-header-copy"
            a.string = t_copy

            code_tag = el.find('code')
            language = ""
            if code_tag and code_tag.has_attr('class'):
                classes = code_tag.get('class', [])
                if classes:
                    first = classes[0]
                    if isinstance(first, str):
                        language = first

            if language:
                lang = soup.new_tag('span', **{'class': "code-header-lang"})
                lang.string = language.replace('language-', '') + "   "
                link_wrapper.append(lang)

            link_wrapper.append(a)
            header.append(link_wrapper)

            wrapper = soup.new_tag('div', **{'class': "code-wrapper"})
            wrapper['data-index'] = str(self.block_idx)

            new_code = soup.new_tag('code')
            new_pre = soup.new_tag('pre')
            new_code.string = content
            new_pre.append(new_code)
            wrapper.append(header)
            wrapper.append(new_pre)

            el.replace_with(wrapper)
            self.block_idx += 1

    def highlight_code_blocks(self, soup: BeautifulSoup):
        """
        Add copy code button to code blocks (with syntax highlighting)

        :param soup: BeautifulSoup instance
        """
        icons = self._get_icon_paths()

        t_copy = trans('ctx.extra.copy_code')
        t_collapse = trans('ctx.extra.collapse')
        t_expand = trans('ctx.extra.expand')
        t_copied = trans('ctx.extra.copied')
        t_preview = trans('ctx.extra.preview')
        t_run = trans('ctx.extra.run')

        style = self.window.core.config.get("render.code_syntax") or "default"

        for el in soup.find_all('pre'):
            content = el.get_text()
            if not content or not content.strip():
                continue

            header = soup.new_tag('p', **{'class': "code-header-wrapper"})
            link_wrapper = soup.new_tag('span')

            code_tag = el.find('code')
            language = ""
            if code_tag:
                classes = code_tag.get('class', [])
                for cls in classes or []:
                    if isinstance(cls, str) and cls.startswith('language-'):
                        language = cls.split('-', 1)[1]
                        break

            is_output = (language == "output")
            if is_output:
                language = "python"
                if code_tag is not None:
                    code_tag['class'] = "language-python"

            lang_span = soup.new_tag('span', **{'class': "code-header-lang"})
            if language:
                lang_span.string = ("output" if is_output else language) + "   "
            else:
                lang_span.string = "code "
            link_wrapper.append(lang_span)

            if language == 'html':
                preview = soup.new_tag('a', href=f'empty:{self.block_idx}')
                preview['class'] = "code-header-action code-header-preview"
                preview.string = t_preview
                preview_icon = soup.new_tag('img', src=icons["preview"], **{'class': "action-img"})
                preview.insert(0, preview_icon)
                link_wrapper.append(preview)
            elif language == 'python' and not is_output:
                run = soup.new_tag('a', href=f'empty:{self.block_idx}')
                run['class'] = "code-header-action code-header-run"
                run.string = t_run
                run_icon = soup.new_tag('img', src=icons["run"], **{'class': "action-img"})
                run.insert(0, run_icon)
                link_wrapper.append(run)

            # collapse
            collapse = soup.new_tag('a', href=f'empty:{self.block_idx}')
            collapse['class'] = "code-header-action code-header-collapse"
            collapse_span = soup.new_tag('span')
            collapse_span.string = t_collapse
            collapse_icon = soup.new_tag('img', src=icons["collapse"], **{'class': "action-img"})
            collapse.insert(0, collapse_icon)
            collapse.append(collapse_span)

            # copy
            copy = soup.new_tag('a', href=f'empty:{self.block_idx}')
            copy['class'] = "code-header-action code-header-copy"
            copy_span = soup.new_tag('span')
            copy_span.string = t_copy
            copy_icon = soup.new_tag('img', src=icons["copy"], **{'class': "action-img"})
            copy.insert(0, copy_icon)
            copy.append(copy_span)

            link_wrapper.append(collapse)
            link_wrapper.append(copy)
            header.append(link_wrapper)

            # wrapper
            wrapper = soup.new_tag('div', **{'class': "code-wrapper highlight"})
            wrapper['data-index'] = str(self.block_idx)
            wrapper['data-locale-collapse'] = t_collapse
            wrapper['data-locale-expand'] = t_expand
            wrapper['data-locale-copy'] = t_copy
            wrapper['data-locale-copied'] = t_copied
            wrapper['data-style'] = style

            pre = soup.new_tag('pre')
            code_new = soup.new_tag('code')
            if language:
                code_new['class'] = 'language-' + language
            code_new.string = content
            pre.append(code_new)

            wrapper.append(header)
            wrapper.append(pre)
            el.replace_with(wrapper)
            self.block_idx += 1

    def convert_lists_to_paragraphs(self, soup: BeautifulSoup):
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

    def convert_list(self, soup: BeautifulSoup, list_element, ordered=False):
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

    def format_images(self, soup: BeautifulSoup):
        """
        Add width to img tags

        :param soup: BeautifulSoup instance
        """
        for img in soup.find_all('img'):
            img['width'] = "400"
