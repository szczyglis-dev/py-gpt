#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.06 19:00:00                  #
# ================================================== #

import re


def output_html2text(html: str) -> str:
    """
    Convert output HTML to plain text

    :param html: HTML content
    :return: Plain text
    """
    from bs4 import BeautifulSoup
    if html == "":
        return ""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # remove headers from code blocks
        for tag in soup.find_all('p', class_='code-header-wrapper'):
            empty = soup.new_tag('p')
            empty.string = '\n'
            tag.replace_with(empty)
        for tag in soup.find_all('span', class_='ts'):
            empty = soup.new_tag('span')
            empty.string = ''
            tag.replace_with(empty)
        for tag in soup.find_all('div', class_='name-header'):
            empty = soup.new_tag('span')
            empty.string = ''
            tag.replace_with(empty)
        for tag in soup.find_all('span', class_='toggle-cmd-output'):
            empty = soup.new_tag('span')
            empty.string = ''
            tag.replace_with(empty)        
        # add separators
        for tag in soup.find_all('div', class_='msg-bot'):
            sep = soup.new_tag('p')
            sep.string = '\n\n'
            tag.insert_before(sep)
        for p in soup.select('.msg-user .msg p'):
            for br in p.find_all('br'):
                br.replace_with("\n")
        for tag in soup.find_all('div', class_='msg-user'):
            sep = soup.new_tag('p')
            sep.string = '\n\n'
            tag.insert_before(sep)
        text = soup.get_text(separator="", strip=False)
        return text.replace('\t', '    ')
    except Exception as e:
        pass
    return ""

def output_clean_html(html: str) -> str:
    """
    Clean output HTML content

    :param html: HTML content
    :return: HTML content
    """
    from bs4 import BeautifulSoup
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
    code_blocks = re.findall(r'```', text)
    if len(code_blocks) % 2 != 0:
        return True
    return False