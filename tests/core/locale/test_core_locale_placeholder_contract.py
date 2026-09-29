from pygpt_net.core.locale.placeholder import apply
from pygpt_net.core.types import MODEL_DEFAULT, MODEL_DEFAULT_MINI


def test_apply_replaces_model_placeholders_and_handles_none():
    assert apply(None) == ""
    assert apply("plain") == "plain"
    assert apply("A=%MODEL_DEFAULT% B=%MODEL_DEFAULT_MINI%") == f"A={MODEL_DEFAULT} B={MODEL_DEFAULT_MINI}"
