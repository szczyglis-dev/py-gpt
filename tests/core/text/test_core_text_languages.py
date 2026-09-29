from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.text.text as mod
from pygpt_net.core.text.text import Text


def make_text(tmp_path):
    app = tmp_path / "app"; data = app / "data"; data.mkdir(parents=True)
    config = SimpleNamespace(get_app_path=MagicMock(return_value=str(app)))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    return Text(window), data


def test_language_choices_load_sort_clean_and_cache(tmp_path, monkeypatch):
    text, data = make_text(tmp_path)
    (data / "languages.csv").write_text(
        "code,x,y,name,original\npl,,,Polish,Polski\nen,,,English,English\nzz,,,\"Zulu\",'Zulu'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "trans", lambda key: "Auto detect")
    choices = text.get_language_choices()
    labels = [next(iter(x.values())) for x in choices]
    assert labels == sorted(labels, key=str.lower)
    assert {"pl": "Polish (Polski)"} in choices
    assert {"zz": "Zulu (Zulu)"} in choices
    (data / "languages.csv").unlink()
    assert text.get_language_choices() is choices


def test_language_name_and_search_use_prefix_before_substring(tmp_path, monkeypatch):
    text, _ = make_text(tmp_path)
    monkeypatch.setattr(mod, "trans", lambda key: "Auto detect")
    text.lang_list = [
        {"en": "English"},
        {"gb": "British English"},
        {"pl": "Polish (Polski)"},
    ]
    assert text.get_language_name("pl") == "Polish (Polski)"
    assert text.get_language_name("xx") == ""
    assert text.find_lang_id_by_search_string("eng") == "en"
    assert text.find_lang_id_by_search_string("brit") == "gb"
    assert text.find_lang_id_by_search_string("polski") == "pl"
    assert text.find_lang_id_by_search_string("missing") == ""
