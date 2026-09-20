from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6 import QtCore

from pygpt_net.tools.agent_builder.ui.list import AgentsList, AgentsWidget


def _agent(agent_id, name):
    return SimpleNamespace(id=agent_id, name=name)


def test_agents_widget_action_new_delegates_to_tool():
    tool = MagicMock()
    obj = SimpleNamespace(tool=tool)

    AgentsWidget.action_new(obj)

    tool.add_agent.assert_called_once_with()


def test_agents_widget_cleanup_detaches_model_and_removes_registry_entry():
    list_widget = MagicMock()
    ui = SimpleNamespace(models={"agent.builder.list": object()})
    obj = SimpleNamespace(
        list=list_widget,
        window=SimpleNamespace(ui=ui),
        id="agent.builder.list",
    )

    AgentsWidget.cleanup(obj)

    list_widget.setModel.assert_called_once_with(None)
    list_widget.deleteLater.assert_called_once_with()
    assert ui.models == {}
    assert obj.list is None


def test_agents_widget_cleanup_is_safe_without_list_or_model_registry_entry():
    ui = SimpleNamespace(models={})
    obj = SimpleNamespace(list=None, window=SimpleNamespace(ui=ui), id="agent.builder.list")

    AgentsWidget.cleanup(obj)

    assert obj.list is None
    assert ui.models == {}


def test_agents_widget_update_list_guards_closed_dialog():
    model = MagicMock()
    obj = SimpleNamespace(
        id="agent.builder.list",
        parent=object(),
        window=SimpleNamespace(
            ui=SimpleNamespace(
                nodes={},
                models={"agent.builder.list": model},
            )
        ),
        create_model=MagicMock(),
    )

    AgentsWidget.update_list(obj, {"a": _agent("a", "Agent A")})

    model.setRowCount.assert_not_called()
    obj.create_model.assert_not_called()


def test_agents_widget_update_list_recreates_missing_model_and_binds_rows():
    list_widget = MagicMock()
    widget = SimpleNamespace(list=list_widget)
    model = MagicMock()
    model.index.side_effect = lambda row, col: (row, col)
    ui = SimpleNamespace(
        nodes={"agent.builder.list": widget},
        models={},
    )
    obj = SimpleNamespace(
        id="agent.builder.list",
        parent=object(),
        window=SimpleNamespace(ui=ui),
        create_model=MagicMock(return_value=model),
    )
    data = {
        "key-1": _agent("id-1", "One"),
        "key-2": _agent("id-2", "Two"),
    }

    AgentsWidget.update_list(obj, data)

    obj.create_model.assert_called_once_with(obj.parent)
    list_widget.setModel.assert_called_once_with(model)
    model.setRowCount.assert_called_once_with(2)
    assert model.setItemData.call_count == 2
    assert model.setItemData.call_args_list[0].args == (
        (0, 0),
        {QtCore.Qt.DisplayRole: "One", QtCore.Qt.UserRole: "id-1"},
    )
    assert model.setItemData.call_args_list[1].args == (
        (1, 0),
        {QtCore.Qt.DisplayRole: "Two", QtCore.Qt.UserRole: "id-2"},
    )


def test_agents_widget_update_list_empty_data_clears_rows():
    list_widget = MagicMock()
    model = MagicMock()
    obj = SimpleNamespace(
        id="agent.builder.list",
        parent=object(),
        window=SimpleNamespace(
            ui=SimpleNamespace(
                nodes={"agent.builder.list": SimpleNamespace(list=list_widget)},
                models={"agent.builder.list": model},
            )
        ),
    )

    AgentsWidget.update_list(obj, {})

    model.setRowCount.assert_called_once_with(0)


def _list_obj(agent_id="agent-1"):
    model = MagicMock()
    model.index.side_effect = lambda row, col: (row, col)
    model.data.return_value = agent_id
    return SimpleNamespace(model=MagicMock(return_value=model), tool=MagicMock()), model


def test_agents_list_click_edits_selected_agent():
    obj, model = _list_obj()
    item = SimpleNamespace(row=MagicMock(return_value=2))

    AgentsList.click(obj, item)

    model.data.assert_called_once_with((2, 0), QtCore.Qt.UserRole)
    obj.tool.edit_agent.assert_called_once_with("agent-1")


def test_agents_list_actions_route_selected_id_to_expected_tool_methods():
    for method_name, action in (
        ("rename_agent", AgentsList.action_edit),
        ("duplicate_agent", AgentsList.action_duplicate),
        ("delete_agent", AgentsList.action_delete),
    ):
        obj, _ = _list_obj("id-x")
        item = SimpleNamespace(row=MagicMock(return_value=1))

        action(obj, item)

        getattr(obj.tool, method_name).assert_called_once_with("id-x")


def test_agents_list_actions_ignore_invalid_rows_and_missing_ids():
    item = SimpleNamespace(row=MagicMock(return_value=-1))
    obj, model = _list_obj()
    AgentsList.click(obj, item)
    AgentsList.action_edit(obj, item)
    AgentsList.action_duplicate(obj, item)
    AgentsList.action_delete(obj, item)
    model.data.assert_not_called()
    obj.tool.edit_agent.assert_not_called()
    obj.tool.rename_agent.assert_not_called()
    obj.tool.duplicate_agent.assert_not_called()
    obj.tool.delete_agent.assert_not_called()

    item.row.return_value = 0
    model.data.return_value = None
    AgentsList.click(obj, item)
    AgentsList.action_delete(obj, item)
    obj.tool.edit_agent.assert_not_called()
    obj.tool.delete_agent.assert_not_called()
