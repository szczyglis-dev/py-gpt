from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtTest import QTest, QSignalSpy
from PySide6.QtWidgets import QTreeWidget, QStyle, QStyleOptionViewItem
from shiboken6 import isValid

from pygpt_net.controller.skills.skills import Skills
from pygpt_net.controller.plugins.plugins import Plugins
from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.ui.widget.element.labels import StatusIconCounter
from pygpt_net.ui.layout.toolbox.presets import Presets


@pytest.fixture
def selector(qapp):
    records = [{'name': 'alpha', 'display_name': 'Alpha', 'enabled': False},
               {'name': 'beta', 'display_name': 'Beta', 'enabled': True}]
    def set_enabled(name, enabled):
        next(row for row in records if row['name'] == name)['enabled'] = enabled
        return True
    core = SimpleNamespace(list_installed=lambda enabled_only=False: [dict(row) for row in records
                           if not enabled_only or row["enabled"]],
                           set_enabled=Mock(side_effect=set_enabled))
    window = SimpleNamespace(
        core=SimpleNamespace(skills=core),
        ui=SimpleNamespace(nodes={}, toolbox=SimpleNamespace()),
        controller=SimpleNamespace(presets=SimpleNamespace(sync_agent_skills_from_global=Mock()),
                                   plugins=SimpleNamespace(update_info=Mock())),
    )
    controller = Skills(window)
    window.controller.skills = controller
    toolbox = Presets(window)
    window.ui.toolbox.presets = toolbox
    page = toolbox.setup_skills()
    window.core.config = SimpleNamespace(get=lambda key: MODE_AGENT_V2)
    window.core.plugins = SimpleNamespace(get_ids=lambda: [])
    for key in ('chat.plugins', 'chat.skills'):
        window.ui.nodes[key] = StatusIconCounter(':/icons/code.svg', page)
    info = SimpleNamespace(window=window, is_enabled=lambda name: False,
                           _status_tooltip=lambda title, names: ', '.join(names),
                           update_annotations_info=Mock())
    window.controller.plugins.update_info.side_effect = lambda: Plugins.update_info(info)
    installed = QTreeWidget()
    installed.setColumnCount(5)
    installed.itemChanged.connect(controller._on_enabled_changed)
    window.ui.nodes['skills.installed.list'] = installed
    controller.refresh_installed()
    page.resize(400, 250)
    page.show()
    qapp.processEvents()
    yield window, toolbox, records
    page.close()
    installed.close()
    page.deleteLater()
    installed.deleteLater()


def test_checkbox_callback_keeps_emitting_item_alive(selector):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    item = tree.topLevelItem(0)
    # Call the slot after setting state silently: the broken implementation can
    # be diagnosed without segfaulting Qt's native mouse-event stack in this test.
    with QSignalBlocker(tree):
        item.setCheckState(0, Qt.Checked)
    toolbox._on_skill_changed(item, 0)
    assert isValid(item), 'Checkbox callback deleted its emitting QTreeWidgetItem'
    assert tree.topLevelItem(0) is item
    assert records[0]['enabled'] is True
    window.controller.presets.sync_agent_skills_from_global.assert_called_once()
    window.controller.plugins.update_info.assert_called_once()


def test_repeated_real_mouse_clicks_keep_rows_and_views_in_sync(selector, qapp):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    item = tree.topLevelItem(0)
    changes = QSignalSpy(tree.itemChanged)
    resets = QSignalSpy(tree.model().modelReset)
    option = QStyleOptionViewItem()
    option.initFrom(tree)
    option.rect = tree.visualItemRect(item)
    option.features |= QStyleOptionViewItem.HasCheckIndicator
    option.checkState = item.checkState(0)
    rect = tree.style().subElementRect(QStyle.SE_ItemViewItemCheckIndicator, option, tree)
    for index in range(30):
        QTest.mouseClick(tree.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
        qapp.processEvents()
        assert isValid(item)
        assert tree.topLevelItem(0) is item
        assert records[0]['enabled'] == (index % 2 == 0)
        assert window.ui.nodes['chat.skills'].text() == str(sum(row['enabled'] for row in records))
        assert window.ui.nodes['skills.installed.list'].topLevelItem(0).checkState(0) == item.checkState(0)
    assert changes.count() == 30
    assert resets.count() == 0
    assert window.core.skills.set_enabled.call_count == 30


def test_refresh_updates_data_without_emitting_checkbox_changes(selector):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    item = tree.topLevelItem(0)
    changes = QSignalSpy(tree.itemChanged)
    records[0].update(enabled=True, display_name='Renamed', description='Updated description')
    toolbox.refresh_skills()
    assert tree.topLevelItem(0) is item
    assert item.text(0) == 'Renamed'
    assert item.toolTip(0) == 'Updated description'
    assert item.checkState(0) == Qt.Checked
    assert changes.count() == 0
    window.core.skills.set_enabled.assert_not_called()


def test_refresh_rebuilds_when_installed_skills_change(selector):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    records[:] = [records[1], {'name': 'gamma', 'enabled': False}]
    toolbox.refresh_skills()
    assert [tree.topLevelItem(i).data(0, Qt.UserRole) for i in range(2)] == ['beta', 'gamma']
    window.core.skills.set_enabled.assert_not_called()


def test_keyboard_toggle_preserves_item(selector):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    item = tree.topLevelItem(0)
    tree.setCurrentItem(item)
    QTest.keyClick(tree, Qt.Key_Space)
    assert isValid(item)
    assert records[0]['enabled'] is True
    assert window.ui.nodes['chat.skills'].text() == '2'


def test_registry_read_failure_does_not_delete_existing_rows(selector):
    window, toolbox, records = selector
    tree = window.ui.nodes['toolbox.skills.list']
    item = tree.topLevelItem(0)
    window.core.skills.list_installed = Mock(side_effect=OSError('Temporary read failure'))
    toolbox.refresh_skills()
    assert isValid(item)
    assert tree.topLevelItem(0) is item
