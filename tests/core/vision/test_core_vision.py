from unittest.mock import MagicMock

import pygpt_net.core.vision.vision as vision_module
from pygpt_net.core.vision.vision import Vision


def test_vision_builds_analyzer_with_window(monkeypatch):
    analyzer = MagicMock(return_value="analyzer")
    monkeypatch.setattr(vision_module, "Analyzer", analyzer)
    window = object()

    vision = Vision(window)

    assert vision.window is window
    assert vision.analyzer == "analyzer"
    analyzer.assert_called_once_with(window)
