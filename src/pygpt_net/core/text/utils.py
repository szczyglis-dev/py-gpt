#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.07 05:00:00                  #
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
        # remove scripts
        for tag in soup.select('script'):
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
    return False
    if not text:
        return False
    return (text.count('```') % 2) != 0

def elide_filename(name_or_path: str, max_len: int = 45, ellipsis: str = "...", keep_dir: bool = False) -> str:
    """
    Elide a long filename by replacing the middle with an ellipsis, preserving the extension.

    Args:
        name_or_path: Filename or full path.
        max_len: Maximum length of the resulting string (including extension and ellipsis).
        ellipsis: Ellipsis text to insert (e.g., "...").
        keep_dir: If True and a path is provided, keep the directory prefix and elide only the basename.
                  If False, operate on the basename only.

    Returns:
        Elided filename (or path if keep_dir=True).
    """
    import os

    if max_len <= 0:
        return name_or_path

    dirpart, base = os.path.split(name_or_path) if keep_dir else ("", os.path.basename(name_or_path))
    stem, ext = os.path.splitext(base)

    # if already short enough
    if len(base) <= max_len:
        return os.path.join(dirpart, base) if keep_dir else base

    # minimal sanity for very small max_len
    min_needed = len(ext) + len(ellipsis) + 2  # at least 1 char head + 1 char tail
    if max_len < min_needed:
        # degrade gracefully: keep first char, ellipsis, last char, and as much ext as fits
        head = stem[:1] if stem else ""
        tail = stem[-1:] if len(stem) > 1 else ""
        # if ext is too long, trim it (rare edge case)
        ext_trim = ext[: max(0, max_len - len(head) - len(ellipsis) - len(tail))]
        out = f"{head}{ellipsis}{tail}{ext_trim}"
        return os.path.join(dirpart, out) if keep_dir else out

    # compute available budget for visible stem parts
    avail = max_len - len(ext) - len(ellipsis)
    # split budget between head and tail (favor head slightly)
    head_len = (avail + 1) // 2
    tail_len = avail - head_len

    # guardrails
    head_len = max(1, head_len)
    tail_len = max(1, tail_len)

    # build elided name
    head = stem[:head_len]
    tail = stem[-tail_len:] if tail_len <= len(stem) else stem
    out = f"{head}{ellipsis}{tail}{ext}"
    return os.path.join(dirpart, out) if keep_dir else out