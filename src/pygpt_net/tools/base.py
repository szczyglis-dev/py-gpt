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

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget

from pygpt_net.core.events import BaseEvent
from pygpt_net.core.locale import LocaleDomain
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

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
        self.has_tab = False
        self.tab_title = ""
        self.tab_icon = ":/icons/build.svg"
        self._lang_mappings = []

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