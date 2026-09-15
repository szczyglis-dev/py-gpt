#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace

from pygpt_net.core.text import mentions


def test_encode_decode_and_make_tag_round_trip():
    value = "a<&>b"
    encoded = mentions.encode_value(value)

    assert encoded == "a&lt;&amp;&gt;b"
    assert mentions.decode_value(encoded) == value
    assert mentions.make_tag("ATTACHMENT", value) == "<attachment>a&lt;&amp;&gt;b</attachment>"
    assert mentions.make_tag("unknown", value) == value


def test_iter_tags_matches_supported_kinds_and_preserves_values():
    text = (
        "before <attachment>photo.png</attachment> middle "
        "<file_context>%workdir%/data/src/main.py</file_context> after"
    )

    found = [(match.group(1).lower(), match.group(2)) for match in mentions.iter_tags(text)]

    assert found == [
        (mentions.KIND_ATTACHMENT, "photo.png"),
        (mentions.KIND_FILE_CONTEXT, "%workdir%/data/src/main.py"),
    ]


def test_label_for_attachment_and_workdir_paths():
    assert mentions.label_for(mentions.KIND_ATTACHMENT, "photo.png") == "photo.png"
    assert mentions.label_for(mentions.KIND_FILE_CONTEXT, "%workdir%/data/src/main.py") == "src/main.py"
    assert mentions.label_for(mentions.KIND_FILE_CONTEXT, "data\\docs\\readme.md") == "docs/readme.md"
    assert mentions.label_for(mentions.KIND_FILE_CONTEXT, "%workdir%/data") == "data/"


def test_image_attachment_mentions_counts_only_existing_local_images(tmp_path):
    image_a = tmp_path / "a.png"
    image_b = tmp_path / "b.jpg"
    text = tmp_path / "note.txt"
    image_a.write_bytes(b"a")
    image_b.write_bytes(b"b")
    text.write_text("x", encoding="utf-8")

    attachments = {
        "a": SimpleNamespace(path=str(image_a), name="first.png"),
        "text": SimpleNamespace(path=str(text), name="note.txt"),
        "missing": SimpleNamespace(path=str(tmp_path / "missing.webp"), name="missing.webp"),
        "b": SimpleNamespace(path=str(image_b), name=""),
        "duplicate-name": SimpleNamespace(path=str(image_b), name="FIRST.PNG"),
    }

    labels = mentions._image_attachment_mentions(attachments)

    assert labels["first.png"] == "Attached Image #1"
    assert labels["b.jpg"] == "Attached Image #2"
    # The duplicate is still an image in provider order, but setdefault keeps the
    # first stable label for a repeated filename.
    assert labels["first.png"] != "Attached Image #3"
    assert "note.txt" not in labels
    assert "missing.webp" not in labels


def test_to_model_text_flattens_tags_without_runtime_attachments():
    text = (
        "inspect <attachment>photo.png</attachment> and "
        "<file_context>%workdir%/data/a&amp;b.txt</file_context>"
    )

    assert mentions.to_model_text(text) == "inspect photo.png and %workdir%/data/a&b.txt"


def test_to_model_text_maps_only_image_attachment_mentions_to_native_labels(tmp_path):
    image = tmp_path / "photo.png"
    document = tmp_path / "document.txt"
    image.write_bytes(b"png")
    document.write_text("text", encoding="utf-8")
    attachments = {
        "doc": SimpleNamespace(path=str(document), name="document.txt"),
        "image": SimpleNamespace(path=str(image), name="photo.png"),
    }
    text = (
        "compare <attachment>photo.png</attachment> with "
        "<attachment>document.txt</attachment>"
    )

    result = mentions.to_model_text(text, attachments=attachments)

    assert result == "compare Attached Image #1 with document.txt"


def test_to_display_text_uses_plain_at_labels_and_decodes_entities():
    text = (
        "<attachment>a&amp;b.png</attachment> "
        "<file_context>%workdir%/data/src/app.py</file_context>"
    )

    assert mentions.to_display_text(text) == "@a&b.png @src/app.py"
