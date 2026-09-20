#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.12 18:30:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
)
from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Agent common controller

        :param window: Window instance
        """
        self.window = window

    def _set_toolbox_toggle(self, key: str, state: bool):
        """Update an Agent toolbox toggle without re-entering its handler."""
        try:
            widget = self.window.ui.config.get('global', {}).get(key)
        except AttributeError:
            widget = None
        if widget is None:
            return

        box = getattr(widget, 'box', None)
        if box is None:
            widget.setChecked(bool(state))
            return

        state = bool(state)
        previous = box.blockSignals(True)
        try:
            widget.setChecked(state)
        finally:
            box.blockSignals(previous)

        # AnimToggle normally moves its handle from stateChanged.  Signals are
        # intentionally blocked above to avoid recursively entering the paired
        # toggle handler, so trigger only its visual animation explicitly.
        setup_animation = getattr(box, "setup_animation", None)
        if callable(setup_animation):
            setup_animation(state)
        else:
            box.update()

    def sync_stop_continue_ui(self):
        """Synchronize the mutually exclusive Auto-stop/Always continue toggles."""
        self._set_toolbox_toggle(
            'agent.auto_stop',
            bool(self.window.core.config.get('agent.auto_stop')),
        )
        self._set_toolbox_toggle(
            'agent.continue',
            bool(self.window.core.config.get('agent.continue.always')),
        )

    def normalize_stop_continue(self):
        """Repair an old contradictory state where both options are enabled."""
        if self.window.core.config.get('agent.auto_stop') and \
                self.window.core.config.get('agent.continue.always'):
            # Always continue is the more explicit mode; when both legacy values
            # are true, keep it and disable Auto-stop.
            self.window.core.config.set('agent.auto_stop', False)
            self.window.core.config.save()

    def enable_auto_stop(self):
        """Enable auto stop and disable Always continue (Legacy)."""
        self.window.core.config.set('agent.auto_stop', True)
        self.window.core.config.set('agent.continue.always', False)
        self.window.core.config.save()
        self.sync_stop_continue_ui()

    def disable_auto_stop(self):
        """Disable auto stop (Legacy)."""
        self.window.core.config.set('agent.auto_stop', False)
        self.window.core.config.save()
        self._set_toolbox_toggle('agent.auto_stop', False)

    def toggle_auto_stop(self, state: bool):
        """
        Toggle auto stop (Legacy). Enabling it disables Always continue.

        :param state: state of checkbox
        """
        if not state:
            self.disable_auto_stop()
        else:
            self.enable_auto_stop()

    def enable_continue(self):
        """Enable Always continue and disable Auto-stop (Legacy)."""
        self.window.core.config.set('agent.continue.always', True)
        self.window.core.config.set('agent.auto_stop', False)
        self.window.core.config.save()
        self.sync_stop_continue_ui()

    def disable_continue(self):
        """Disable Always continue (Legacy)."""
        self.window.core.config.set('agent.continue.always', False)
        self.window.core.config.save()
        self._set_toolbox_toggle('agent.continue', False)

    def toggle_continue(self, state: bool):
        """
        Toggle Always continue (Legacy). Enabling it disables Auto-stop.

        :param state: state of checkbox
        """
        if not state:
            self.disable_continue()
        else:
            self.enable_continue()

    def is_infinity_loop(self, mode: str) -> bool:
        """
        Check if infinity loop is active

        :param mode: current mode
        :return: True if infinity loop is enabled
        """
        # legacy
        if (mode == MODE_AGENT and self.window.core.config.get('agent.iterations') == 0) or \
            (self.window.controller.plugins.is_enabled("agent")
             and self.window.core.plugins.get_option("agent", "iterations") == 0):
            return True
        return False

    def should_confirm_infinity_loop(self) -> bool:
        """Return True when the infinite-run safety confirmation is enabled."""
        value = self.window.core.config.get('agent.infinity.confirm')
        # Fail safe for profiles that have not gone through the 2.8.17 patch yet.
        return True if value is None else bool(value)

    def disable_infinity_loop_confirm(self):
        """Persistently disable the infinite-run confirmation dialog."""
        self.window.core.config.set('agent.infinity.confirm', False)
        self.window.core.config.save()

    def display_infinity_loop_confirm(self):
        """Show infinity run confirm dialog"""
        self.window.ui.dialogs.confirm(
            type="agent.infinity.run",
            id=0,
            msg=trans("agent.infinity.confirm.content"),
            dont_show_again=True,
        )

    def show_status(self):
        """Show agent status (Legacy)"""
        self.window.ui.nodes['status.agent'].setVisible(True)

    def hide_status(self):
        """Hide agent status (Legacy)"""
        self.window.ui.nodes['status.agent'].setVisible(False)

    def toggle_status(self):
        """Toggle agent status (Legacy)"""
        mode = self.window.core.config.get('mode')
        if mode in [MODE_AGENT] or self.window.controller.agent.legacy.is_inline():
            self.show_status()
        else:
            self.hide_status()

    def enable_loop(self):
        """Enable loop (Llama)"""
        self.window.core.config.set('agent.llama.loop.enabled', True)
        self.window.core.config.save()

    def disable_loop(self):
        """Disable loop (Llama)"""
        self.window.core.config.set('agent.llama.loop.enabled', False)
        self.window.core.config.save()

    def toggle_loop(self, state: bool):
        """
        Toggle loop (Llama)

        :param state: state of checkbox
        """
        if not state:
            self.disable_loop()
        else:
            self.enable_loop()