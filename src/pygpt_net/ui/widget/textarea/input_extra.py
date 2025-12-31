#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 16:00:00                  #
# ================================================== #

import math
import os

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QAction, QIcon, QImage
from PySide6.QtWidgets import (
    QTextEdit,
    QApplication,
)

from pygpt_net.utils import trans
from pygpt_net.core.attachments.clipboard import AttachmentDropHandler


class ExtraInput(QTextEdit):

    ICON_PASTE = QIcon(":/icons/paste.svg")
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")

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
        self._text_top_padding = 10
        self.setProperty('class', 'layout-input')

        if self.window.core.platforms.is_windows():
            self._text_top_padding = 8

        # ---- Auto-resize config (input in splitter) ----
        self._auto_max_lines = 10  # max lines for auto-expansion
        self._auto_max_ratio = 0.25  # max fraction of main window height
        self._auto_debounce_ms = 0  # coalesce updates in next event loop turn
        self._auto_updating = False  # reentrancy guard
        self._splitter_resize_in_progress = False
        self._splitter_connected = False
        self._user_adjusting_splitter = False
        self._auto_pause_ms_after_user_drag = 350
        self._last_target_container_h = None

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_resize_tick)

        # Paste/input safety limits
        self._paste_max_chars = 1000000000  # hard cap to prevent pathological pastes from freezing/crashing

        # One-shot guard to avoid duplicate attachment processing on drops that also insert text.
        self._skip_clipboard_on_next_insert = False

        # Drag & Drop: add as attachments; do not insert file paths into text
        self._dnd_handler = AttachmentDropHandler(self.window, self, policy=AttachmentDropHandler.INPUT_MIX)

    def _on_text_changed_tokens(self):
        """Schedule token count update with debounce."""
        self._tokens_timer.start()

    def _apply_text_top_padding(self):
        """Apply extra top padding inside the text area by using viewport margins."""
        # Left margin is computed in _apply_margins()
        self._apply_margins()

    def set_text_top_padding(self, px: int):
        """
        Public helper to adjust top padding at runtime.

        :param px: padding in pixels
        """
        self._text_top_padding = max(0, int(px))
        self._apply_margins()

    def canInsertFromMimeData(self, source) -> bool:
        """
        Restrict accepted MIME types to safe, explicitly handled ones.
        This prevents Qt from trying to parse unknown/broken formats.
        """
        try:
            if source is None:
                return False
            return source.hasText() or source.hasUrls() or source.hasImage()
        except Exception:
            return False

    def _mime_has_local_file_urls(self, source) -> bool:
        """
        Detects whether mime data contains any local file/directory URLs.
        """
        try:
            if source and source.hasUrls():
                for url in source.urls():
                    if url.isLocalFile():
                        return True
        except Exception:
            pass
        return False

    def insertFromMimeData(self, source):
        """
        Insert from mime data

        :param source: source
        """
        has_local_files = self._mime_has_local_file_urls(source)

        # Avoid double-processing when drop is allowed to fall through to default insertion.
        should_skip = bool(getattr(self, "_skip_clipboard_on_next_insert", False))
        if should_skip:
            self._skip_clipboard_on_next_insert = False
        else:
            # Always process attachments first; never break input pipeline on errors.
            try:
                self.handle_clipboard(source)
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass

        # Do not insert textual representation for images nor local file URLs (including directories).
        try:
            if source and (source.hasImage() or has_local_files):
                return
        except Exception:
            pass

        # Insert only sanitized plain text (no HTML, no custom formats).
        try:
            text = self._safe_text_from_mime(source)
            if text:
                self.insertPlainText(text)
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass

    def _safe_text_from_mime(self, source) -> str:
        """
        Extracts plain text from QMimeData safely, normalizes and sanitizes it.
        Falls back to URLs joined by space only for non-local URLs.
        """
        try:
            if source is None:
                return ""
            # Prefer real text if present
            if source.hasText():
                return self._sanitize_text(source.text())
            # Fallback: for non-local URLs we allow insertion as text (e.g., http/https)
            if source.hasUrls():
                parts = []
                for url in source.urls():
                    try:
                        if url.isLocalFile():
                            # Skip local files/dirs textual fallback; they are handled as attachments
                            continue
                        parts.append(url.toString())
                    except Exception:
                        continue
                if parts:
                    return self._sanitize_text(" ".join([p for p in parts if p]))
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass
        return ""

    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize pasted text:
        - normalize newlines
        - remove NUL and most control chars except tab/newline
        - strip zero-width and bidi control characters
        - hard-cap maximum length to avoid UI freeze
        """
        if not text:
            return ""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""

        # Normalize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove disallowed control chars, keep tab/newline
        out = []
        for ch in text:
            code = ord(ch)
            if code == 0:
                continue  # NUL
            if code < 32:
                if ch in ("\n", "\t"):
                    out.append(ch)
                else:
                    out.append(" ")
                continue
            if code == 0x7F:
                continue  # DEL
            # Remove zero-width and bidi controls
            if (0x200B <= code <= 0x200F) or (0x202A <= code <= 0x202E) or (0x2066 <= code <= 0x2069):
                continue
            out.append(ch)

        s = "".join(out)

        # Cap very large pastes
        try:
            limit = int(self._paste_max_chars)
        except Exception:
            limit = 250000
        if limit > 0 and len(s) > limit:
            s = s[:limit]
            try:
                self.window.core.debug.log(f"Input paste truncated to {limit} chars")
            except Exception:
                pass

        return s

    def handle_clipboard(self, source):
        """
        Handle clipboard

        :param source: source
        """
        if source is None:
            return
        try:
            if source.hasImage():
                image = source.imageData()
                if isinstance(image, QImage):
                    self.window.controller.attachment.from_clipboard_image(image)
                else:
                    # Some platforms provide QPixmap; convert to QImage if possible
                    try:
                        img = image.toImage()
                        if isinstance(img, QImage):
                            self.window.controller.attachment.from_clipboard_image(img)
                    except Exception:
                        pass
            elif source.hasUrls():
                urls = source.urls()
                for url in urls:
                    try:
                        if url.isLocalFile():
                            local_path = url.toLocalFile()
                            if not local_path:
                                continue
                            if os.path.isdir(local_path):
                                # Recursively add all files from the dropped directory
                                for root, _, files in os.walk(local_path):
                                    for name in files:
                                        fpath = os.path.join(root, name)
                                        try:
                                            self.window.controller.attachment.from_clipboard_url(fpath, all=True)
                                        except Exception:
                                            continue
                            else:
                                self.window.controller.attachment.from_clipboard_url(local_path, all=True)
                        else:
                            # Non-local URLs are handled as text (if any) by _safe_text_from_mime
                            pass
                    except Exception:
                        # Ignore broken URL entries
                        continue
            elif source.hasText():
                text = self._sanitize_text(source.text())
                if text:
                    self.window.controller.attachment.from_clipboard_text(text)
        except Exception as e:
            # Never propagate clipboard errors to UI thread
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass

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
        """Paste from clipboard"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        self.handle_clipboard(source)

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event
        """
        handled = False
        key = event.key()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:
                mods = event.modifiers()
                has_shift_or_ctrl = bool(mods & (Qt.ShiftModifier | Qt.ControlModifier))

                if mode == 2:
                    if has_shift_or_ctrl:
                        self.window.controller.chat.input.send_input()
                        handled = True
                else:
                    if not has_shift_or_ctrl:
                        self.window.controller.chat.input.send_input()
                        handled = True

                self.setFocus()
                if handled:
                    QTimer.singleShot(0, self.collapse_to_min)

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
                # Reflow may change number of lines; adjust auto-height next tick
                QTimer.singleShot(0, self._schedule_auto_resize)
            event.accept()
            return
        super().wheelEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self._schedule_auto_resize()

    def resizeEvent(self, event):
        """Resize event keeps the icon bar in place."""
        super().resizeEvent(event)
        # Recompute on width changes (word wrap may change line count)
        if not self._splitter_resize_in_progress:
            if self.hasFocus():
                self._schedule_auto_resize()
            else:
                # Allow shrinking to minimum when content is single line
                self._schedule_auto_resize(enforce_minimize_if_single=True)

    # ================== Auto-resize inside QSplitter ==================

    def _ensure_splitter_hook(self):
        """Lazy-connect to main splitter to detect manual drags."""
        if self._splitter_connected:
            return
        splitter = self._get_main_splitter()
        if splitter is not None:
            try:
                splitter.splitterMoved.connect(self._on_splitter_moved_by_user)
                self._splitter_connected = True
            except Exception:
                pass

    def _on_splitter_moved_by_user(self, pos, index):
        """Pause auto-resize briefly while the user drags the splitter."""
        self._user_adjusting_splitter = True
        QTimer.singleShot(self._auto_pause_ms_after_user_drag, self._reset_user_adjusting_flag)

    def _reset_user_adjusting_flag(self):
        self._user_adjusting_splitter = False

    def _get_main_splitter(self):
        """Get main vertical splitter from window registry."""
        try:
            return self.window.ui.splitters.get('main.output')
        except Exception:
            return None

    def _find_container_in_splitter(self, splitter):
        """Find the direct child of splitter that contains this ChatInput."""
        if splitter is None:
            return None, -1
        for i in range(splitter.count()):
            w = splitter.widget(i)
            if w and w.isAncestorOf(self):
                return w, i
        return None, -1

    def _schedule_auto_resize(self, force: bool = False, enforce_minimize_if_single: bool = False):
        """Schedule auto-resize; multiple calls are coalesced."""
        # Store flags for the next tick
        self._pending_force = getattr(self, "_pending_force", False) or bool(force)
        self._pending_minimize_if_single = getattr(self, "_pending_minimize_if_single", False) or bool(
            enforce_minimize_if_single)
        # Avoid scheduling when splitter drag in progress
        if self._user_adjusting_splitter or self._splitter_resize_in_progress:
            return
        self._ensure_splitter_hook()
        # Debounce to next event loop to ensure document layout is up to date
        if not self._auto_timer.isActive():
            self._auto_timer.start(self._auto_debounce_ms)

    def _auto_resize_tick(self):
        """Execute auto-resize once after debounce."""
        force = getattr(self, "_pending_force", False)
        minimize_if_single = getattr(self, "_pending_minimize_if_single", False)
        self._pending_force = False
        self._pending_minimize_if_single = False
        try:
            self._update_auto_height(force=force, minimize_if_single=minimize_if_single)
        except Exception:
            # Never break input pipeline on errors
            pass

    def _document_content_height(self) -> int:
        """Return QTextDocument layout height in pixels."""
        doc = self.document()
        layout = doc.documentLayout()
        if layout is not None:
            h = layout.documentSize().height()
        else:
            h = doc.size().height()
        return int(math.ceil(h))

    def _line_spacing(self) -> int:
        """Return current line spacing for font."""
        return int(math.ceil(self.fontMetrics().lineSpacing()))

    def _effective_lines(self, doc_h: int, line_h: int, doc_margin: float) -> float:
        """Rough estimate of visible line count from document height."""
        base = max(0.0, doc_h - 2.0 * float(doc_margin))
        if line_h <= 0:
            return 1.0
        return max(1.0, base / float(line_h))

    def _min_input_widget_height(self, non_viewport_h: int) -> int:
        """Height of QTextEdit widget required to fit a single line without scrollbars."""
        line_h = self._line_spacing()
        doc_margin = float(self.document().documentMargin())
        min_viewport_h = int(math.ceil(2.0 * doc_margin + line_h))
        # Respect current minimum size hint to avoid jitter on some styles
        min_hint = max(self.minimumSizeHint().height(), 0)
        return max(min_hint, min_viewport_h + non_viewport_h)

    def _max_input_widget_height_by_lines(self, non_viewport_h: int) -> int:
        """Max widget height allowed by line count cap."""
        line_h = self._line_spacing()
        doc_margin = float(self.document().documentMargin())
        max_viewport_h = int(math.ceil(2.0 * doc_margin + self._auto_max_lines * line_h))
        return max_viewport_h + non_viewport_h

    def _should_shrink_to_min(self, doc_h: int) -> bool:
        """Decide if we should collapse to minimum (single line or empty)."""
        line_h = self._line_spacing()
        doc_margin = float(self.document().documentMargin())
        threshold = 2.0 * doc_margin + 1.25 * line_h  # small slack for layout rounding
        return doc_h <= threshold

    def _update_auto_height(self, force: bool = False, minimize_if_single: bool = False):
        """
        Core auto-resize routine:
        - expand only when the input has focus (unless force=True),
        - cap by max lines and 1/4 of main window height,
        - shrink back to minimal only after send or when text is effectively one line.
        """
        if self._auto_updating or self._splitter_resize_in_progress:
            return

        splitter = self._get_main_splitter()
        container, idx = self._find_container_in_splitter(splitter)
        if splitter is None or container is None or idx < 0:
            return  # Not yet attached to the splitter

        # Expansion only with focus unless forced
        has_focus = self.hasFocus()
        can_expand = force or has_focus
        if self._user_adjusting_splitter and not force:
            return

        # Measure current layout and targets
        doc_h = self._document_content_height()
        non_viewport_h = self.height() - self.viewport().height()
        needed_input_h = int(math.ceil(doc_h + non_viewport_h))
        min_input_h = self._min_input_widget_height(non_viewport_h)
        max_input_by_lines = self._max_input_widget_height_by_lines(non_viewport_h)

        # Container overhead above the inner QTextEdit
        container_overhead = max(0, container.height() - self.height())
        needed_container_h = needed_input_h + container_overhead
        min_container_h = min_input_h + container_overhead

        # Max cap by window fraction
        try:
            max_container_by_ratio = int(self.window.height() * self._auto_max_ratio)
        except Exception:
            max_container_by_ratio = 0  # fallback disables ratio cap if window unavailable

        max_container_by_lines = max_input_by_lines + container_overhead
        cap_container_max = max_container_by_lines
        if max_container_by_ratio > 0:
            cap_container_max = min(cap_container_max, max_container_by_ratio)

        current_sizes = splitter.sizes()
        if idx >= len(current_sizes):
            return
        current_container_h = current_sizes[idx]

        # Decide on action
        target_container_h = None

        # Shrink only when requested or effectively single line
        if minimize_if_single or self._should_shrink_to_min(doc_h):
            if current_container_h > min_container_h + 1:
                target_container_h = min_container_h

        # Expand if focused (or forced), but only up to caps
        elif can_expand:
            desired = min(needed_container_h, cap_container_max)
            if desired > current_container_h + 1:
                target_container_h = desired

        # Apply if needed
        if target_container_h is None:
            return

        total = sum(current_sizes)
        # Clamp to splitter total height
        target_container_h = max(0, min(target_container_h, total))

        if abs(target_container_h - current_container_h) <= 1:
            return

        # Prepare new sizes (2 widgets expected: output at 0, input at 1)
        new_sizes = list(current_sizes)
        # Distribute delta to other panes; here we have exactly 2
        other_total = total - current_container_h
        new_other_total = total - target_container_h
        if other_total <= 0:
            # degenerate case; just set directly
            pass
        else:
            # Scale other widgets proportionally
            scale = new_other_total / float(other_total) if other_total > 0 else 1.0
            for i in range(len(new_sizes)):
                if i != idx:
                    new_sizes[i] = int(round(new_sizes[i] * scale))
        new_sizes[idx] = int(target_container_h)

        # Final clamp to preserve sum
        diff = total - sum(new_sizes)
        if diff != 0 and len(new_sizes) > 0:
            # Adjust the first non-target pane to fix rounding
            for i in range(len(new_sizes)):
                if i != idx:
                    new_sizes[i] += diff
                    break

        self._splitter_resize_in_progress = True
        try:
            old_block = splitter.blockSignals(True)
            splitter.setSizes(new_sizes)
            splitter.blockSignals(old_block)
        finally:
            self._splitter_resize_in_progress = False

        # Keep stored sizes in sync with app expectations (mirrors ChatMain.on_splitter_moved)
        try:
            tabs = self.window.ui.tabs
            if "input" in tabs:
                t_idx = tabs['input'].currentIndex()
                if t_idx != 0:
                    self.window.controller.ui.splitter_output_size_files = new_sizes
                else:
                    self.window.controller.ui.splitter_output_size_input = new_sizes
        except Exception:
            pass

        self._last_target_container_h = target_container_h

    def collapse_to_min(self):
        """Public helper to collapse input area to minimal height."""
        self._schedule_auto_resize(force=True, enforce_minimize_if_single=True)