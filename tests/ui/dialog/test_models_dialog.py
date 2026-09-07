from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.dialog.models import Models


def _models():
    editor = SimpleNamespace(current=None)
    return SimpleNamespace(
        _filter_text="", _all_data={}, _filtered_ids=[], _index_to_id=[], _id_to_index={},
        window=SimpleNamespace(
            controller=SimpleNamespace(model=SimpleNamespace(editor=editor)),
            core=SimpleNamespace(llm=MagicMock()),
            ui=SimpleNamespace(models={}, nodes={}),
        ),
        update_list=MagicMock(), _restore_selection_for_current=MagicMock(),
    )


def test_search_normalizes_text_and_reuses_last_dataset():
    m = _models()
    m._all_data = {"a": object()}
    Models._on_search_models(m, "  GPT  ")
    assert m._filter_text == "gpt"
    m.update_list.assert_called_once_with("models.list", m._all_data)


def test_clear_filter_is_noop_when_empty():
    m = _models()
    Models._on_clear_models(m)
    m.update_list.assert_not_called()


def test_clear_filter_refreshes_and_restores_selection():
    m = _models()
    m._filter_text = "gpt"
    m._all_data = {"a": object()}
    Models._on_clear_models(m)
    assert m._filter_text == ""
    m.update_list.assert_called_once_with("models.list", m._all_data)
    m._restore_selection_for_current.assert_called_once_with()


def test_filter_matches_id_or_name_case_insensitively_and_preserves_order():
    m = _models()
    m._filter_text = "son"
    data = OrderedDict([
        ("gpt-5", SimpleNamespace(id="gpt-5", name="GPT")),
        ("sonar-pro", SimpleNamespace(id="sonar-pro", name="Perplexity")),
        ("claude", SimpleNamespace(id="claude", name="Sonnet")),
    ])
    filtered = Models._apply_filter(m, data)
    assert list(filtered) == ["sonar-pro", "claude"]


def test_index_mapping_helpers_are_consistent_and_copy_visible_ids():
    m = _models()
    Models._refresh_index_mapping(m, ["a", "b"])
    assert Models.get_model_id_by_row(m, 0) == "a"
    assert Models.get_model_id_by_row(m, 3) is None
    assert Models.get_row_by_model_id(m, "b") == 1
    ids = Models.get_filtered_ids(m)
    ids.append("c")
    assert m._filtered_ids == ["a", "b"]


def test_provider_display_name_strips_and_handles_errors():
    m = _models()
    m.window.core.llm.get_provider_name.return_value = "  OpenAI  "
    assert Models._get_provider_display_name(m, "openai") == "OpenAI"
    m.window.core.llm.get_provider_name.side_effect = RuntimeError("bad")
    assert Models._get_provider_display_name(m, "broken") == ""
    assert Models._get_provider_display_name(m, "") == ""
