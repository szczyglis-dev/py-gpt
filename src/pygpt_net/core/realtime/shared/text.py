#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import re

def coalesce_text(parts):
    """Merge text parts, preserving intentional newlines and fixing spaces."""
    if not parts:
        return ""
    out = []
    for piece in parts:
        if not piece:
            continue
        s = str(piece)
        s = re.sub(r"[ \t\f\v]+", " ", s)
        s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
        if not out:
            out.append(s.strip())
            continue
        if out[-1].endswith("\n") or s.startswith("\n"):
            out.append(s.lstrip())
        else:
            out.append(" " + s.strip())
    text = "".join(out)
    text = re.sub(r"[ \t]+([,.;:!?%])", r"\1", text)
    text = re.sub(r"[ \t]+([\)\]\}])", r"\1", text)
    text = re.sub(r"[ \t]+(['\"])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()