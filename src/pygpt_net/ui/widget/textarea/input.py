#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 07:00:00                  #
# ================================================== #

from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QImage
from PySide6.QtWidgets import (
    QTextEdit,
    QApplication,
    QPushButton,
    QWidget,
    QHBoxLayout,
)

from pygpt_net.core.events import Event
from pygpt_net.utils import trans

class ChatInput(QTextEdit):

    ICON_PASTE = QIcon(":/icons/paste.svg")
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    ICON_ATTACHMENT = QIcon(":/icons/add.svg")
    ICON_MIC_ON = QIcon(":/icons/mic.svg")
    ICON_MIC_OFF = QIcon(":/icons/mic_off.svg")

    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.setFocus()
        self.value = self.window.core.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8
        self._text_top_padding = 12
        self.textChanged.connect(self.window.controller.ui.update_tokens)
        self.setProperty('class', 'layout-input')

        # --- Icon bar (left) settings ---
        # Settings controlling the left icon bar (spacing, sizes, margins)
        self._icons_margin = 6           # inner left/right padding around the bar
        self._icons_spacing = 4          # spacing between buttons
        self._icons_offset_y = -4        # small upward shift (visual alignment)
        self._icon_size = QSize(18, 18)  # icon size (matches your original)
        self._btn_size = QSize(24, 24)   # button size (w x h), matches previous QPushButton

        # Storage for icon buttons and metadata
        self._icons = {}       # key -> QPushButton
        self._icon_meta = {}   # key -> {"icon": QIcon, "alt_icon": Optional[QIcon], "tooltip": str, "alt_tooltip": Optional[str], "active": bool}
        self._icon_order = []  # rendering order

        # Add a "+" button in the top-left corner to add attachments
        self._init_icon_bar()
        self.add_icon(
            key="attach",
            icon=self.ICON_ATTACHMENT,
            tooltip=trans("attachments.btn.input.add"),
            callback=self.action_add_attachment,
            visible=True,
        )
        self.add_icon(
            key="mic",
            icon=self.ICON_MIC_ON,
            alt_icon=self.ICON_MIC_OFF,
            tooltip=trans('audio.speak.btn'),
            alt_tooltip=trans('audio.speak.btn.stop.tooltip'),
            callback=self.action_toggle_mic,
            visible=False,
        )

        # Apply initial margins (top padding + left space for icons)
        self._apply_margins()

    def _apply_text_top_padding(self):
        """Apply extra top padding inside the text area by using viewport margins."""
        # English: Left margin is computed in _apply_margins()
        self._apply_margins()

    def set_text_top_padding(self, px: int):
        """Public helper to adjust top padding at runtime."""
        self._text_top_padding = max(0, int(px))
        self._apply_margins()

    def insertFromMimeData(self, source):
        """
        Insert from mime data

        :param source: source
        """
        self.handle_clipboard(source)
        if not source.hasImage():
            super().insertFromMimeData(source)

    def handle_clipboard(self, source):
        """
        Handle clipboard

        :param source: source
        """
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
        elif source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path)
        elif source.hasText():
            text = source.text()
            if text:
                self.window.controller.attachment.from_clipboard_text(text)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: event
        """
        menu = self.createStandardContextMenu()
        try:
            if self.window.controller.attachment.clipboard_has_attachment():
                action = QAction(self.ICON_PASTE, trans("action.use.attachment"), menu)
                action.triggered.connect(self.action_from_clipboard)
                menu.addAction(action)

            cursor = self.textCursor()
            selected_text = cursor.selectedText()
            if selected_text:
                plain_text = cursor.selection().toPlainText()

                action = QAction(self.ICON_VOLUME, trans('text.context_menu.audio.read'), menu)
                action.triggered.connect(self.audio_read_selection)
                menu.addAction(action)

                copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text, excluded=["input"])
                menu.addMenu(copy_to_menu)

                action = QAction(self.ICON_SAVE, trans('action.save_selection_as'), menu)
                action.triggered.connect(lambda: self.window.controller.chat.common.save_text(plain_text))
                menu.addAction(action)
            else:
                action = QAction(self.ICON_SAVE, trans('action.save_as'), menu)
                action.triggered.connect(lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
                menu.addAction(action)

            try:
                self.window.core.prompt.template.to_menu_options(menu, "input")
                self.window.core.prompt.custom.to_menu_options(menu, "input")
            except Exception as e:
                self.window.core.debug.log(e)

            action = QAction(self.ICON_SAVE, trans('preset.prompt.save_custom'), menu)
            action.triggered.connect(self.window.controller.presets.save_prompt)
            menu.addAction(action)

            menu.exec(event.globalPos())
        finally:
            menu.deleteLater()

    def action_from_clipboard(self):
        """
        Get from clipboard
        """
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        self.handle_clipboard(source)

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        handled = False
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:
                modifiers = event.modifiers()
                if mode == 2:
                    if modifiers == Qt.ShiftModifier or modifiers == Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                        handled = True
                else:
                    if modifiers != Qt.ShiftModifier and modifiers != Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                        handled = True
                self.setFocus()
        elif key == Qt.Key_Escape and self.window.controller.ctx.extra.is_editing():
            self.window.controller.ctx.extra.edit_cancel()
            handled = True

        if not handled:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            prev = self.value
            dy = event.angleDelta().y()
            if dy > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            if self.value != prev:
                self.window.core.config.data['font_size.input'] = self.value
                self.window.core.config.save()
                self.window.controller.ui.update_font_size()
            event.accept()
            return
        super().wheelEvent(event)

    # -------------------- Attachment button (top-left) --------------------
    def _init_attachment_button(self):
        """Create and place the '+' attachment button pinned in the top-left corner."""
        # Deprecated – use _init_icon_bar() and add_icon(...).
        if not hasattr(self, "_icon_bar"):
            self._init_icon_bar()
        if "attach" not in self._icons:
            self.add_icon(
                key="attach",
                icon=self.ICON_ATTACHMENT,
                tooltip=trans("attachments.btn.input.add"),
                callback=self.action_add_attachment,
                visible=True,
            )

    def action_add_attachment(self):
        """Add attachment (button click)."""
        self.window.controller.attachment.open_add()

    def action_toggle_mic(self):
        """Toggle microphone (button click)."""
        self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE))

    # -------------------- Left icon bar  --------------------
    # - Add icons: add_icon(...) or add_icons([...])
    # - Show/hide: set_icon_visible(key, bool)
    # - Swap icon at runtime: set_icon_state(key, active) with optional alt_icon

    def _init_icon_bar(self):
        """Create the left-side icon bar pinned in the top-left corner."""
        self._icon_bar = QWidget(self)
        self._icon_bar.setObjectName("chatInputIconBar")

        # English: Keep styled background enabled so the style engine (Qt Material) can still
        # paint hover/pressed states on child buttons. We'll only make the BAR itself transparent.
        self._icon_bar.setAttribute(Qt.WA_StyledBackground, True)
        self._icon_bar.setAutoFillBackground(False)

        # English: Scope the rule to this object by its ID to avoid cascading 'background: transparent'
        # to child QPushButtons, which would kill their hover highlight in Qt Material.
        self._icon_bar.setStyleSheet("""
            #chatInputIconBar { background-color: transparent; }
        """)

        layout = QHBoxLayout(self._icon_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._icons_spacing)
        self._icon_bar.setLayout(layout)

        self._icon_bar.setFixedHeight(self._btn_size.height())
        self._icon_bar.show()  # make sure it's visible so children render

        self._reposition_icon_bar()
        self._update_icon_bar_geometry()
        self._apply_margins()

    # ---- Public API for icons ----

    def add_icon(
        self,
        key: str,
        icon: QIcon,
        tooltip: str = "",
        callback=None,
        visible: bool = True,
        alt_icon: Optional[QIcon] = None,
        alt_tooltip: Optional[str] = None,
    ) -> QPushButton:
        """
        Add a new icon button to the left bar.

        - key: unique identifier (string)
        - icon: default QIcon (e.g., mic off)
        - tooltip: default tooltip
        - callback: callable executed on click
        - visible: initial visibility
        - alt_icon: optional alternate icon (e.g., mic on / recording)
        - alt_tooltip: optional alternate tooltip
        """
        if key in self._icons:
            btn = self._icons[key]
            meta = self._icon_meta.get(key, {})
            meta.update({
                "icon": icon or meta.get("icon"),
                "alt_icon": alt_icon if alt_icon is not None else meta.get("alt_icon"),
                "tooltip": tooltip or meta.get("tooltip", key),
                "alt_tooltip": alt_tooltip if alt_tooltip is not None else meta.get("alt_tooltip"),
            })
            self._icon_meta[key] = meta
            btn.setIcon(meta["icon"])
            btn.setToolTip(meta["tooltip"])
            if callback is not None:
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(callback)
            btn.setHidden(not visible)
            self._sync_icon_order(key)
            self._rebuild_icon_layout()
            self._update_icon_bar_geometry()
            self._apply_margins()
            return btn

        btn = QPushButton(self._icon_bar)
        btn.setObjectName(f"chatInputIconBtn_{key}")
        btn.setIcon(icon)
        btn.setIconSize(self._icon_size)
        btn.setFixedSize(self._btn_size)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip or key)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFlat(True)  # flat button style like your original
        # optional: no text
        btn.setText("")

        if callback is not None:
            btn.clicked.connect(callback)

        self._icons[key] = btn
        self._icon_order.append(key)
        self._icon_meta[key] = {
            "icon": icon,
            "alt_icon": alt_icon,
            "tooltip": tooltip or key,
            "alt_tooltip": alt_tooltip,
            "active": False,
        }

        self._apply_icon_visual(key)
        btn.setHidden(not visible)

        self._rebuild_icon_layout()
        self._update_icon_bar_geometry()
        self._apply_margins()
        return btn

    def add_icons(self, items):
        """
        Add multiple icons at once.

        - items: iterable of tuples/dicts:
          tuple: (key, icon, tooltip, callback, visible=True, alt_icon=None, alt_tooltip=None)
          dict : {"key":..., "icon":..., "tooltip":..., "callback":..., "visible":True, "alt_icon":..., "alt_tooltip":...}
        """
        for it in items:
            if isinstance(it, dict):
                self.add_icon(
                    key=it["key"],
                    icon=it["icon"],
                    tooltip=it.get("tooltip", ""),
                    callback=it.get("callback"),
                    visible=it.get("visible", True),
                    alt_icon=it.get("alt_icon"),
                    alt_tooltip=it.get("alt_tooltip"),
                )
            else:
                key, icon = it[0], it[1]
                tooltip = it[2] if len(it) > 2 else ""
                callback = it[3] if len(it) > 3 else None
                visible = it[4] if len(it) > 4 else True
                alt_icon = it[5] if len(it) > 5 else None
                alt_tooltip = it[6] if len(it) > 6 else None
                self.add_icon(key, icon, tooltip, callback, visible, alt_icon, alt_tooltip)

    def remove_icon(self, key: str):
        """English: Remove an icon from the bar."""
        btn = self._icons.pop(key, None)
        self._icon_meta.pop(key, None)
        if btn is not None:
            try:
                self._icon_order.remove(key)
            except ValueError:
                pass
            btn.setParent(None)
            btn.deleteLater()
            self._rebuild_icon_layout()
            self._update_icon_bar_geometry()
            self._apply_margins()

    def set_icon_visible(self, key: str, visible: bool):
        """Show or hide an icon by key; margins are recalculated."""
        btn = self._icons.get(key)
        if not btn:
            return
        btn.setHidden(not visible)
        self._update_icon_bar_geometry()
        self._apply_margins()

    def toggle_icon(self, key: str):
        """Toggle icon visibility and recalc margins."""
        btn = self._icons.get(key)
        if not btn:
            return
        btn.setHidden(not btn.isHidden())
        self._update_icon_bar_geometry()
        self._apply_margins()

    def is_icon_visible(self, key: str) -> bool:
        """ Return True if icon is visible (not hidden)."""
        btn = self._icons.get(key)
        return bool(btn and not btn.isHidden())

    def set_icon_order(self, keys):
        """
        Set rendering order for icons by a list of keys.
        Icons not listed keep their relative order at the end.
        """
        new_order = []
        seen = set()
        for k in keys:
            if k in self._icons and k not in seen:
                new_order.append(k)
                seen.add(k)
        for k in self._icon_order:
            if k not in seen and k in self._icons:
                new_order.append(k)
        self._icon_order = new_order
        self._rebuild_icon_layout()
        self._update_icon_bar_geometry()
        self._apply_margins()

    # ---- Runtime icon swap / state API ----

    def set_icon_state(self, key: str, active: bool):
        """
        Switch between base icon and alt icon at runtime.
        - active=False -> show base icon/tooltip
        - active=True  -> show alt icon/tooltip (if provided; falls back to base icon if not)
        """
        if key not in self._icons:
            return
        meta = self._icon_meta.get(key, {})
        meta["active"] = bool(active)
        self._icon_meta[key] = meta
        self._apply_icon_visual(key)

    def toggle_icon_state(self, key: str) -> bool:
        """Toggle active state and return new state."""
        if key not in self._icons:
            return False
        current = bool(self._icon_meta.get(key, {}).get("active", False))
        self.set_icon_state(key, not current)
        return not current

    def set_icon_pixmap(self, key: str, icon: QIcon):
        """Replace base icon at runtime (does not touch alt icon)."""
        if key not in self._icons:
            return
        meta = self._icon_meta.get(key, {})
        meta["icon"] = icon
        self._icon_meta[key] = meta
        self._apply_icon_visual(key)

    def set_icon_alt(self, key: str, alt_icon: Optional[QIcon], alt_tooltip: Optional[str] = None):
        """Set/replace alternate icon and optional tooltip."""
        if key not in self._icons:
            return
        meta = self._icon_meta.get(key, {})
        meta["alt_icon"] = alt_icon
        if alt_tooltip is not None:
            meta["alt_tooltip"] = alt_tooltip
        self._icon_meta[key] = meta
        self._apply_icon_visual(key)

    def set_icon_tooltip(self, key: str, tooltip: str, for_alt: bool = False):
        """Update tooltip; for_alt=True updates alternate tooltip."""
        if key not in self._icons:
            return
        meta = self._icon_meta.get(key, {})
        if for_alt:
            meta["alt_tooltip"] = tooltip
        else:
            meta["tooltip"] = tooltip
        self._icon_meta[key] = meta
        self._apply_icon_visual(key)

    def set_icon_callback(self, key: str, callback):
        """Update click callback at runtime."""
        btn = self._icons.get(key)
        if not btn:
            return
        try:
            btn.clicked.disconnect()
        except Exception:
            pass
        if callback is not None:
            btn.clicked.connect(callback)

    def get_icon_state(self, key: str) -> bool:
        """Return active state for icon (True if alt icon is displayed)."""
        return bool(self._icon_meta.get(key, {}).get("active", False))

    def get_icon_button(self, key: str) -> Optional[QPushButton]:
        """Return the underlying QPushButton for advanced customization."""
        return self._icons.get(key)

    # ---- Internal layout helpers ----

    def _apply_icon_visual(self, key: str):
        """Apply correct icon and tooltip based on meta state."""
        btn = self._icons.get(key)
        meta = self._icon_meta.get(key, {})
        if not btn or not meta:
            return
        active = meta.get("active", False)
        base_icon = meta.get("icon")
        alt_icon = meta.get("alt_icon")
        base_tt = meta.get("tooltip") or key
        alt_tt = meta.get("alt_tooltip") or base_tt

        use_alt = active and isinstance(alt_icon, QIcon)
        btn.setIcon(alt_icon if use_alt else base_icon)
        btn.setToolTip(alt_tt if use_alt else base_tt)

    def _rebuild_icon_layout(self):
        """Rebuild the layout according to current _icon_order."""
        if not hasattr(self, "_icon_bar"):
            return
        layout = self._icon_bar.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                layout.removeWidget(w)
        for k in self._icon_order:
            btn = self._icons.get(k)
            if btn:
                layout.addWidget(btn)

    def _visible_buttons(self):
        """Helper to list icon buttons that are not hidden."""
        return [self._icons[k] for k in self._icon_order if k in self._icons and not self._icons[k].isHidden()]

    def _compute_icon_bar_width(self) -> int:
        """Compute width from button count to ensure padding before layout measures."""
        vis = self._visible_buttons()
        if not vis:
            return 0
        count = len(vis)
        w = count * self._btn_size.width() + (count - 1) * self._icons_spacing
        return w

    def _update_icon_bar_geometry(self):
        """Update the bar width and keep it raised above the text viewport."""
        if not hasattr(self, "_icon_bar"):
            return
        width = self._compute_icon_bar_width()
        self._icon_bar.setFixedWidth(max(0, width))
        self._icon_bar.raise_()
        self._reposition_icon_bar()

    def _reposition_icon_bar(self):
        """Keep the icon bar pinned to the top-left corner."""
        if hasattr(self, "_icon_bar"):
            fw = self.frameWidth()
            x = fw + self._icons_margin
            y = fw + self._icons_margin + self._icons_offset_y
            if y < 0:
                y = 0
            self._icon_bar.move(x, y)

    def _apply_margins(self):
        """Reserve left space for visible icons and apply top text padding."""
        left_space = self._compute_icon_bar_width()
        if left_space > 0:
            left_space += self._icons_margin * 2
        self.setViewportMargins(left_space, self._text_top_padding, 0, 0)

    def resizeEvent(self, event):
        """Resize event keeps the icon bar in place."""
        super().resizeEvent(event)
        try:
            self._reposition_icon_bar()
        except Exception:
            pass