"""Shared text editor components."""

from .base import CONFIG_TAB_INDENT_SPACES, CONFIG_TAB_WIDTH, CONFIG_WORD_WRAP, DEFAULT_TAB_WIDTH, TextEditor
from .gutter import LineNumbers
from .syntax import SyntaxHighlighter

__all__ = [
    'CONFIG_TAB_INDENT_SPACES',
    'CONFIG_TAB_WIDTH',
    'CONFIG_WORD_WRAP',
    'DEFAULT_TAB_WIDTH',
    'LineNumbers',
    'SyntaxHighlighter',
    'TextEditor',
]
