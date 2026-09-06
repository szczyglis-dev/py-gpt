from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.render.web.syntax_highlight import SyntaxHighlight


def make_highlighter(tmp_path, current="monokai"):
    styles = tmp_path / "data" / "js" / "highlight" / "styles"
    styles.mkdir(parents=True)
    (styles / "default.min.css").write_text("default")
    (styles / "monokai.min.css").write_text("mono")
    (styles / "monokai.css").write_text("duplicate")
    config = SimpleNamespace(get_app_path=MagicMock(return_value=str(tmp_path)), get=MagicMock(return_value=current))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    return SyntaxHighlight(window)


def test_style_exists_current_fallback_and_defs(tmp_path):
    h = make_highlighter(tmp_path)
    assert h.exists("monokai") is True
    assert h.exists("missing") is False
    assert h.get_style() == "monokai"
    assert h.get_style_defs() == "mono"
    h.window.core.config.get.return_value = "missing"
    assert h.get_style() == "default"
    assert h.get_style_defs() == "default"


def test_get_styles_deduplicates_minified_and_regular_names(tmp_path):
    h = make_highlighter(tmp_path)
    assert h.get_styles() == ["default", "monokai"]
