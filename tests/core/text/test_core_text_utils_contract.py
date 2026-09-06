import os

from pygpt_net.core.text.utils import elide_filename, has_unclosed_code_tag, output_clean_html, output_html2text


def test_output_clean_html_removes_actions_copy_links_and_scripts():
    html = '<div><a class="code-header-copy">copy</a><div class="action-icons">icons</div><script>x()</script><p>keep</p></div>'
    cleaned = output_clean_html(html)
    assert "code-header-copy" not in cleaned
    assert "action-icons" not in cleaned
    assert "<script" not in cleaned
    assert "keep" in cleaned


def test_output_html2text_removes_ui_only_elements_and_preserves_message_breaks():
    html = (
        '<div class="msg-user"><div class="name-header">Me</div><div class="msg"><p>Hello<br>world</p></div></div>'
        '<div class="msg-bot"><span class="ts">12:00</span><p>Answer</p></div>'
    )
    text = output_html2text(html)
    assert "Me" not in text and "12:00" not in text
    assert "Hello\nworld" in text
    assert "Answer" in text


def test_empty_and_unclosed_code_helpers():
    assert output_html2text("") == ""
    # Current renderer intentionally disables this heuristic.
    assert has_unclosed_code_tag("```python\nprint(1)") is False


def test_elide_filename_preserves_extension_and_optional_directory():
    name = "this_is_a_very_long_filename_for_testing.txt"
    out = elide_filename(name, max_len=24)
    assert len(out) <= 24
    assert out.endswith(".txt")
    assert "..." in out
    short = "short.txt"
    assert elide_filename(short, max_len=24) == short
    path = os.path.join("folder", name)
    kept = elide_filename(path, max_len=24, keep_dir=True)
    assert os.path.dirname(kept) == "folder"
    assert os.path.basename(kept).endswith(".txt")


def test_elide_filename_tiny_or_nonpositive_limits_are_deterministic():
    assert elide_filename("abcdef.txt", max_len=0) == "abcdef.txt"
    tiny = elide_filename("abcdef.txt", max_len=5)
    assert tiny.startswith("a...")
    assert len(tiny) <= 5
