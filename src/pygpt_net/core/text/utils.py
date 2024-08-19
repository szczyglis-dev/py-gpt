#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 07:00:00                  #
# ================================================== #

import re

from bs4 import BeautifulSoup


def output_html2text(html: str) -> str:
    """
    Convert output HTML to plain text

    :param html: HTML content
    :return: Plain text
    """
    if html == "":
        return ""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # remove headers from code blocks
        for tag in soup.find_all('p', class_='code-header-wrapper'):
            empty = soup.new_tag('p')
            empty.string = '\n'
            tag.replace_with(empty)
        # add separators
        for tag in soup.find_all('div', class_='msg-bot'):
            sep = soup.new_tag('p')
            sep.string = '\n\n'
            tag.insert_before(sep)
        for tag in soup.find_all('div', class_='msg-user'):
            sep = soup.new_tag('p')
            sep.string = '\n\n'
            tag.insert_before(sep)
        return soup.get_text()
    except Exception as e:
        pass
    return ""

def output_clean_html(html: str) -> str:
    """
    Clean output HTML content

    :param html: HTML content
    :return: HTML content
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # remove copy to clipboard from code blocks
        for tag in soup.find_all('a', class_='code-header-copy'):
            tag.decompose()
        # remove action icons
        for tag in soup.find_all('div', class_='action-icons'):
            tag.decompose()
        return str(soup)
    except Exception as e:
        pass
    return html

def has_unclosed_code_tag(text: str) -> bool:
    """
    Check if HTML content has unclosed code block

    :param text: HTML content
    :return: True if unclosed code block found
    """
    if text is None:
        return False
    if re.search(r'```(?!.*```)', text):
        return True
    return False