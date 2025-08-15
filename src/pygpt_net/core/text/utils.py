#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #


def output_html2text(html: str) -> str:
    """
    Convert output HTML to plain text

    :param html: HTML content
    :return: Plain text
    """
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup, NavigableString
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        # remove headers from code blocks
        for tag in soup.select('p.code-header-wrapper'):
            tag.replace_with(NavigableString('\n'))
        for tag in soup.select('span.ts, span.toggle-cmd-output, div.name-header'):
            tag.decompose()
        # add separators
        for tag in soup.select('div.msg-bot, div.msg-user'):
            tag.insert_before(NavigableString('\n\n'))
        for br in soup.select('.msg-user .msg p br'):
            br.replace_with('\n')
        text = soup.get_text(separator="", strip=False)
        return text.replace('\t', '    ')
    except Exception:
        pass
    return ""


def output_clean_html(html: str) -> str:
    """
    Clean output HTML content

    :param html: HTML content
    :return: HTML content
    """
    try:
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        # remove copy to clipboard from code blocks
        for tag in soup.select('a.code-header-copy'):
            tag.decompose()
        # remove action icons
        for tag in soup.select('div.action-icons'):
            tag.decompose()
        return str(soup)
    except Exception:
        pass
    return html


def has_unclosed_code_tag(text: str) -> bool:
    """
    Check if HTML content has unclosed code block

    :param text: HTML content
    :return: True if unclosed code block found
    """
    if not text:
        return False
    return (text.count('```') % 2) != 0