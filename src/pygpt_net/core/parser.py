#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 04:00:00                  #
# ================================================== #

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import xml.etree.ElementTree as etree


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
            # UnorderedListToParagraphExtension() <- convert <li> to <p>, it allows copy lists from QTextBrowser via
            # Ctrl+C (HTML list-bullets are not copied)
            self.md = markdown.Markdown(extensions=[UnorderedListToParagraphExtension(), 'fenced_code'])

    def parse(self, text: str) -> str:
        """
        Convert markdown to html

        :param text: markdown text
        :return: html formatted text
        """
        self.init()
        return self.md.convert(text.strip())


class UnorderedListToParagraphProcessor(Treeprocessor):
    def run(self, root):
        """
        Convert ul to p
        :param root: Root element
        """
        self.convert_ul_to_paragraphs(root)

    def convert_ul_to_paragraphs(self, element):
        """
        Convert ul to p

        :param element: Element
        """
        for child in list(element):
            if child.tag == 'ul':
                self.handle_ul(element, child)
            elif child.tag == 'ol':
                self.handle_ol(element, child)
            else:
                self.convert_ul_to_paragraphs(child)

    def handle_ul(self, parent, ul_element):
        """
        Handle ul element

        :param parent: Parent element
        :param ul_element: Ul element
        """
        for li in list(ul_element):
            p = etree.Element('p')
            p.set('class', 'list')  # styled in css
            p.text = "- " + (li.text if li.text is not None else "")
            parent.append(p)
            self.convert_ul_to_paragraphs(li)
        parent.remove(ul_element)

    def handle_ol(self, parent, ol_element):
        """
        Handle ol element
        :param parent: Parent element
        :param ol_element: Ol element
        """
        i = 1
        for li in list(ol_element):
            p = etree.Element('p')
            p.set('class', 'list')  # styled in css
            p.text = f"{i}. " + (li.text if li.text is not None else "")
            i += 1
            parent.append(p)
            self.convert_ul_to_paragraphs(li)
        parent.remove(ol_element)


class UnorderedListToParagraphExtension(Extension):
    def extendMarkdown(self, md):
        """
        Markdown extension, convert ul to p

        :param md: Markdown instance
        """
        ul_to_p = UnorderedListToParagraphProcessor(md)
        md.treeprocessors.register(ul_to_p, 'ul_to_p', 25)