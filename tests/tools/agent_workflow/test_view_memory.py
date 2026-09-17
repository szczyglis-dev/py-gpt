import threading
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# Load the small bridge without importing unrelated desktop controllers (X11).
_spec = importlib.util.spec_from_file_location(
    'workflow_bridge_under_test',
    Path(__file__).resolve().parents[3] / 'src/pygpt_net/controller/agent_workflow/agent_workflow.py',
)
_bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bridge)
AgentWorkflow = _bridge.AgentWorkflow
from pygpt_net.tools.agent_workflow.ui.widgets import WorkflowView


def test_controller_coalesces_worker_burst(monkeypatch):
    emit = MagicMock()
    monkeypatch.setattr(_bridge, 'safe_emit', emit)
    controller = SimpleNamespace(
        _publish_lock=threading.Lock(), _publish_pending=False, signals=object(),
        is_visible=lambda: True,
    )
    threads = [threading.Thread(target=lambda: [AgentWorkflow.publish(controller) for _ in range(100)])
               for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    emit.assert_called_once_with(controller.signals, 'invalidated')
    AgentWorkflow._flush_publish(controller)
    assert emit.call_args.args == (controller.signals, 'changed', None)
    AgentWorkflow.publish(controller)
    assert emit.call_count == 3


def test_controller_skips_publish_when_workflow_is_hidden(monkeypatch):
    emit = MagicMock()
    monkeypatch.setattr(_bridge, 'safe_emit', emit)
    controller = SimpleNamespace(
        _publish_lock=threading.Lock(), _publish_pending=False, signals=object(),
        is_visible=MagicMock(return_value=False),
    )

    AgentWorkflow.publish(controller)

    controller.is_visible.assert_called_once_with()
    emit.assert_not_called()
    assert not controller._publish_pending


def make_view():
    page = MagicMock()
    core = SimpleNamespace(agent_workflow=SimpleNamespace(snapshot=MagicMock(return_value={'run_id': 'latest'})))
    return SimpleNamespace(
        _deleted=False, _dirty=True, _loaded=True, _sending=False,
        _generation=1, _pending_snapshot=None, _render_timer=MagicMock(),
        _recovery_timer=MagicMock(), _on_terminated=MagicMock(),
        window=SimpleNamespace(core=core), isVisible=MagicMock(return_value=True),
        page=MagicMock(return_value=page),
    )


def test_hidden_view_does_not_snapshot_or_send():
    view = make_view()
    view.isVisible.return_value = False
    WorkflowView._flush_render(view)
    view.window.core.agent_workflow.snapshot.assert_not_called()
    view.page.assert_not_called()
    assert view._dirty


def test_only_one_javascript_update_is_in_flight_and_newest_state_is_preserved():
    view = make_view()
    WorkflowView._flush_render(view)
    callback = view.page().runJavaScript.call_args.args[1]
    view._dirty = True
    for _ in range(100):
        WorkflowView._flush_render(view)
    view.page().runJavaScript.assert_called_once()
    view.window.core.agent_workflow.snapshot.assert_called_once()
    callback(True)
    assert not view._sending
    view._render_timer.start.assert_called_once()
    WorkflowView._flush_render(view)
    assert view.page().runJavaScript.call_count == 2


def test_stale_callback_cannot_clear_new_page_sending_state():
    view = make_view()
    WorkflowView._flush_render(view)
    callback = view.page().runJavaScript.call_args.args[1]
    view._generation += 1
    callback(False)
    assert view._sending
    view._on_terminated.assert_not_called()


def test_crashed_workflow_retains_dirty_state_until_visible():
    view = make_view()
    view.isVisible.return_value = False
    WorkflowView._on_terminated(view)
    assert not view._loaded
    assert view._dirty
    view._recovery_timer.start.assert_not_called()
