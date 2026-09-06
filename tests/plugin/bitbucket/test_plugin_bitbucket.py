from tests.mocks import mock_window
from tests.plugin_test_helpers import (
    assert_command_plugin_surface,
    assert_command_plugin_worker_routing,
    assert_handle_execute_routes,
)
from pygpt_net.plugin.bitbucket import Plugin


def test_bitbucket_command_surface(mock_window):
    plugin = Plugin(window=mock_window)
    assert_command_plugin_surface(plugin)


def test_bitbucket_execute_event_routes_to_cmd(mock_window):
    plugin = Plugin(window=mock_window)
    assert_handle_execute_routes(plugin)


def test_bitbucket_worker_routing_isolated_from_external_sdk(mock_window):
    plugin = Plugin(window=mock_window)
    assert_command_plugin_worker_routing(plugin, "pygpt_net.plugin.bitbucket.worker")
