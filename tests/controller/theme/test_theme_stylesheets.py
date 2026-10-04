"""Bundled theme contracts needed for editing and live theme switching."""
from pathlib import Path
import re

import pytest


CSS_ROOT = Path(__file__).resolve().parents[3] / "src/pygpt_net/data/css"
THEMES = sorted(CSS_ROOT.glob("*/app.css"))


def rules(path):
    text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
    text = re.sub(r"\{(?:QTMATERIAL|APP)_\w+\}", "theme_value", text)
    text = text.replace("{{", "{").replace("}}", "}")
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        declarations = [part.strip().split(":", 1) for part in body.split(";") if part.strip()]
        for selector in selectors.split(","):
            yield selector.strip(), {key.strip(): value.strip() for key, value in declarations}


@pytest.mark.parametrize("path", THEMES, ids=lambda path: path.parent.name)
def test_theme_defines_core_widget_styles(path):
    # Repeated QSS selectors are valid cascading overrides. Check the theme's
    # basic contract instead of enforcing its source layout.
    merged = {}
    for selector, declarations in rules(path):
        merged.setdefault(selector, {}).update(declarations)
    for selector in ('QMainWindow', 'QSplitter', 'QPushButton'):
        assert merged.get(selector), (path.parent.name, selector)


def test_every_theme_resets_all_persistent_widget_properties():
    # Unlike ordinary QSS, qproperty values are written into the widget and
    # can survive replacing its stylesheet. No theme may omit a reset.
    properties = {
        path.parent.name: {
            (selector, key)
            for selector, declarations in rules(path)
            for key in declarations
            if key.startswith("qproperty-")
        }
        for path in THEMES
    }
    required = set.union(*properties.values())
    assert required
    for theme, declared in properties.items():
        assert declared == required, (theme, required - declared)
