#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Preview dispatch. Register additional readers before TextReader (e.g. archives)."""
import mimetypes
from pathlib import Path


class ImageReader:
    kind = 'image'

    def accepts(self, path):
        return Path(path).suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico', '.tif', '.tiff'}


class MediaReader:
    kind = 'media'

    def accepts(self, path):
        mime = mimetypes.guess_type(path)[0] or ''
        return mime.startswith(('audio/', 'video/'))


class TextReader:
    kind = 'text'
    max_bytes = 4 * 1024 * 1024

    def accepts(self, path):
        try:
            self.read(path)
            return True
        except (OSError, UnicodeError, ValueError):
            return False

    def read(self, path):
        with open(path, 'rb') as stream:
            data = stream.read(self.max_bytes + 1)
        if len(data) > self.max_bytes:
            raise ValueError('File too large for the text preview')
        encoding = 'utf-8'
        if data.startswith((b'\xff\xfe', b'\xfe\xff')):
            encoding = 'utf-16'
        elif data.startswith(b'\xef\xbb\xbf'):
            encoding = 'utf-8-sig'
        text = data.decode(encoding)
        if any(ord(c) < 32 and c not in '\n\r\t\f' for c in text):
            raise ValueError('Binary file')
        return text, encoding


class MarkdownReader:
    kind = 'markdown'

    def accepts(self, path):
        return Path(path).suffix.lower() in {'.md', '.markdown'}


class ReaderRegistry:
    def __init__(self):
        self.readers = [ImageReader(), MediaReader(), MarkdownReader(), TextReader()]

    def register(self, reader):
        self.readers.insert(0, reader)

    def resolve(self, path):
        return next((reader for reader in self.readers if reader.accepts(path)), None)
