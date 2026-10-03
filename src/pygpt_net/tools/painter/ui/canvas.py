#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

import math

from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPen, QAction, QActionGroup, QIcon, QColor, QCursor, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget, QApplication

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.painter.core.modes import (
    DrawMode,
    DRAW_MODE_ORDER,
    DRAW_MODE_TRANSLATION_KEYS,
    DRAW_MODE_ICONS,
    create_draw_mode_handlers,
)
from pygpt_net.utils import trans

from ..core.document import Document
from ..core.history import History
from ..core.selection import Selection
from ..core.viewport import Viewport
from ..core.files import Files
from ..core.clipboard import Clipboard

class PainterWidget(QWidget):
    # Emitted whenever zoom changes; payload is zoom factor (e.g. 1.0 for 100%)
    zoomChanged = Signal(float)

    def __init__(self, tool):
        super().__init__(tool.window)
        self.window = tool.window
        self.tool = tool
        self.document = Document(self)
        self.history = History(self)
        self.selection = Selection(self)
        self.viewport = Viewport(self)
        self.files = Files(self)
        self.clipboard = Clipboard(self)

        # Drawing state
        self.drawing = False
        self._mouseDown = False
        self.brushSize = 3
        self.brushColor = Qt.black
        self._mode = "brush"  # paint tool: "brush" or "erase"
        self._drawMode = DrawMode.FREE
        self._drawHandlers = create_draw_mode_handlers()
        self.text = self._drawHandlers[DrawMode.TEXT]
        self._activeDrawHandler = None
        self._drawTransactionSnapshot = None
        self.lastPointCanvas = QPoint()  # kept for API compatibility
        self._pen = QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.installEventFilter(self)

        self.tab = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_StaticContents, True)

        # Internal flags
        self._ignoreResizeOnce = False   # guard to prevent recursive work in resize path

        # Actions
        self._act_undo = QAction(QIcon(":/icons/undo.svg"), trans('action.undo'), self)
        self._act_undo.triggered.connect(self.history.undo)

        self._act_redo = QAction(QIcon(":/icons/redo.svg"), trans('action.redo'), self)
        self._act_redo.triggered.connect(self.history.redo)

        self._act_copy = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
        self._act_copy.triggered.connect(self.clipboard.copy)

        self._act_paste = QAction(QIcon(":/icons/paste.svg"), trans('action.paste'), self)
        self._act_paste.triggered.connect(self.clipboard.paste)

        self._act_open = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open'), self)
        self._act_open.triggered.connect(self.files.open_dialog)

        self._act_capture = QAction(QIcon(":/icons/attachment.svg"), trans('painter.btn.capture'), self)
        self._act_capture.triggered.connect(self.action_capture)

        self._act_camera_capture = QAction(QIcon(":/icons/camera.svg"), trans('painter.btn.camera.capture'), self)
        self._act_camera_capture.triggered.connect(self.action_camera_capture)

        self._act_save = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        self._act_save.triggered.connect(self.files.save_dialog)

        self._act_clear = QAction(QIcon(":/icons/close.svg"), trans('painter.btn.clear'), self)
        self._act_clear.triggered.connect(self.action_clear)

        # Crop action (also add this QAction to your top toolbar if desired)
        self._act_crop = QAction(QIcon(":/icons/crop.svg"), trans('painter.btn.crop') if trans('painter.btn.crop') else "Crop", self)
        self._act_crop.triggered.connect(self.selection.start)

        # Fit action (trims letterbox and resizes canvas to the scaled image area)
        self._act_fit = QAction(QIcon(":/icons/fit.svg"), trans('painter.btn.fit') if trans('painter.btn.fit') else "Fit", self)
        self._act_fit.triggered.connect(self.selection.fit)

        # Drawing mode submenu
        self._draw_menu = QMenu(trans('painter.draw'), self)
        self._draw_action_group = QActionGroup(self)
        self._draw_action_group.setExclusive(True)
        self._draw_actions = {}
        for draw_mode in DRAW_MODE_ORDER:
            icon_path = DRAW_MODE_ICONS.get(draw_mode)
            if icon_path:
                action = QAction(
                    QIcon(icon_path),
                    trans(DRAW_MODE_TRANSLATION_KEYS[draw_mode]),
                    self,
                )
            else:
                action = QAction(trans(DRAW_MODE_TRANSLATION_KEYS[draw_mode]), self)
            action.setCheckable(True)
            action.setData(draw_mode.value)
            action.setChecked(draw_mode == self._drawMode)
            action.triggered.connect(
                lambda checked=False, mode=draw_mode: self._on_draw_mode_action(mode, checked)
            )
            self._draw_action_group.addAction(action)
            self._draw_menu.addAction(action)
            self._draw_actions[draw_mode] = action

        # Context menu
        self._ctx_menu = QMenu(self)
        self._ctx_menu.addAction(self._act_undo)
        self._ctx_menu.addAction(self._act_redo)
        self._ctx_menu.addSeparator()
        self._ctx_menu.addMenu(self._draw_menu)
        self._ctx_menu.addAction(self._act_crop)
        self._ctx_menu.addAction(self._act_fit)
        self._ctx_menu.addSeparator()
        self._ctx_menu.addAction(self._act_capture)
        self._ctx_menu.addSeparator()
        self._ctx_menu.addAction(self._act_open)
        self._ctx_menu.addAction(self._act_camera_capture)
        self._ctx_menu.addAction(self._act_copy)
        self._ctx_menu.addAction(self._act_paste)
        self._ctx_menu.addAction(self._act_save)
        self._ctx_menu.addAction(self._act_clear)

        # Composite state: mark when self.document.image is out-of-date relative to layers

        # Allocate initial buffers
        self.document.ensure_layers()
        self.document.recompose()
        # Keep display size in sync with zoom (initially 1.0 => no change)
        self.viewport.update_widget_size_from_zoom()

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def bind_clipboard_shortcuts(self, container: QWidget, scroll_area=None):
        """
        Bind Painter keyboard shortcuts to the whole Painter tab.

        The empty part of QScrollArea is its viewport, not PainterWidget. Make
        that viewport focusable and watch its mouse/key events so Ctrl+C,
        Ctrl+V and Delete work after clicking anywhere in the Painter area.

        :param container: Painter tab container
        :param scroll_area: Painter QScrollArea
        """
        if container is None:
            return

        self._act_copy.setShortcuts(
            QKeySequence.keyBindings(QKeySequence.StandardKey.Copy)
        )
        self._act_copy.setShortcutContext(Qt.WidgetWithChildrenShortcut)

        self._act_paste.setShortcuts(
            QKeySequence.keyBindings(QKeySequence.StandardKey.Paste)
        )
        self._act_paste.setShortcutContext(Qt.WidgetWithChildrenShortcut)

        # Delete must not share the Clear QAction: while the in-place text editor
        # has focus it is a normal text-editing key, not a canvas-clear command.
        if getattr(self, '_act_delete_shortcut', None) is None:
            self._act_delete_shortcut = QAction(self)
            self._act_delete_shortcut.setShortcut(QKeySequence(Qt.Key_Delete))
            self._act_delete_shortcut.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            self._act_delete_shortcut.triggered.connect(self._handle_delete_shortcut_action)

        container.addAction(self._act_copy)
        container.addAction(self._act_paste)
        container.addAction(self._act_delete_shortcut)

        # Keep references because these objects are checked in eventFilter().
        self._shortcutContainer = container
        self._shortcutFocusWidgets = [container]
        container.setFocusPolicy(Qt.StrongFocus)
        container.installEventFilter(self)

        if scroll_area is not None:
            scroll_area.setFocusPolicy(Qt.StrongFocus)
            scroll_area.installEventFilter(self)
            self._shortcutFocusWidgets.append(scroll_area)

            viewport = scroll_area.viewport()
            if viewport is not None:
                viewport.setFocusPolicy(Qt.StrongFocus)
                viewport.installEventFilter(self)
                self._shortcutFocusWidgets.append(viewport)

    def _handle_delete_shortcut_action(self):
        """Handle the tab-wide Delete shortcut without stealing Delete from text editing."""
        if self.text.delete_at_cursor(self):
            return
        self.action_clear()

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        self._act_undo.setEnabled(self.history.can_undo())
        self._act_redo.setEnabled(self.history.can_redo())

        # Enable paste based on clipboard; avoid heavy 'fit' checks here to keep menu snappy
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        self._act_paste.setEnabled(bool(mime_data.hasImage()))

        # Keep Fit enabled; the action validates availability when executed
        self._act_fit.setEnabled(True)
        self.sync_draw_mode_actions()

        self._ctx_menu.exec(event.globalPos())

    def action_capture(self):
        """Use an image from the current capture source."""
        self.history.push()
        self.tool.capture.use()

    def action_camera_capture(self):
        """Capture an image from the camera."""
        self.tool.capture.camera()

    def action_clear(self):
        """Clear the image"""
        self.text.cancel(self)
        self.history.push()
        self.document.clear()
        self.document.original_image = self.document.image

    def _on_draw_mode_action(self, mode: DrawMode, checked: bool = True):
        """Handle a drawing mode selected from the Painter context menu."""
        if not checked:
            return
        common = self.tool.settings if self.tool else None
        if common is not None:
            common.change_draw_mode(mode.value)
        else:
            self.set_draw_mode(mode)

    def get_draw_mode(self) -> DrawMode:
        """Return the currently selected drawing mode."""
        return self._drawMode

    def set_draw_mode(self, mode):
        """Set the current drawing mode using a stable DrawMode ID."""
        mode = DrawMode.from_value(mode)
        if self.text.has_active() and mode != DrawMode.TEXT:
            self.text.commit(self)
        if self.drawing:
            self.cancel_active_drawing()
        self._drawMode = mode
        if self._mode == "brush":
            cursor = Qt.IBeamCursor if mode == DrawMode.TEXT else Qt.CrossCursor
            self.setCursor(QCursor(cursor))
        self.sync_draw_mode_actions()
        self.update()

    def sync_draw_mode_actions(self):
        """Keep context-menu checkmarks synchronized with the active mode."""
        for mode, action in self._draw_actions.items():
            action.blockSignals(True)
            action.setChecked(mode == self._drawMode)
            action.blockSignals(False)

    def retranslate_draw_modes(self):
        """Refresh Painter RMB actions and drawing mode labels at runtime."""
        action_keys = {
            self._act_undo: 'action.undo',
            self._act_redo: 'action.redo',
            self._act_copy: 'action.copy',
            self._act_paste: 'action.paste',
            self._act_open: 'action.open',
            self._act_capture: 'painter.btn.capture',
            self._act_camera_capture: 'painter.btn.camera.capture',
            self._act_save: 'img.action.save',
            self._act_clear: 'painter.btn.clear',
            self._act_crop: 'painter.btn.crop',
            self._act_fit: 'painter.btn.fit',
        }
        for action, key in action_keys.items():
            action.setText(trans(key))

        self._draw_menu.setTitle(trans('painter.draw'))
        for mode, action in self._draw_actions.items():
            action.setText(trans(DRAW_MODE_TRANSLATION_KEYS[mode]))

    def _begin_draw_transaction(self):
        """Capture the pre-gesture state; the snapshot enters UNDO only on commit."""
        self.document.ensure_layers()
        self.document.compose()
        self._drawTransactionSnapshot = self.history.snapshot_state()

    def _commit_draw_transaction(self):
        """Commit the current drawing gesture as one UNDO step."""
        if self._drawTransactionSnapshot is not None:
            self.history.undo_stack.append(self._drawTransactionSnapshot)
            self.history.redo_stack.clear()
        self._drawTransactionSnapshot = None
        self.drawing = False

    def _cancel_draw_transaction(self):
        """Restore the pre-gesture state without creating an UNDO/REDO entry."""
        state = self._drawTransactionSnapshot
        self._drawTransactionSnapshot = None
        if state is not None:
            self.history.apply_state(state)
        self.drawing = False

    def _effective_draw_handler(self):
        """Eraser always behaves freehand; paint uses the selected drawing mode."""
        mode = DrawMode.FREE if self._mode == "erase" else self._drawMode
        return self._drawHandlers.get(mode)

    def cancel_active_drawing(self):
        """Cancel an in-progress drawing gesture (used by ESC and mode changes)."""
        handler = self._activeDrawHandler
        if handler is not None and handler.active:
            handler.cancel(self)
        elif self._drawTransactionSnapshot is not None:
            self._cancel_draw_transaction()
        self._activeDrawHandler = None
        self._mouseDown = False
        try:
            self.releaseMouse()
        except Exception:
            pass
        self.update()

    def set_mode(self, mode: str):
        """
        Set painting mode: "brush" or "erase"

        :param mode: Mode
        """
        if mode not in ("brush", "erase"):
            return
        if mode == "erase" and self.text.has_active():
            self.text.commit(self)
        self._mode = mode
        if self._mode == "erase":
            self.setCursor(QCursor(Qt.PointingHandCursor))
        elif self._drawMode == DrawMode.TEXT:
            self.setCursor(QCursor(Qt.IBeamCursor))
        else:
            self.setCursor(QCursor(Qt.CrossCursor))

    def set_brush_color(self, color):
        """
        Set the brush color

        :param color: Color
        """
        self.brushColor = color
        self._pen.setColor(color)
        self.text.set_color(self, color, refocus=True)

    def set_brush_size(self, size):
        """
        Set the brush size

        :param size: Brush size
        """
        self.brushSize = size
        self._pen.setWidth(size)
        self.text.set_font_size(self, size, refocus=True)

    def wheelEvent(self, event):
        """
        While LMB drawing: wheel changes brush/shape size in real time.
        Otherwise CTRL + wheel controls zoom.

        :param event: Event
        """
        delta = event.angleDelta().y()
        if self.text.has_active() and delta != 0:
            self.text.step_size(self, 1 if delta > 0 else -1)
            event.accept()
            return

        if self._mouseDown and self.drawing and delta != 0:
            common = self.tool.settings if self.tool else None
            if common is not None:
                common.step_brush_size(1 if delta > 0 else -1)
            self.update()
            event.accept()
            return

        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            if delta > 0:
                self.viewport.zoom_in_step()
            elif delta < 0:
                self.viewport.zoom_out_step()
            event.accept()
            return
        super().wheelEvent(event)

    def _dirty_canvas_rect_for_point(self, pt_canvas: QPoint, pen_width: int) -> QRect:
        """Compute dirty canvas rect around a single painted point."""
        r = max(1, int(math.ceil(pen_width / 2))) + 2
        return QRect(pt_canvas.x() - r, pt_canvas.y() - r, 2 * r + 1, 2 * r + 1)

    def _dirty_canvas_rect_for_segment(self, a: QPoint, b: QPoint, pen_width: int) -> QRect:
        """Compute dirty canvas rect for a line segment between two canvas points."""
        x1 = min(a.x(), b.x())
        y1 = min(a.y(), b.y())
        x2 = max(a.x(), b.x())
        y2 = max(a.y(), b.y())
        pad = max(1, int(math.ceil(pen_width / 2))) + 2
        return QRect(x1 - pad, y1 - pad, (x2 - x1) + 2 * pad + 1, (y2 - y1) + 2 * pad + 1)

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        # Middle button: start panning if scrollable
        if event.button() == Qt.MiddleButton:
            if not (self.selection.active and self.selection.selecting) and not self.drawing and self.viewport.can_pan():
                gp = event.globalPosition().toPoint()
                self.viewport.start_pan(gp)
                event.accept()
                return

        if event.button() == Qt.LeftButton:
            self._mouseDown = True
            self.setFocus(Qt.MouseFocusReason)

            # Clicking outside the live editor commits the complete block.
            # The same click is consumed; a second click starts another block.
            if self.text.has_active():
                self._mouseDown = False
                self.text.commit(self)
                event.accept()
                return

            if self.selection.active:
                self.history.push()
                self.selection.selecting = True
                self.selection.start_point = self.viewport.to_canvas_point(event.position())
                self.selection.rect = QRect(self.selection.start_point, self.selection.start_point)
                self.update()
                self.grabMouse()
                self.viewport.start_autoscroll()
                return

            point = self.viewport.to_canvas_point(event.position())
            if self._mode != "erase" and self._drawMode == DrawMode.TEXT:
                self._mouseDown = False
                self.text.start_edit(self, point)
                event.accept()
                return

            self.document.ensure_layers()
            handler = self._effective_draw_handler()
            if handler is None:
                self._mouseDown = False
                event.accept()
                return
            self._activeDrawHandler = handler
            handler.begin(self, point)
            # Capture the complete drag even when the pointer leaves the canvas.
            self.grabMouse()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        # Update panning if active
        if self.viewport.panning and (event.buttons() & Qt.MiddleButton):
            gp = event.globalPosition().toPoint()
            self.viewport.update_pan(gp)
            event.accept()
            return

        if self.selection.active and self.selection.selecting and (event.buttons() & Qt.LeftButton):
            self.selection.rect = QRect(self.selection.start_point, self.viewport.to_canvas_point(event.position()))
            self.update()
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing and self._activeDrawHandler is not None:
            cur = self.viewport.to_canvas_point(event.position())
            self._activeDrawHandler.update(self, cur)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Mouse release event

        :param event: Event
        """
        # End panning on middle button release
        if event.button() == Qt.MiddleButton:
            self.viewport.end_pan()
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            self._mouseDown = False
            if self.selection.active and self.selection.selecting:
                self.selection.finish()
                event.accept()
                return

            if self.drawing and self._activeDrawHandler is not None:
                cur = self.viewport.to_canvas_point(event.position())
                handler = self._activeDrawHandler
                handler.release(self, cur)
                self._activeDrawHandler = None
                try:
                    self.releaseMouse()
                except Exception:
                    pass
                event.accept()
                return

        if event.button() == Qt.RightButton:
            self._mouseDown = False

        super().mouseReleaseEvent(event)

    def _handle_painter_shortcut(self, event) -> bool:
        """
        Handle Painter-wide keyboard shortcuts.

        :param event: key event
        :return: True if handled
        """
        if event.matches(QKeySequence.StandardKey.Copy):
            self.clipboard.copy()
            event.accept()
            return True
        if event.matches(QKeySequence.StandardKey.Paste):
            self.clipboard.paste()
            event.accept()
            return True
        if event.key() == Qt.Key_Delete and event.modifiers() == Qt.NoModifier:
            self._handle_delete_shortcut_action()
            event.accept()
            return True
        return False

    def keyPressEvent(self, event):
        """
        Key press event to handle shortcuts

        :param event: Event
        """
        if self._handle_painter_shortcut(event):
            return
        if event.key() == Qt.Key_Z and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.history.undo()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.selection.active and self.selection.selecting:
                self.selection.finish()
        elif event.key() == Qt.Key_Escape:
            if self.text.has_active():
                self.text.cancel(self)
            elif self.drawing:
                self.cancel_active_drawing()
            elif self.selection.active:
                self.selection.cancel()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """
        Paint event (draw)

        :param event: Event
        """
        # Ensure layers are valid; avoid recomposing the full image here.
        if self.document.base is None or self.document.drawing is None:
            self.document.ensure_layers()

        p = QPainter(self)

        # Paint only the region requested by Qt; map it to canvas to avoid scaling the whole image.
        target_rect = event.rect()
        if not target_rect.isNull():
            src_rect = self.viewport.widget_rect_to_canvas_rect(target_rect)
            if not src_rect.isNull():
                # Draw base
                p.drawImage(target_rect, self.document.base, src_rect)
                # Draw strokes on top
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.drawImage(target_rect, self.document.drawing, src_rect)

        # Draw transient vector-shape preview in logical canvas coordinates.
        if self.drawing and self._mode != "erase" and self._activeDrawHandler is not None:
            p.save()
            p.scale(self.viewport.zoom, self.viewport.zoom)
            self._activeDrawHandler.paint_preview(self, p)
            p.restore()

        # Draw crop overlay if active (convert canvas selection to display coords)
        if self.selection.active and not self.selection.rect.isNull():
            sel = self.selection.rect.normalized()
            sel_view = self.viewport.from_canvas_rect(sel)
            overlay = QColor(0, 0, 0, 120)
            W, H = self.width(), self.height()

            if sel_view.left() > 0:
                p.fillRect(0, 0, sel_view.left(), H, overlay)
            if sel_view.right() < W - 1:
                p.fillRect(sel_view.right() + 1, 0, W - (sel_view.right() + 1), H, overlay)
            if sel_view.top() > 0:
                p.fillRect(sel_view.left(), 0, sel_view.width(), sel_view.top(), overlay)
            if sel_view.bottom() < H - 1:
                p.fillRect(sel_view.left(), sel_view.bottom() + 1, sel_view.width(), H - (sel_view.bottom() + 1), overlay)

            p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
            p.drawRect(sel_view.adjusted(0, 0, -1, -1))

        p.end()
        # Leave self.document.image stale until explicitly requested; avoids recomposition on every frame.

    def resizeEvent(self, event):
        """
        Update layers on canvas size change; ignore layout/display resizes unless explicitly requested.
        Only two kinds of resizes are acted upon:
        - canvas resize requested via document.resize() -> document.resizing
        - display-only resizes initiated by zoom -> viewport.resizing
        Any other widget/layout resize will be ignored for canvas logic.
        """

        # Explicit logical canvas resize requested by controller
        if self.document.resizing:
            # Already updated document.canvas_size in setter; ensure display size is in sync
            self.viewport.update_widget_size_from_zoom()
            self.text.sync_geometry(self)
            super().resizeEvent(event)
            return

        # Display-only resize caused by zoom update: nothing to do with buffers
        if self.viewport.resizing:
            self.text.sync_geometry(self)
            self.update()
            super().resizeEvent(event)
            return

        # Ignore stray layout-driven resizes; enforce current display size from zoom
        self.viewport.update_widget_size_from_zoom()
        self.text.sync_geometry(self)
        self.update()
        super().resizeEvent(event)

    def eventFilter(self, source, event):
        """
        Focus and Painter-tab shortcut event filter.

        :param source: source
        :param event: event
        """
        event_type = event.type()

        shortcut_widgets = getattr(self, '_shortcutFocusWidgets', [])
        if source in shortcut_widgets:
            if event_type == event.Type.MouseButtonPress:
                # Clicking the empty QScrollArea viewport must give the Painter
                # tab keyboard focus instead of leaving it in another widget.
                source.setFocus(Qt.MouseFocusReason)
            elif event_type == event.Type.KeyPress:
                if self._handle_painter_shortcut(event):
                    return True

        if event_type == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)
