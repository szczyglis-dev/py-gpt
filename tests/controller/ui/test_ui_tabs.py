"""Compatibility smoke tests for the tabs controller location.

Detailed coverage moved to ``tests/controller/tabs`` together with the
``controller.ui.tabs -> controller.tabs`` refactor.
"""

from pygpt_net.controller.tabs import Tabs


def test_tabs_controller_is_exposed_from_new_controller_package():
    assert Tabs.__module__ == "pygpt_net.controller.tabs.tabs"
