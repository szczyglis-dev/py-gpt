from pygpt_net.core.agents.custom.debug import content_to_text, ellipsize, items_preview


def test_ellipsize_normalizes_newlines_and_truncates():
    assert ellipsize("a\nb\r", 20) == "a b "
    assert ellipsize("abcdef", 5) == "ab..."
    assert ellipsize(None) == ""


def test_content_to_text_handles_string_parts_and_other_values():
    assert content_to_text("abc") == "abc"
    assert content_to_text(None) == ""
    assert content_to_text([
        {"text": "one"},
        {"type": "output_text", "text": 2},
        {"type": "other", "text": "three"},
        4,
    ]) == "one 2 three 4"


def test_items_preview_uses_last_items_and_roles():
    items = [
        {"role": "system", "content": "old"},
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": [{"text": "answer"}]},
    ]
    preview = items_preview(items, total_chars=128, max_items=2)
    assert "system" not in preview
    assert "- user: question" in preview
    assert "- assistant: answer" in preview
    assert items_preview([]) == "(empty)"
