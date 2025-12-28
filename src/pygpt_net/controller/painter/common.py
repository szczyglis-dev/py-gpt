#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 15:00:00                  #
# ================================================== #

from typing import Tuple, Optional, Dict, List

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox


class Common:
    def __init__(self, window=None):
        """
        Painter common methods controller

        :param window: Window instance
        """
        self.window = window
        # Guard to prevent re-entrancy when programmatically changing the combo/size
        self._changing_canvas_size = False
        # Cached set for predefined canvas sizes
        self._predef_canvas_sizes_set = None
        # Sticky custom value derived from the current "source" image (kept at index 0 when present)
        self._sticky_custom_value: Optional[str] = None

    def convert_to_size(self, canvas_size: str) -> Tuple[int, int]:
        """
        Convert string to size

        :param canvas_size: Canvas size string
        :return: tuple (width, height)
        """
        return tuple(map(int, canvas_size.split('x'))) if canvas_size else (0, 0)

    def set_canvas_size(self, width: int, height: int):
        """
        Set canvas size

        :param width: Canvas width
        :param height: Canvas height
        """
        painter = self.window.ui.painter
        if hasattr(painter, "set_canvas_size_pixels"):
            painter.set_canvas_size_pixels(width, height)
        else:
            # required on image open
            self.window.ui.painter.setFixedSize(QSize(width, height))

    def set_brush_mode(self, enabled: bool):
        """
        Set the paint mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.set_mode("brush")
            self.window.core.config.set('painter.brush.mode', "brush")
            self.window.core.config.save()

    def set_erase_mode(self, enabled: bool):
        """
        Set the erase mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.set_mode("erase")
            self.window.core.config.set('painter.brush.mode', "erase")
            self.window.core.config.save()

    def change_canvas_size(self, selected: Optional[str] = None):
        """
        Change the canvas size

        :param selected: Selected size
        """
        # Re-entrancy guard to avoid loops when we adjust the combo programmatically
        if self._changing_canvas_size:
            return

        # Be resilient if combobox node is not present in a given UI layout
        combo: Optional[QComboBox] = None
        try:
            if hasattr(self.window.ui, "nodes"):
                combo = self.window.ui.nodes.get('painter.select.canvas.size', None)
        except Exception:
            combo = None

        painter = self.window.ui.painter

        # Heuristic to detect manual UI change vs programmatic call
        # - manual if: no arg, or int index (Qt int overload), or arg equals currentText/currentData
        raw_arg = selected
        current_text = combo.currentText() if combo is not None else ""
        current_data = combo.currentData() if combo is not None else None
        current_data_str = current_data if isinstance(current_data, str) else None
        is_manual = (
            raw_arg is None
            or isinstance(raw_arg, int)
            or (isinstance(raw_arg, str) and (raw_arg == current_text or (current_data_str and raw_arg == current_data_str)))
        )

        # Resolve selection if not passed explicitly; fallback to currentText if userData is missing
        if not selected:
            selected = current_data_str or current_text

        # Normalize to "WxH" strictly; if invalid, do nothing
        selected_norm = self._normalize_canvas_value(selected)
        if not selected_norm:
            return

        # Use true logical canvas size when available
        if hasattr(painter, "get_canvas_size"):
            cur_sz = painter.get_canvas_size()
            cur_val = f"{cur_sz.width()}x{cur_sz.height()}"
        else:
            cur_val = f"{painter.width()}x{painter.height()}"

        # Save undo only for manual changes and only if size will change
        will_change = selected_norm != cur_val
        if is_manual and will_change:
            painter.saveForUndo()

        try:
            self._changing_canvas_size = True

            predef = self._get_predef_canvas_set()

            # Sticky custom update only for programmatic (source-driven) changes
            programmatic = not is_manual
            if programmatic:
                if selected_norm in predef:
                    self._sticky_custom_value = None
                else:
                    self._sticky_custom_value = selected_norm

            # Ensure combo reflects single custom at index 0 (sticky respected), then select current value
            if combo is not None:
                self._sync_canvas_size_combo(combo, selected_norm, sticky_to_keep=self._sticky_custom_value)

            # Apply canvas size; PainterWidget handles rescaling in its own logic
            w, h = self.convert_to_size(selected_norm)
            self.set_canvas_size(w, h)

            # Persist normalized value
            self.window.core.config.set('painter.canvas.size', selected_norm)
            self.window.core.config.save()
        finally:
            self._changing_canvas_size = False

    def change_brush_size(self, size: int):
        """
        Change the brush size

        :param size: Brush size
        """
        size = int(size)
        self.update_brush_size(size)
        self.window.core.config.set('painter.brush.size', size)
        self.window.core.config.save()

    def change_brush_color(self):
        """Change the brush color"""
        color = self.window.ui.nodes['painter.select.brush.color'].currentData()
        text_color = self.window.ui.nodes['painter.select.brush.color'].currentText()
        self.update_brush_color(color)
        self.window.core.config.set('painter.brush.color', text_color)
        self.window.core.config.save()

    def update_brush_size(self, size: int):
        """
        Update brush size

        :param size: Brush size
        """
        self.window.ui.painter.set_brush_size(size)

    def update_brush_color(self, color: QColor):
        """
        Update brush color

        :param color: QColor
        """
        self.window.ui.painter.set_brush_color(color)

    def restore_brush_settings(self):
        """Restore brush settings"""
        brush_color = None
        if self.window.core.config.has('painter.brush.color'):
            brush_color = self.window.core.config.get('painter.brush.color', "Black")

        # mode
        if self.window.core.config.has('painter.brush.mode'):
            mode = self.window.core.config.get('painter.brush.mode', "brush")
            if mode == "brush":
                self.window.ui.nodes['painter.btn.brush'].setChecked(True)
                self.set_brush_mode(True)
            elif mode == "erase":
                self.window.ui.nodes['painter.btn.erase'].setChecked(True)
                self.set_erase_mode(True)
        # color
        if brush_color:
            color = self.get_colors().get(brush_color)
            self.window.ui.nodes['painter.select.brush.color'].setCurrentText(brush_color)
            self.update_brush_color(color)

        # size
        size = 3
        if self.window.core.config.has('painter.brush.size'):
            size = int(self.window.core.config.get('painter.brush.size', 3))
        self.window.ui.nodes['painter.select.brush.size'].setCurrentIndex(
            self.window.ui.nodes['painter.select.brush.size'].findText(str(size))
        )

    def restore_zoom(self):
        """Restore zoom from config"""
        if self.window.core.config.has('painter.zoom'):
            zoom = int(self.window.core.config.get('painter.zoom', 100))
            self.window.ui.painter.set_zoom_percent(zoom)

    def save_zoom(self):
        """Save zoom to config"""
        zoom = self.window.ui.painter.get_zoom_percent()
        self.window.core.config.set('painter.zoom', zoom)
        self.window.core.config.save()

    def get_colors(self) -> Dict[str, QColor]:
        """
        Get colors dict

        :return: colors dict
        """
        return {
            "Black": Qt.black,
            "White": Qt.white,
            "Red": Qt.red,
            "Orange": QColor('orange'),
            "Yellow": Qt.yellow,
            "Green": Qt.green,
            "Blue": Qt.blue,
            "Indigo": QColor('indigo'),
            "Violet": QColor('violet')
        }

    def get_sizes(self) -> List[str]:
        """
        Get brush sizes

        :return: list of sizes
        """
        return ['1', '2', '3', '5', '8', '12', '15', '20', '25', '30', '50', '100', '200']

    def get_canvas_sizes(self) -> List[str]:
        """
        Get canvas sizes

        :return: list of sizes
        """
        return [
            # horizontal
            "640x480", "800x600", "1024x768", "1280x720", "1600x900",
            "1920x1080", "2560x1440", "3840x2160", "4096x2160",
            # vertical
            "480x640", "600x800", "768x1024", "720x1280", "900x1600",
            "1080x1920", "1440x2560", "2160x3840", "2160x4096"
        ]

    def get_capture_dir(self) -> str:
        """
        Get capture directory

        :return: path to capture directory
        """
        return self.window.core.config.get_user_dir('capture')

    # ---------- Public sync helper (used by PainterWidget undo/redo) ----------

    def sync_canvas_combo_from_widget(self):
        """
        Sync the size combobox with current PainterWidget canvas size.
        Also derive sticky custom from the current source image if it is custom.
        This method does not change the canvas size (UI-only sync).
        """
        if self._changing_canvas_size:
            return

        combo: Optional[QComboBox] = None
        try:
            if hasattr(self.window.ui, "nodes"):
                combo = self.window.ui.nodes.get('painter.select.canvas.size', None)
        except Exception:
            combo = None

        painter = self.window.ui.painter

        # Use true logical canvas size, not widget size
        if hasattr(painter, "get_canvas_size"):
            sz = painter.get_canvas_size()
            canvas_value = f"{sz.width()}x{sz.height()}"
        else:
            canvas_value = f"{painter.width()}x{painter.height()}"

        canvas_norm = self._normalize_canvas_value(canvas_value)
        if not canvas_norm:
            return

        # Derive sticky from current source image (if custom)
        predef = self._get_predef_canvas_set()
        sticky = None
        if painter.sourceImageOriginal is not None and not painter.sourceImageOriginal.isNull():
            src_val = f"{painter.sourceImageOriginal.width()}x{painter.sourceImageOriginal.height()}"
            src_val = self._normalize_canvas_value(src_val)
            if src_val and src_val not in predef:
                sticky = src_val

        try:
            self._changing_canvas_size = True
            self._sticky_custom_value = sticky
            if combo is not None:
                self._sync_canvas_size_combo(combo, canvas_norm, sticky_to_keep=sticky)

            # Persist canvas size only (do not change sticky config-scope)
            self.window.core.config.set('painter.canvas.size', canvas_norm)
            self.window.core.config.save()
        finally:
            self._changing_canvas_size = False

    # ---------- Internal helpers ----------

    def _normalize_canvas_value(self, value: Optional[str]) -> Optional[str]:
        """
        Normalize arbitrary canvas string to canonical 'WxH'. Returns None if invalid.
        Accepts variants like ' 1024 x 768 ', '1024×768', etc.

        :param value: input value
        :return: normalized value or None
        """
        if not value:
            return None
        s = str(value).strip().lower().replace(' ', '').replace('×', 'x')
        if 'x' not in s:
            return None
        parts = s.split('x', 1)
        try:
            w = int(parts[0])
            h = int(parts[1])
        except Exception:
            return None
        if w <= 0 or h <= 0:
            return None
        return f"{w}x{h}"

    def _get_predef_canvas_set(self) -> set:
        """
        Return cached set of predefined sizes for O(1) lookups.

        :return: set of predefined sizes
        """
        if self._predef_canvas_sizes_set is None:
            self._predef_canvas_sizes_set = set(self.get_canvas_sizes())
        return self._predef_canvas_sizes_set

    def _find_index_for_value(self, combo: QComboBox, value: str) -> int:
        """
        Find index by userData first, then by text. Returns -1 if not found.

        :param combo: QComboBox
        :param value: value to find
        :return: index or -1
        """
        idx = combo.findData(value)
        if idx == -1:
            idx = combo.findText(value, Qt.MatchFixedString)
        return idx

    def _remove_extra_custom_items(self, combo: QComboBox, predef: set, keep_index: int = -1):
        """
        Remove all non-predefined items except one at keep_index (if set).

        :param combo: QComboBox
        :param predef: set of predefined values
        :param keep_index: index to keep even if custom, or -1 to remove all custom
        """
        for i in range(combo.count() - 1, -1, -1):
            if i == keep_index:
                continue
            txt = combo.itemText(i)
            if txt not in predef:
                combo.removeItem(i)

    def _ensure_custom_index0(self, combo: QComboBox, custom_value: str, predef: set):
        """
        Ensure exactly one custom item exists at index 0 with given value.

        :param combo: QComboBox
        :param custom_value: custom value to set at index 0
        :param predef: set of predefined values
        """
        if combo.count() > 0 and combo.itemText(0) not in predef:
            if combo.itemText(0) != custom_value:
                combo.setItemText(0, custom_value)
                combo.setItemData(0, custom_value)
        else:
            combo.insertItem(0, custom_value, custom_value)
        self._remove_extra_custom_items(combo, predef, keep_index=0)

    def _sync_canvas_size_combo(self, combo: QComboBox, value: str, sticky_to_keep: Optional[str]):
        """
        Enforce invariant and selection:
        - If sticky_to_keep is a custom value -> keep it as single custom item at index 0.
        - If sticky_to_keep is None -> remove all custom items.
        - Select 'value' in the combo. If value is custom and sticky_to_keep differs or is None,
          ensure index 0 matches 'value' and select it.

        :param combo: QComboBox
        :param value: current canvas size value to select
        :param sticky_to_keep: sticky custom value to keep at index 0, or None
        """
        predef = self._get_predef_canvas_set()

        # Maintain sticky custom slot (index 0) if provided
        if sticky_to_keep and sticky_to_keep not in predef:
            self._ensure_custom_index0(combo, sticky_to_keep, predef)
        else:
            self._remove_extra_custom_items(combo, predef, keep_index=-1)

        # Select the current canvas value
        if value in predef:
            idx = self._find_index_for_value(combo, value)
            if idx != -1 and idx != combo.currentIndex():
                combo.setCurrentIndex(idx)
            elif idx == -1:
                # Fallback: set text (should not normally happen if combo prepopulates predefined sizes)
                combo.setCurrentText(value)
        else:
            # Current value is custom: ensure it exists at index 0 and select it
            if not sticky_to_keep or sticky_to_keep != value:
                self._ensure_custom_index0(combo, value, predef)
            if combo.currentIndex() != 0:
                combo.setCurrentIndex(0)