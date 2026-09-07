from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.layout.chat.markdown import MarkdownHighlighter


def _highlighter():
    return SimpleNamespace(
        setFormat=MagicMock(),
        currentBlock=MagicMock(),
        MARKDOWN_KEYS_REGEX=MarkdownHighlighter.MARKDOWN_KEYS_REGEX,
        MARKDOWN_KWS_FORMAT={
            "BlockQuote": object(), "HR": object(), "HeaderAtx": object(),
            "UnorderedList": object(), "OrderedList": object(), "CodeSpan": object(),
            "Bold": object(), "Italic": object(), "CodeBlock": object(), "HTML": object(),
        },
    )


def test_empty_line_recognizes_only_whitespace():
    h = _highlighter()
    assert MarkdownHighlighter.highlightEmptyLine(h, "   ", None, None, 0) is True
    assert MarkdownHighlighter.highlightEmptyLine(h, "text", None, None, 0) is False


def test_atx_header_formats_match_and_ignores_plain_text():
    h = _highlighter()
    assert MarkdownHighlighter.highlightAtxHeader(h, "## Header", None, None, 0) is True
    h.setFormat.assert_called_once()
    h.setFormat.reset_mock()
    assert MarkdownHighlighter.highlightAtxHeader(h, "plain", None, None, 0) is False
    h.setFormat.assert_not_called()


def test_list_formats_unordered_and_ordered_markers():
    h = _highlighter()
    assert MarkdownHighlighter.highlightList(h, "- item", None, None, 0) is True
    assert h.setFormat.call_count == 1
    h.setFormat.reset_mock()
    assert MarkdownHighlighter.highlightList(h, "1. item", None, None, 0) is True
    assert h.setFormat.call_count == 1


def test_code_span_bold_and_emphasis_detect_markdown():
    h = _highlighter()
    assert MarkdownHighlighter.highlightCodeSpan(h, "`code`", None, None, 0) is True
    assert MarkdownHighlighter.highlightBold(h, "**bold**", None, None, 0) is True
    assert MarkdownHighlighter.highlightEmphasis(h, "*italic*", None, None, 0) is True
    assert h.setFormat.call_count == 3


def test_horizontal_rule_formats_without_reporting_header_match():
    h = _highlighter()
    previous = MagicMock()
    previous.text.return_value = ""
    h.currentBlock.return_value.previous.return_value = previous

    with patch("pygpt_net.ui.layout.chat.markdown.QTextCursor") as cursor_cls:
        result = MarkdownHighlighter.highlightHorizontalLine(h, "---", None, None, 0)

    assert result is False  # current implementation uses formatting as the effect
    cursor_cls.assert_called_once_with(previous)
    h.setFormat.assert_called_once_with(0, 3, h.MARKDOWN_KWS_FORMAT["HR"])


def test_html_highlighter_formats_each_tag():
    h = _highlighter()
    MarkdownHighlighter.highlightHtml(h, "<b>x</b>")
    assert h.setFormat.call_count == 2
