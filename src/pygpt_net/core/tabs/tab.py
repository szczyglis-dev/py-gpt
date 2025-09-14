#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
# ================================================== #

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass(slots=True)
class Tab:

    # types
    TAB_ADD = -1
    TAB_CHAT = 0
    TAB_NOTEPAD = 1
    TAB_FILES = 2
    TAB_TOOL_PAINTER = 3
    TAB_TOOL_CALENDAR = 4
    TAB_TOOL = 100

    uuid: Optional[str] = None
    pid: Optional[int] = None
    idx: Optional[int] = 0
    type: Optional[int] = TAB_CHAT
    title: Optional[str] = ""
    icon: Optional[str] = None
    tooltip: Optional[str] = None
    data_id: Optional[str] = None
    new_idx: Optional[int] = None
    custom_name: Optional[bool] = False
    child: Optional[Any] = None
    parent: Optional[Any] = None
    column_idx: Optional[int] = 0
    tool_id: Optional[str] = None
    on_delete: Optional[callable] = None

    loaded: bool = False
    refs: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __init__(
            self,
            uuid: Optional[str] = None,
            pid: Optional[int] = None,
            idx: Optional[int] = 0,
            type: Optional[int] = TAB_CHAT,
            title: Optional[str] = "",
            icon: Optional[str] = None,
            tooltip: Optional[str] = None,
            data_id: Optional[str] = None,
            new_idx: Optional[int] = None,
            custom_name: Optional[bool] = False,
            child: Optional[Any] = None,
            parent: Optional[Any] = None,
            column_idx: Optional[int] = 0,
            tool_id: Optional[str] = None,
            on_delete: Optional[callable] = None
    ):
        """
        Tab data

        :param uuid: Unique identifier
        :param pid: Process ID
        :param idx: Index of the tab
        :param type: Type of the tab, one of the TAB_* constants
        :param title: Title of the tab
        :param icon: Icon for the tab
        :param tooltip: Tooltip for the tab
        :param data_id: Data identifier for the tab content (meta_id, notepad_id, etc.)
        :param new_idx: New index for the tab, used when reordering
        :param custom_name: True if tab has custom name, False otherwise
        :param child: Child widget (TabBody)
        :param parent: Parent output column (OutputColumn)
        :param column_idx: Index of the column this tab belongs to
        :param tool_id: Tool identifier if this tab is a tool tab
        :param on_delete: Callback function for delete event
        """
        self.uuid = uuid
        self.pid = pid
        self.idx = idx
        self.type = type
        self.title = title
        self.icon = icon
        self.tooltip = tooltip
        self.data_id = data_id
        self.new_idx = new_idx
        self.custom_name = custom_name
        self.child = child  # TabBody
        self.parent = parent # OutputColumn
        self.column_idx = column_idx  # index of the column this tab belongs to
        self.tool_id = tool_id
        self.loaded = False  # True if tab is loaded, False if not
        self.on_delete = on_delete  # callback for delete event
        self.refs = []  # list of references to widgets in this tab

        dt = datetime.now()
        self.created_at = dt
        self.updated_at = dt

    def cleanup(self):
        """Clean up on delete"""
        try:
            if self.on_delete:
                self.on_delete(self)
            self.delete_refs()
        except Exception as e:
            pass
            # print(f"Error during tab cleanup:")
            # print(e)

    def add_ref(self, ref: Any) -> None:
        """
        Add reference to widget in this tab

        :param ref: widget reference
        """
        if ref not in self.refs:
            self.refs.append(ref)

    def delete_refs(self) -> None:
        """
        Delete all references to widgets in this tab
        """
        # cleanup children
        if self.child:
            self.child.cleanup()

        # cleanup parent
        for ref in self.refs:
            if ref and hasattr(ref, 'deleteLater'):
                ref.deleteLater()
        del self.refs[:]

    def delete_ref(self, widget: Any) -> None:
        """
        Unpin reference to widget in this tab

        :param widget: widget reference
        """
        for ref in self.refs:
            if ref and ref is widget:
                self.refs.remove(ref)
                break
        if self.child and hasattr(self.child, 'delete_ref'):
            self.child.delete_ref(widget)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict

        :return: dict
        """
        return {
            "uuid": str(self.uuid),
            "pid": self.pid,
            "idx": self.idx,
            "type": self.type,
            "title": self.title,
            "loaded": self.loaded,
            "icon": self.icon,
            "tooltip": self.tooltip,
            "data_id": self.data_id,
            "child": str(self.child),  # child widget
            "parent": str(self.parent),  # parent column
            "custom_name": self.custom_name,
            "custom_idx": self.new_idx,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "column_idx": self.column_idx,
            "tool_id": self.tool_id,
            "refs": [str(ref) for ref in self.refs],  # references to widgets
        }

    def __str__(self) -> str:
        """
        String representation

        :return: str
        """
        return str(self.to_dict())