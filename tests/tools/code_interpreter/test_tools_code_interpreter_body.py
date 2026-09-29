from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.code_interpreter.body import Body


def _body(syntax="default", blocks=True, edit_icons=True, style="blocks"):
    config = MagicMock()
    values = {
        "render.code_syntax": syntax,
        "theme.style": style,
        "render.blocks": blocks,
        "ctx.edit_icons": edit_icons,
    }
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.get_app_path.return_value = "/app"
    markdown = MagicMock()
    markdown.get_web_css.return_value = "@font-face{src:url(%fonts%/font.woff)}"
    body = Body.__new__(Body)
    body.window = SimpleNamespace(
        core=SimpleNamespace(config=config),
        controller=SimpleNamespace(theme=SimpleNamespace(markdown=markdown)),
    )
    body.highlight = MagicMock()
    body.highlight.get_style_defs.return_value = ".hljs{}"
    return body


def test_code_interpreter_body_constructor_builds_syntax_highlighter():
    window = object()
    highlighter = object()
    with patch("pygpt_net.tools.code_interpreter.body.SyntaxHighlight", return_value=highlighter) as cls:
        body = Body(window)
    assert body.window is window
    assert body.highlight is highlighter
    cls.assert_called_once_with(window)


def test_code_interpreter_body_prepare_styles_replaces_fonts_and_dark_syntax_color():
    body = _body(syntax="monokai")
    css = body.prepare_styles()
    assert "/app/data/fonts/font.woff" in css
    assert "pre { color: #fff; }" in css
    assert ".hljs{}" in css
    assert "lds-ring" in css


def test_code_interpreter_body_prepare_styles_defaults_to_light_syntax():
    body = _body(syntax="")
    css = body.prepare_styles()
    assert "pre { color: #000; }" in css


def test_code_interpreter_body_get_html_includes_pid_theme_and_feature_classes():
    body = _body(blocks=True, edit_icons=True, style="compact")
    body.prepare_styles = MagicMock(return_value="CSS")

    html = body.get_html(77)

    assert "let pid = 77" in html
    assert 'class="display-blocks display-edit-icons theme-compact"' in html
    assert "CSS" in html
    assert "scrollToBottom" in html
    assert "appendImage" in html
    assert "qrc:///qtwebchannel/qwebchannel.js" in html


def test_code_interpreter_body_get_html_omits_disabled_feature_classes():
    body = _body(blocks=False, edit_icons=False, style="blocks")
    body.prepare_styles = MagicMock(return_value="")
    html = body.get_html(1)
    assert 'class="theme-blocks"' in html
    assert "display-edit-icons" not in html
    assert "display-blocks" not in html
