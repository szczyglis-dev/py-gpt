import importlib

import pytest


CASES = [
    ("file_csv", "csv", ["csv"]),
    ("file_docx", "docx", ["docx"]),
    ("file_epub", "epub", ["epub"]),
    ("file_excel", "xlsx", ["xlsx"]),
    ("file_html", "html", ["html", "htm"]),
    ("file_image_vision", "image_vision", ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]),
    ("file_ipynb", "ipynb", ["ipynb"]),
    ("file_json", "json", ["json"]),
    ("file_markdown", "md", ["md"]),
    ("file_pdf", "pdf", ["pdf"]),
    ("file_video_audio", "video_audio", ["mp4", "avi", "mov", "mkv", "webm", "mp3", "mpeg", "mpga", "m4a", "wav"]),
    ("file_xml", "xml", ["xml"]),
]


@pytest.mark.parametrize("module_name,loader_id,extensions", CASES)
def test_file_loader_metadata_is_stable(module_name, loader_id, extensions):
    module = importlib.import_module(f"pygpt_net.provider.loaders.{module_name}")
    loader = module.Loader()
    assert loader.id == loader_id
    assert loader.extensions == extensions
    assert loader.type == ["file"]
    assert loader.name
