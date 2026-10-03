#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.05 21:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any, Callable
import weakref
from enum import Enum

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget

from pygpt_net.core.events import BaseEvent
from pygpt_net.core.locale import LocaleDomain
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

class ToolMenuAction(Enum):
    ALWAYS_DIALOG = 'always_dialog'
    ALWAYS_TAB = 'always_tab'
    DIALOG_IF_TAB_EXISTS = 'dialog_if_tab_exists'
    TAB_IF_EXISTS = 'tab_if_exists'


class BaseTool(QObject, LocaleDomain):
    def __init__(self, *args, **kwargs):
        """
        Base Tool

        :param window: Window instance
        :param args: arguments
        :param kwargs: keyword arguments
        """
        super(BaseTool, self).__init__()
        self.init_locale_domain()
        self.window = None
        self.id = ""
        self.allow_tab = False
        self.allow_dialog = True
        self.multi_tab = True
        self.multi_dialog = False
        self.on_menu_click = ToolMenuAction.ALWAYS_DIALOG
        self.dialog_id = ''
        self.dialog_types = ()
        self.dialog_opener = 'open'
        self._single_dialog_id = None
        self.tab_title = ""
        self.tab_icon = ":/icons/build.svg"
        self._lang_mappings = []

    @property
    def has_tab(self):
        """Compatibility alias; all policy lives in allow_tab."""
        return self.allow_tab

    @has_tab.setter
    def has_tab(self, value):
        self.allow_tab = bool(value)

    @property
    def single_instance(self):
        return not self.multi_tab

    @single_instance.setter
    def single_instance(self, value):
        self.multi_tab = not bool(value)

    def can_open_tab(self):
        return self.allow_tab

    def can_open_dialog(self):
        return self.allow_dialog

    def allows_multiple_tabs(self):
        return self.allow_tab and self.multi_tab

    def allows_multiple_dialogs(self):
        return self.allow_dialog and self.multi_dialog

    def existing_tab(self):
        if self.window is None:
            return None
        return self.window.controller.tabs.get_first_tab_by_tool(self.id)

    def can_add_tab(self):
        return self.can_open_tab() and (self.multi_tab or self.existing_tab() is None)

    def can_add_dialog(self):
        """Whether opening may create a new window instead of reusing one."""
        if not self.can_open_dialog():
            return False
        if self.multi_dialog or self.window is None:
            return True
        dialog_id = self.dialog_id or self._single_dialog_id
        return not dialog_id or dialog_id not in self.window.ui.dialog

    def resolve_dialog_id(self, requested):
        """Select a stable dialog identity for single-dialog tools."""
        if not self.can_open_dialog():
            return None
        if self.multi_dialog:
            return requested
        if self._single_dialog_id is None:
            self._single_dialog_id = requested
        return self._single_dialog_id

    def open_tab(self):
        if not self.can_open_tab():
            return None
        return self.window.controller.tabs.open_or_activate(Tab.TAB_TOOL, self.id)

    def open_dialog(self):
        if not self.can_open_dialog():
            return None
        dialog = self.window.ui.dialog.get(self.dialog_id or self._single_dialog_id)
        if not self.multi_dialog and dialog is not None and dialog.isVisible():
            dialog.raise_()
            dialog.activateWindow()
            return dialog
        return getattr(self, self.dialog_opener)()

    def on_menu_action(self, checked=False):
        policy = self.on_menu_click
        if policy == ToolMenuAction.ALWAYS_TAB:
            return self.open_tab()
        if policy == ToolMenuAction.ALWAYS_DIALOG:
            return self.open_dialog()
        exists = self.existing_tab() is not None
        if policy == ToolMenuAction.DIALOG_IF_TAB_EXISTS:
            return self.open_dialog() if exists else self.open_tab()
        if policy == ToolMenuAction.TAB_IF_EXISTS:
            return self.open_tab() if exists else self.open_dialog()
        raise ValueError(f'Unsupported tool menu policy: {policy}')

    def setup(self):
        """Setup tool"""
        pass

    def post_setup(self):
        """Post-setup (window), after plugins are loaded"""
        pass

    def on_update(self):
        """On app main loop update"""
        pass

    def on_post_update(self):
        """On app main loop update"""
        pass

    def on_exit(self):
        """On app exit"""
        pass

    def on_reload(self):
        """On app profile reload"""
        pass

    def handle(self, event: BaseEvent):
        """
        Handle event

        :param event: Event instance
        """
        pass

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        return {}

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        pass

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_instance(
            self,
            type_id: str,
            dialog_id: Optional[str] = None
    ) -> Optional[BaseDialog]:
        """
        Spawn and return dialog instance

        :param type_id: dialog instance ID
        :param dialog_id: dialog instance ID
        """
        return None

    def as_tab(self, tab: Tab) -> Optional[QWidget]:
        """
        Spawn and return tab instance

        :param tab: Parent tab instance
        :return: Tab widget instance
        """
        return None


    def add_lang_mapping(
            self,
            target: Any,
            key: str,
            setter: str = "setText",
            domain: Optional[str] = None,
            on_apply: Optional[Callable] = None,
    ) -> Any:
        """
        Register a runtime language mapping owned by this tool.

        Unlike the legacy ``get_lang_mappings()`` table, this API can target
        widgets/actions owned privately by a tool (including dynamically
        created tab instances), so they do not need to be exposed through
        ``window.ui.nodes``. Dead Qt/Python targets are dropped automatically.

        :param target: Qt/Python object that owns the setter
        :param key: translation key
        :param setter: setter method name, e.g. setText/setToolTip/setTitle
        :param domain: optional translation domain
        :param on_apply: optional callback executed after applying the mapping
        :return: target (for convenient inline registration)
        """
        if target is None or not isinstance(key, str) or not key:
            return target

        try:
            target_ref = weakref.ref(target)
        except TypeError:
            target_ref = lambda target=target: target

        callback_ref = None
        if on_apply is not None:
            try:
                callback_ref = weakref.WeakMethod(on_apply)
            except TypeError:
                callback_ref = lambda on_apply=on_apply: on_apply

        mapping = {
            "target": target_ref,
            "key": key,
            "setter": setter,
            "domain": domain if domain is not None else self.get_locale_domain(),
            "on_apply": callback_ref,
        }
        self._lang_mappings.append(mapping)
        self._apply_lang_mapping(mapping)
        return target

    def _apply_lang_mapping(self, mapping: Dict[str, Any]) -> bool:
        """Apply one registered tool mapping; return False for a dead target."""
        target_ref = mapping.get("target")
        target = target_ref() if callable(target_ref) else None
        if target is None:
            return False

        try:
            setter = getattr(target, mapping.get("setter", "setText"), None)
            if setter is not None:
                setter(trans(mapping.get("key", ""), domain=mapping.get("domain")))
        except RuntimeError:
            return False
        except Exception:
            return True

        callback_ref = mapping.get("on_apply")
        callback = callback_ref() if callable(callback_ref) else None
        if callback is not None:
            try:
                callback()
            except RuntimeError:
                pass
            except Exception:
                pass
        return True

    def apply_lang_mappings(self):
        """Refresh every live runtime language mapping registered by the tool."""
        if not self._lang_mappings:
            return
        alive = []
        for mapping in self._lang_mappings:
            if self._apply_lang_mapping(mapping):
                alive.append(mapping)
        self._lang_mappings = alive

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {}


class TabWidget(QWidget):
    """Base tab tool widget"""
    def __init__(self, parent: QWidget = None):
        """
        Initialize tab tool widget

        :param parent: Parent widget
        """
        super(TabWidget, self).__init__(parent)
        self.window = None  # Window instance
        self.tool = None  # Tool instance
        self.setObjectName("TabWidget")  # Set object name for styling

    def from_tool(self, tool: Any):
        """
        Set tool instance

        :param tool: Tool instance
        """
        self.tool = tool
        self.window = tool.window if tool else None

    def setup(self):
        """Setup tab tool widget"""
        layout = self.tool.setup(all=False)
        self.setLayout(layout)

    def on_delete(self):
        """Cleanup on delete"""
        if self.tool and hasattr(self.tool, 'on_delete'):
            self.tool.on_delete()
