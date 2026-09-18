#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 14:40:00                  #
# ================================================== #

from typing import Optional, Union, Tuple
import math
import os

from PySide6.QtCore import Qt, QSize, QTimer, QEvent, QPoint, Property
from PySide6.QtGui import QAction, QIcon, QImage, QTextCursor, QTextCharFormat, QTextFormat, QColor
from PySide6.QtWidgets import (
    QTextEdit,
    QApplication,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QMenu,
)

from pygpt_net.core.events import Event
from pygpt_net.utils import trans
from pygpt_net.core.attachments.clipboard import AttachmentDropHandler, DirectoryPasteHandler
from pygpt_net.core.text.mentions import (
    KIND_ATTACHMENT,
    KIND_FILE_CONTEXT,
    decode_value as decode_mention_value,
    iter_tags as iter_mention_tags,
    label_for as mention_label_for,
    make_tag as make_mention_tag,
)
from pygpt_net.ui.widget.textarea.mention import MentionEntry, MentionPopup


class ChatInput(QTextEdit):

    REASONING_EFFORT_KEY = "reasoning_effort"

    MENTION_ID_PROP = QTextFormat.UserProperty + 201
    MENTION_KIND_PROP = QTextFormat.UserProperty + 202
    MENTION_VALUE_PROP = QTextFormat.UserProperty + 203
    MENTION_LABEL_PROP = QTextFormat.UserProperty + 204
    MENTION_SCAN_LIMIT = 5000

    ICON_PASTE = QIcon(":/icons/paste.svg")
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    # ICON_ATTACHMENT = QIcon(":/icons/add.svg")
    ICON_ATTACHMENT = QIcon(":/icons/attachment.svg")
    ICON_MIC_ON = QIcon(":/icons/mic.svg")
    ICON_MIC_OFF = QIcon(":/icons/mic_off.svg")
    ICON_WEB_ON = QIcon(":/icons/web_on.svg")
    ICON_WEB_OFF = QIcon(":/icons/web_off.svg")

    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super().__init__(window)
        self.window = window

        # Mention state. The actual durable value lives in QTextCharFormat user
        # properties; QSS controls only its visual color.
        self._mention_color = QColor("#39a85a")
        self._mention_formatting = False
        self._mention_loading = False
        self._mention_trigger_pos = None
        self._mention_entries = []
        self._mention_source_key = None
        self._mention_seq = 0
        self._mention_popup = MentionPopup(self)
        self._mention_popup.selected.connect(self._accept_mention_entry)

        self.setAcceptRichText(False)
        self.setPlaceholderText(trans("input.placeholder"))
        self.setFocus()
        self.value = self.window.core.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8
        self._text_top_padding = 10
        self.textChanged.connect(self.window.controller.ui.update_tokens)
        self.setProperty('class', 'layout-input')
        self.setObjectName('chatInput')

        if self.window.core.platforms.is_windows():
            self._text_top_padding = 8

        # --- Icon bar (left) settings ---
        # Settings controlling the left icon bar (spacing, sizes, margins)
        self._icons_margin = 6           # inner left/right padding around the bar
        self._icons_spacing = 4          # spacing between buttons
        self._icons_offset_y = -4        # small upward shift (visual alignment)
        self._icon_size = QSize(18, 18)  # icon size (matches original)
        self._btn_size = QSize(24, 24)   # button size (w x h), matches QPushButton

        # Independent sizes for the right-bottom icon bar
        self._icon_size_right = QSize(20, 20)  # slightly larger by default
        self._btn_size_right = QSize(26, 26)   # slightly larger by default

        # Independent padding/spacing/offset for the dedicated bottom controls row.
        # The row occupies its own band below the text viewport, so its controls
        # never reduce the usable text width.
        self._icons_margin_right = 6
        self._icons_spacing_right = 4
        self._icons_offset_x_right = 0
        self._icons_offset_y_right = 4

        # Storage for icon buttons and metadata
        self._icons = {}       # key -> QPushButton
        self._icon_meta = {}   # key -> {"icon": QIcon, "alt_icon": Optional[QIcon], "tooltip": str, "alt_tooltip": Optional[str], "active": bool}
        self._icon_order = []  # rendering order

        # Storage for right-bottom icon buttons and metadata
        self._icons_right = {}       # key -> QPushButton
        self._icon_meta_right = {}   # key -> meta as above
        self._icon_order_right = []  # rendering order for right bar
        self._right_text_buttons = set()  # non-icon buttons embedded in the right bar
        self._reasoning_effort_menu = None

        self._init_icon_bar()
        # Initialize the bottom-right icon bar (independent from the left one)
        self._init_icon_bar_right()

        # Add a "+" button in the top-left corner to add attachments
        self.add_icon(
            key="attach",
            icon=self.ICON_ATTACHMENT,
            tooltip=trans("attachments.btn.input.add"),
            callback=self.action_add_attachment,
            visible=True,
        )
        # Runtime reasoning-effort selector. It is shown only for models which
        # explicitly opt in and is placed immediately to the left of microphone.
        self.add_reasoning_effort_button()

        # Add a microphone button (hidden by default; shown when audio input is enabled)
        # Placed on the bottom-right icon bar
        self.add_right_icon(
            key="mic",
            icon=self.ICON_MIC_ON,
            alt_icon=self.ICON_MIC_OFF,
            tooltip=trans('audio.speak.btn'),
            alt_tooltip=trans('audio.speak.btn.stop.tooltip'),
            callback=self.action_toggle_mic,
            visible=False,
        )
        # Add a web search toggle button
        self.add_icon(
            key="web",
            icon=self.ICON_WEB_OFF,
            alt_icon=self.ICON_WEB_ON,
            tooltip=trans('icon.remote_tool.web.disabled'),
            alt_tooltip=trans('icon.remote_tool.web.enabled'),
            callback=self.action_toggle_web,
            visible=True,
        )

        # Apply initial margins (top padding + left icon space + dedicated
        # bottom controls row when any right-side controls are visible).
        self._apply_margins()
        self.update_reasoning_effort()

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

        self._tokens_timer = QTimer(self)
        self._tokens_timer.setSingleShot(True)
        self._tokens_timer.setInterval(1500)
        self._tokens_timer.timeout.connect(self.window.controller.ui.update_tokens)
        self.textChanged.connect(self._on_text_changed_tokens)
        self.textChanged.connect(self._on_mention_text_changed)
        self.cursorPositionChanged.connect(self._on_mention_cursor_changed)

        # Paste/input safety limits
        self._paste_max_chars = 1000000000  # hard cap to prevent pathological pastes from freezing/crashing

        # One-shot guard to avoid duplicate attachment processing on drops that also insert text.
        self._skip_clipboard_on_next_insert = False

        # Drag & Drop: add as attachments; do not insert file paths into text
        self._dnd_handler = AttachmentDropHandler(self.window, self, policy=AttachmentDropHandler.INPUT_MIX)
        self._directory_paste_handler = DirectoryPasteHandler(self.window, self)

        # --- History navigation (input prompts) ---
        # Stores sent prompts and allows keyboard navigation through the history.
        self._history = []  # list[str]
        self._history_limit = 30
        self._history_index = -1     # -1 when not navigating; otherwise index of current history item
        self._history_active = False
        self._history_saved_current = ""  # snapshot of the current typed text before entering history nav

    def _get_mention_color(self):
        return self._mention_color

    def _set_mention_color(self, color):
        """QSS-backed color for mention anchors inside the QTextEdit."""
        try:
            value = color if isinstance(color, QColor) else QColor(color)
            if not value.isValid():
                return
            self._mention_color = value
            if hasattr(self, "_mention_formatting"):
                QTimer.singleShot(0, self._refresh_mention_formats)
        except Exception:
            pass

    mentionColor = Property(QColor, _get_mention_color, _set_mention_color)

    @staticmethod
    def _cursor_selected_text(cursor: QTextCursor) -> str:
        """Return QTextCursor text with paragraph separators normalized to LF."""
        return cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")

    def _insert_plain_cursor(self, cursor: QTextCursor, text: str):
        """Insert plain text while keeping LF semantics predictable in QTextDocument."""
        if not text:
            return
        parts = str(text).split("\n")
        for idx, part in enumerate(parts):
            if part:
                cursor.insertText(part)
            if idx < len(parts) - 1:
                cursor.insertBlock()

    def _new_mention_format(self, entry: MentionEntry) -> QTextCharFormat:
        self._mention_seq += 1
        fmt = QTextCharFormat()
        fmt.setProperty(self.MENTION_ID_PROP, f"m{self._mention_seq}")
        fmt.setProperty(self.MENTION_KIND_PROP, entry.kind)
        fmt.setProperty(self.MENTION_VALUE_PROP, entry.value)
        fmt.setProperty(self.MENTION_LABEL_PROP, entry.label)
        fmt.setForeground(self._mention_color)
        fmt.setFontWeight(600)
        return fmt

    def _insert_mention_cursor(self, cursor: QTextCursor, entry: MentionEntry):
        fmt = self._new_mention_format(entry)
        cursor.insertText("@" + entry.label, fmt)
        # Never let subsequent normal typing inherit mention metadata.
        cursor.setCharFormat(QTextCharFormat())

    def _insert_serialized_cursor(self, cursor: QTextCursor, text: str):
        raw = str(text or "")
        last = 0
        for match in iter_mention_tags(raw):
            self._insert_plain_cursor(cursor, raw[last:match.start()])
            kind = str(match.group(1) or "").lower()
            value = decode_mention_value(match.group(2))
            label = mention_label_for(kind, value)
            if label:
                self._insert_mention_cursor(
                    cursor,
                    MentionEntry(
                        kind=kind,
                        label=label,
                        value=value,
                        is_dir=(kind == KIND_FILE_CONTEXT and value.replace("\\", "/").endswith("/")),
                    ),
                )
            else:
                self._insert_plain_cursor(cursor, match.group(0))
            last = match.end()
        self._insert_plain_cursor(cursor, raw[last:])

    def set_mention_text(self, text: str):
        """Set input from durable text, restoring mention metadata and styling."""
        self._mention_loading = True
        try:
            self._mention_popup.hide()
            self._mention_trigger_pos = None
            self._mention_source_key = None
            self.clear()
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self._insert_serialized_cursor(cursor, str(text or ""))
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
        finally:
            self._mention_loading = False
        self._refresh_mention_formats()
        self._schedule_auto_resize()

    def append_mention_text(self, text: str, separator: str = "\n"):
        """Append durable text while restoring any mention tags as UI anchors."""
        text = str(text or "").strip()
        if not text:
            return
        self._mention_loading = True
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            if self.toPlainText().strip():
                self._insert_plain_cursor(cursor, separator)
            self._insert_serialized_cursor(cursor, text)
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)
        finally:
            self._mention_loading = False
        self._refresh_mention_formats()
        self.setFocus()

    def _collect_mention_groups(self):
        """Collect contiguous QTextDocument fragments carrying the same mention id."""
        groups = []
        current = None
        block = self.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid():
                    fmt = fragment.charFormat()
                    mention_id = fmt.property(self.MENTION_ID_PROP)
                    if mention_id:
                        mention_id = str(mention_id)
                        kind = str(fmt.property(self.MENTION_KIND_PROP) or "")
                        value = str(fmt.property(self.MENTION_VALUE_PROP) or "")
                        label = str(fmt.property(self.MENTION_LABEL_PROP) or "")
                        start = fragment.position()
                        end = start + fragment.length()
                        if current is not None and current["id"] == mention_id and current["end"] == start:
                            current["end"] = end
                        else:
                            if current is not None:
                                groups.append(current)
                            current = {
                                "id": mention_id,
                                "kind": kind,
                                "value": value,
                                "label": label,
                                "start": start,
                                "end": end,
                            }
                    else:
                        if current is not None:
                            groups.append(current)
                            current = None
                iterator += 1
            if current is not None:
                groups.append(current)
                current = None
            block = block.next()
        return groups

    def _validate_mention_groups(self, clean_invalid: bool = False):
        valid = []
        invalid = []
        doc = self.document()
        for group in self._collect_mention_groups():
            kind = group["kind"]
            if kind not in (KIND_ATTACHMENT, KIND_FILE_CONTEXT) or not group["label"] or not group["value"]:
                invalid.append(group)
                continue
            cursor = QTextCursor(doc)
            cursor.setPosition(group["start"])
            cursor.setPosition(group["end"], QTextCursor.KeepAnchor)
            actual = self._cursor_selected_text(cursor)
            if actual == "@" + group["label"]:
                valid.append(group)
            else:
                invalid.append(group)

        if clean_invalid and invalid:
            for group in invalid:
                cursor = QTextCursor(doc)
                cursor.setPosition(group["start"])
                cursor.setPosition(group["end"], QTextCursor.KeepAnchor)
                cursor.setCharFormat(QTextCharFormat())
        return valid

    def _refresh_mention_formats(self):
        if self._mention_formatting or self._mention_loading:
            return
        self._mention_formatting = True
        try:
            valid = self._validate_mention_groups(clean_invalid=True)
            for group in valid:
                cursor = QTextCursor(self.document())
                cursor.setPosition(group["start"])
                cursor.setPosition(group["end"], QTextCursor.KeepAnchor)
                fmt = QTextCharFormat()
                fmt.setForeground(self._mention_color)
                fmt.setFontWeight(600)
                cursor.mergeCharFormat(fmt)
        finally:
            self._mention_formatting = False

    def serialize_mentions(self) -> str:
        """Return input text with valid UI mention anchors converted to model-facing tags."""
        valid = self._validate_mention_groups(clean_invalid=False)
        if not valid:
            return self.toPlainText()

        doc = self.document()
        result = []
        pos = 0
        for group in valid:
            if group["start"] < pos:
                continue
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.setPosition(group["start"], QTextCursor.KeepAnchor)
            result.append(self._cursor_selected_text(cursor))
            result.append(make_mention_tag(group["kind"], group["value"]))
            pos = group["end"]

        cursor = QTextCursor(doc)
        cursor.setPosition(pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        result.append(self._cursor_selected_text(cursor))
        return "".join(result)

    def _on_mention_text_changed(self):
        if self._mention_loading or self._mention_formatting:
            return
        self._refresh_mention_formats()
        QTimer.singleShot(0, self._refresh_mention_popup)

    def _on_mention_cursor_changed(self):
        if self._mention_loading:
            return
        QTimer.singleShot(0, self._refresh_mention_popup)

    def _find_mention_trigger(self):
        """Return (at_pos, end_pos, query) for the nearest live @ trigger."""
        current = self.textCursor()
        if current.hasSelection():
            return None
        block = current.block()
        block_start = block.position()
        probe = QTextCursor(current)
        at_cursor = None

        while probe.position() > block_start:
            probe.clearSelection()
            if not probe.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor):
                break
            char = self._cursor_selected_text(probe)
            if char == "@":
                at_cursor = QTextCursor(probe)
                break
            probe.setPosition(probe.selectionStart())

        if at_cursor is None:
            return None
        if at_cursor.charFormat().property(self.MENTION_ID_PROP):
            return None

        at_pos = at_cursor.selectionStart()
        end_pos = current.position()

        # Avoid triggering inside an e-mail/path/identifier: foo@bar, ./@name, etc.
        if at_pos > block_start:
            prev = QTextCursor(self.document())
            prev.setPosition(at_pos)
            prev.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            prev_char = self._cursor_selected_text(prev)
            if prev_char and (prev_char.isalnum() or prev_char in "_./\\-"):
                return None

        query_cursor = QTextCursor(self.document())
        query_cursor.setPosition(at_cursor.selectionEnd())
        query_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        query = self._cursor_selected_text(query_cursor)
        if "\n" in query or "\t" in query or len(query) > 200:
            return None
        return at_pos, end_pos, query

    def _get_mention_source_key(self):
        core = self.window.core
        try:
            mode = core.config.get("mode")
        except Exception:
            mode = None
        try:
            meta = core.ctx.get_current_meta()
        except Exception:
            meta = None
        return (
            mode,
            getattr(meta, "id", None),
            getattr(meta, "group_id", None),
        )

    def _build_mention_entries(self) -> list:
        entries = []
        seen = set()
        core = self.window.core
        mode = core.config.get("mode")
        meta = core.ctx.get_current_meta()

        attachment_items = []
        try:
            attachment_items.extend(core.attachments.get_all(mode, only_files=True).values())
        except Exception:
            pass
        try:
            attachment_items.extend(core.attachments.get_from_meta_ctx(mode, meta))
        except Exception:
            pass

        for item in attachment_items:
            extra = getattr(item, "extra", None)
            if isinstance(extra, dict) and extra.get("append_to_ctx", True) is False:
                continue
            name = str(getattr(item, "name", None) or "").strip()
            path = str(getattr(item, "path", None) or "").strip()
            if not name and path:
                name = os.path.basename(path.rstrip("/\\"))
            if not name or any(ch in name for ch in "\r\n\t"):
                continue
            key = (KIND_ATTACHMENT, name.casefold())
            if key in seen:
                continue
            seen.add(key)
            entries.append(MentionEntry(KIND_ATTACHMENT, name, name, False))

        try:
            root = core.filesystem.get_data_dir(ctx=meta, create=False)
        except Exception:
            root = None

        count = 0
        if root and os.path.isdir(root):
            root_abs = os.path.abspath(root)
            try:
                for current_root, dirs, files in os.walk(root_abs, followlinks=False):
                    dirs[:] = sorted(
                        [d for d in dirs if not os.path.islink(os.path.join(current_root, d))],
                        key=str.casefold,
                    )
                    files = sorted(files, key=str.casefold)

                    for name in dirs:
                        full = os.path.join(current_root, name)
                        rel = os.path.relpath(full, root_abs).replace(os.sep, "/").rstrip("/") + "/"
                        if any(ch in rel for ch in "\r\n\t"):
                            continue
                        value = core.filesystem.make_local(full, ctx=meta).replace("\\", "/").rstrip("/") + "/"
                        key = (KIND_FILE_CONTEXT, value.casefold())
                        if key not in seen:
                            seen.add(key)
                            entries.append(MentionEntry(KIND_FILE_CONTEXT, rel, value, True))
                            count += 1
                            if count >= self.MENTION_SCAN_LIMIT:
                                return entries

                    for name in files:
                        full = os.path.join(current_root, name)
                        if os.path.islink(full):
                            continue
                        rel = os.path.relpath(full, root_abs).replace(os.sep, "/")
                        if any(ch in rel for ch in "\r\n\t"):
                            continue
                        value = core.filesystem.make_local(full, ctx=meta).replace("\\", "/")
                        key = (KIND_FILE_CONTEXT, value.casefold())
                        if key not in seen:
                            seen.add(key)
                            entries.append(MentionEntry(KIND_FILE_CONTEXT, rel, value, False))
                            count += 1
                            if count >= self.MENTION_SCAN_LIMIT:
                                return entries
            except Exception as e:
                try:
                    core.debug.log(e)
                except Exception:
                    pass
        return entries

    def _refresh_mention_popup(self):
        if self._mention_loading or not self.hasFocus():
            self._mention_popup.hide()
            self._mention_trigger_pos = None
            self._mention_source_key = None
            return

        trigger = self._find_mention_trigger()
        if trigger is None:
            self._mention_popup.hide()
            self._mention_trigger_pos = None
            self._mention_source_key = None
            return

        at_pos, _end_pos, query = trigger
        source_key = self._get_mention_source_key()
        if (self._mention_trigger_pos != at_pos
                or self._mention_source_key != source_key):
            self._mention_trigger_pos = at_pos
            self._mention_source_key = source_key
            self._mention_entries = self._build_mention_entries()
            self._mention_popup.set_entries(self._mention_entries)

        if not self._mention_popup.apply_filter(query):
            return

        anchor = QTextCursor(self.document())
        anchor.setPosition(at_pos)
        rect = self.cursorRect(anchor)
        global_pos = self.viewport().mapToGlobal(rect.topLeft())
        self._mention_popup.show_above(global_pos)
        self.setFocus()

    def _accept_mention_entry(self, entry: MentionEntry):
        trigger = self._find_mention_trigger()
        if trigger is None:
            return
        at_pos, end_pos, _query = trigger

        next_char = ""
        after = QTextCursor(self.document())
        after.setPosition(end_pos)
        if after.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor):
            next_char = self._cursor_selected_text(after)

        self._mention_loading = True
        try:
            cursor = QTextCursor(self.document())
            cursor.setPosition(at_pos)
            cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
            cursor.beginEditBlock()
            try:
                cursor.removeSelectedText()
                self._insert_mention_cursor(cursor, entry)
                # Add a separator at end/before another word, but do not create
                # awkward whitespace before punctuation when inserting in-place.
                if (not next_char
                        or (not next_char.isspace()
                            and (next_char.isalnum() or next_char in "@_"))):
                    cursor.insertText(" ")
            finally:
                cursor.endEditBlock()
            self.setTextCursor(cursor)
            self._mention_popup.hide()
            self._mention_trigger_pos = None
            self._mention_source_key = None
        finally:
            self._mention_loading = False

        self._refresh_mention_formats()
        self.setFocus()
        self._schedule_auto_resize()

    def _on_text_changed_tokens(self):
        """Schedule token count update with debounce."""
        self._tokens_timer.start()
        # Keep auto-height in sync with content growth/shrink on every edit
        self._schedule_auto_resize()

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
                                self._directory_paste_handler.add_directory(local_path)
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

            # Add zoom submenu
            zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "font_size.input", self.value, self.on_zoom_changed)
            menu.addMenu(zoom_menu)

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
        mods = event.modifiers()

        # Mention picker owns navigation/accept keys while visible.
        if self._mention_popup.isVisible():
            if key == Qt.Key_Up:
                self._mention_popup.move_selection(-1)
                return
            if key == Qt.Key_Down:
                self._mention_popup.move_selection(1)
                return
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                if self._mention_popup.choose_current():
                    return
            if key == Qt.Key_Escape:
                self._mention_popup.hide()
                self._mention_trigger_pos = None
                return

        # --- History navigation and recall ---
        # Ctrl/Command + Up/Down navigates history regardless of current text.
        if key in (Qt.Key_Up, Qt.Key_Down) and (mods & (Qt.ControlModifier | Qt.MetaModifier)):
            if key == Qt.Key_Up:
                self._history_navigate(-1)
            else:
                self._history_navigate(+1)
            handled = True

        # Up with empty input and no modifiers recalls the last sent prompt.
        elif key == Qt.Key_Up and mods == Qt.NoModifier:
            if self._is_effectively_empty() and self._history:
                if not self._history_active:
                    self._history_begin()
                # Start from sentinel and move one step up to the latest entry
                self._history_index = len(self._history)
                self._history_navigate(-1)
                handled = True

        if handled:
            return

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

    def _hide_mention_after_focus_out(self):
        # A click in the non-focusable popup can briefly move focus away from
        # QTextEdit before QListWidget emits itemClicked. Defer closing by one
        # event-loop turn so mouse selection can finish first.
        if self.hasFocus():
            return
        if self._mention_popup.underMouse():
            QTimer.singleShot(80, self._hide_mention_after_focus_out)
            return
        self._mention_popup.hide()
        self._mention_trigger_pos = None
        self._mention_source_key = None

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        QTimer.singleShot(0, self._hide_mention_after_focus_out)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            dy = event.angleDelta().y()
            prev = self.value
            if dy > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            if self.value != prev:
                self.on_zoom_changed(self.value)
            event.accept()
            return
        super().wheelEvent(event)

    def on_zoom_changed(self, value: int):
        """
        Called when zoom level changes.

        :param value: new zoom level
        """
        self.value = value
        self.window.core.config.data['font_size.input'] = value
        self.window.core.config.save()
        self.window.controller.ui.update_font_size()
        # Reflow may change number of lines; adjust auto-height next tick
        QTimer.singleShot(0, self._schedule_auto_resize)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.FontChange:
            self._schedule_auto_resize()

    def action_add_attachment(self):
        """Add attachment (button click)."""
        self.window.controller.attachment.open_add()

    def action_toggle_mic(self):
        """Toggle microphone (button click)."""
        self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE))

    def action_toggle_web(self):
        """Toggle web search (button click)."""
        self.window.controller.chat.remote_tools.toggle('web_search')

    def add_reasoning_effort_button(self) -> QPushButton:
        """Add the runtime reasoning-effort selector to the right icon bar."""
        key = self.REASONING_EFFORT_KEY
        if key in self._icons_right:
            return self._icons_right[key]

        btn = QPushButton(self._icon_bar_right)
        btn.setObjectName("chatInputReasoningEffort")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFlat(True)
        btn.setIcon(QIcon())
        btn.setIconSize(QSize(0, 0))
        btn.setFixedHeight(self._btn_size_right.height())
        btn.setMinimumWidth(self._btn_size_right.width())
        btn.setToolTip(trans("reasoning_effort.tooltip"))
        btn.clicked.connect(self.action_reasoning_effort)
        btn.setHidden(True)

        self._icons_right[key] = btn
        self._icon_order_right.append(key)
        self._icon_meta_right[key] = {
            "icon": QIcon(),
            "alt_icon": None,
            "tooltip": trans("reasoning_effort.tooltip"),
            "alt_tooltip": None,
            "active": False,
        }
        self._rebuild_icon_layout_right()
        self._update_icon_bar_geometry_right()
        self._apply_margins()
        return btn

    def update_reasoning_effort(self):
        """Refresh visibility, value and width of the reasoning-effort selector."""
        btn = self._icons_right.get(self.REASONING_EFFORT_KEY)
        if btn is None:
            return

        try:
            model_key = self.window.core.config.get("model")
            model = self.window.core.models.get(model_key)
            efforts = self.window.core.models.get_reasoning_efforts(model)
        except (AttributeError, RuntimeError):
            efforts = []
            model = None

        if not efforts:
            btn.setHidden(True)
            self._update_icon_bar_geometry_right()
            self._apply_margins()
            return

        current = self.window.core.models.get_reasoning_effort(model)
        if current is None:
            btn.setHidden(True)
            self._update_icon_bar_geometry_right()
            self._apply_margins()
            return

        label = trans(f"reasoning_effort.{current}")
        btn.setText(f"{label}  ▴")
        btn.setToolTip(trans("reasoning_effort.tooltip"))
        btn.setFixedHeight(self._btn_size_right.height())

        # This button is text-based, unlike the fixed-size icon buttons next to it.
        # Calculate its width from the translated label every time the model/value
        # changes.  sizeHint() includes the active Qt/QSS button padding; the
        # explicit text fallback keeps enough room with styles whose hint omits
        # some stylesheet padding.
        btn.ensurePolished()
        text_width = btn.fontMetrics().horizontalAdvance(btn.text())
        hint_width = btn.sizeHint().width()
        btn.setFixedWidth(max(
            self._btn_size_right.width(),
            hint_width,
            text_width + 28,
        ))
        btn.setHidden(False)
        self._update_icon_bar_geometry_right()
        self._apply_margins()

    def action_reasoning_effort(self):
        """Open an upward popup with the effort values supported by this model."""
        btn = self._icons_right.get(self.REASONING_EFFORT_KEY)
        if btn is None or btn.isHidden():
            return

        model = self.window.core.models.get(self.window.core.config.get("model"))
        efforts = self.window.core.models.get_reasoning_efforts(model)
        current = self.window.core.models.get_reasoning_effort(model)
        if not efforts:
            return

        menu = QMenu(self)
        menu.setObjectName("chatInputReasoningEffortMenu")

        # Match the context-list section-header convention: disabled + bold.
        # Keeping the header as a menu action lets the native theme provide the
        # correct text color in both light and dark themes.
        header = QAction(trans("reasoning_effort.header"), menu)
        header.setEnabled(False)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        menu.addAction(header)
        menu.addSeparator()

        for effort in efforts:
            action = QAction(trans(f"reasoning_effort.{effort}"), menu)
            action.setCheckable(True)
            action.setChecked(effort == current)
            action.triggered.connect(
                lambda checked=False, value=effort: self.set_reasoning_effort(value)
            )
            menu.addAction(action)

        # Keep a reference for the lifetime of the non-modal popup. QMenu will
        # automatically choose another screen edge if the ideal point is invalid.
        self._reasoning_effort_menu = menu
        menu.aboutToHide.connect(self._clear_reasoning_effort_menu)
        menu.adjustSize()
        size = menu.sizeHint()
        global_pos = btn.mapToGlobal(QPoint(btn.width() - size.width(), -size.height()))
        menu.popup(global_pos)

    def _clear_reasoning_effort_menu(self):
        menu = self._reasoning_effort_menu
        self._reasoning_effort_menu = None
        if menu is not None:
            menu.deleteLater()

    def set_reasoning_effort(self, effort: str):
        """Persist the single global effort value selected by the user."""
        model = self.window.core.models.get(self.window.core.config.get("model"))
        if self.window.core.models.set_reasoning_effort(effort, model=model, persist=True):
            self.update_reasoning_effort()

    # -------------------- Left icon bar  --------------------
    # - Add icons: add_icon(...) or add_icons([...])
    # - Show/hide: set_icon_visible(key, bool)
    # - Swap icon at runtime: set_icon_state(key, active) with optional alt_icon

    def _init_icon_bar(self):
        """Create the left-side icon bar pinned in the top-left corner."""
        self._icon_bar = QWidget(self)
        self._icon_bar.setObjectName("chatInputIconBar")

        # Keep styled background enabled so the style engine (Qt Material) can still
        # paint hover/pressed states on child buttons.
        self._icon_bar.setAttribute(Qt.WA_StyledBackground, True)
        self._icon_bar.setAutoFillBackground(False)

        # Scope the rule to this object by its ID to avoid cascading 'background: transparent'
        # to child QPushButtons.
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

    # -------------------- Bottom controls row --------------------
    # Right-side controls live in a dedicated full-width row below the text
    # viewport. This avoids both a permanent right-side text wall and any need
    # for text-flow tricks around overlay buttons.

    def _init_icon_bar_right(self):
        """Create the dedicated bottom row for right-aligned input controls."""
        self._icon_bar_right = QWidget(self)
        self._icon_bar_right.setObjectName("chatInputIconBarRight")
        self._icon_bar_right.setAttribute(Qt.WA_StyledBackground, True)
        self._icon_bar_right.setAutoFillBackground(False)
        self._icon_bar_right.setStyleSheet("""
            #chatInputIconBarRight { background-color: transparent; }
        """)

        layout = QHBoxLayout(self._icon_bar_right)
        layout.setSpacing(self._icons_spacing_right)
        self._icon_bar_right.setLayout(layout)
        self._sync_right_row_layout()
        layout.addStretch(1)

        self._icon_bar_right.hide()
        self._update_icon_bar_geometry_right()
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

        :param key: unique identifier for the icon
        :param icon: default QIcon (e.g., mic off)
        :param tooltip: default tooltip text
        :param callback: callable executed on click
        :param visible: initial visibility (True=shown, False=hidden)
        :param alt_icon: optional alternate icon (e.g., mic on / recording)
        :param alt_tooltip: optional alternate tooltip text
        :return: the created QPushButton (or existing one if key already present)
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
        btn.setFlat(True)  # flat button style
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

        :param items: iterable of tuples/dicts defining icons
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

    # ---- Public API for icons (RIGHT-BOTTOM) ----

    def add_right_icon(
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
        Add a new icon button to the right-bottom bar.

        :param key: unique identifier for the icon
        :param icon: default QIcon
        :param tooltip: default tooltip text
        :param callback: callable executed on click
        :param visible: initial visibility (True=shown, False=hidden)
        :param alt_icon: optional alternate icon
        :param alt_tooltip: optional alternate tooltip text
        :return: the created QPushButton (or existing one if key already present)
        """
        if key in self._icons_right:
            btn = self._icons_right[key]
            meta = self._icon_meta_right.get(key, {})
            meta.update({
                "icon": icon or meta.get("icon"),
                "alt_icon": alt_icon if alt_icon is not None else meta.get("alt_icon"),
                "tooltip": tooltip or meta.get("tooltip", key),
                "alt_tooltip": alt_tooltip if alt_tooltip is not None else meta.get("alt_tooltip"),
            })
            self._icon_meta_right[key] = meta
            btn.setIcon(meta["icon"])
            btn.setToolTip(meta["tooltip"])
            if callback is not None:
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(callback)
            btn.setHidden(not visible)
            self._rebuild_icon_layout_right()
            self._update_icon_bar_geometry_right()
            self._apply_margins()
            return btn

        btn = QPushButton(self._icon_bar_right)
        btn.setObjectName(f"chatInputIconBtnRight_{key}")
        btn.setIcon(icon)
        btn.setIconSize(self._icon_size_right)
        btn.setFixedSize(self._btn_size_right)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tooltip or key)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFlat(True)
        btn.setText("")

        if callback is not None:
            btn.clicked.connect(callback)

        self._icons_right[key] = btn
        self._icon_order_right.append(key)
        self._icon_meta_right[key] = {
            "icon": icon,
            "alt_icon": alt_icon,
            "tooltip": tooltip or key,
            "alt_tooltip": alt_tooltip,
            "active": False,
        }

        self._apply_icon_visual(key)
        btn.setHidden(not visible)

        self._rebuild_icon_layout_right()
        self._update_icon_bar_geometry_right()
        self._apply_margins()
        return btn

    def add_right_button(
        self,
        key: str,
        text: str,
        callback=None,
        tooltip: str = "",
        visible: bool = True,
    ) -> QPushButton:
        """Add a text button to the dedicated bottom row (after existing controls)."""
        if key in self._icons_right:
            btn = self._icons_right[key]
            self._right_text_buttons.add(key)
            btn.setText(text)
            if tooltip:
                btn.setToolTip(tooltip)
            if callback is not None:
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(callback)
            btn.setHidden(not visible)
            self._fit_right_text_button(btn)
            self._rebuild_icon_layout_right()
            self._update_icon_bar_geometry_right()
            self._apply_margins()
            return btn

        btn = QPushButton(self._icon_bar_right)
        btn.setObjectName(f"chatInputButtonRight_{key}")
        btn.setText(text)
        btn.setIcon(QIcon())
        btn.setIconSize(QSize(0, 0))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolTip(tooltip)
        btn.setFixedHeight(self._btn_size_right.height())

        if callback is not None:
            btn.clicked.connect(callback)

        self._icons_right[key] = btn
        self._icon_order_right.append(key)
        self._right_text_buttons.add(key)
        self._icon_meta_right[key] = {
            "icon": QIcon(),
            "alt_icon": None,
            "tooltip": tooltip or key,
            "alt_tooltip": None,
            "active": False,
        }

        self._fit_right_text_button(btn)
        btn.setHidden(not visible)
        self._rebuild_icon_layout_right()
        self._update_icon_bar_geometry_right()
        self._apply_margins()
        return btn

    def _fit_right_text_button(self, btn: QPushButton):
        """Fit an embedded text button to its translated label and active theme."""
        btn.ensurePolished()
        btn.setIconSize(QSize(0, 0))
        btn.setFixedHeight(self._btn_size_right.height())
        text_width = btn.fontMetrics().horizontalAdvance(btn.text())
        btn.setFixedWidth(max(
            self._btn_size_right.width(),
            btn.sizeHint().width(),
            text_width + 24,
        ))

    def refresh_right_bar(self):
        """Refresh embedded text-button sizes and the dedicated bottom row."""
        for key in tuple(self._right_text_buttons):
            btn = self._icons_right.get(key)
            if btn is not None:
                self._fit_right_text_button(btn)
        self._update_icon_bar_geometry_right()
        self._reposition_icon_bar_right()
        self._apply_margins()

    def add_right_icons(self, items):
        """Add multiple icons to the dedicated bottom controls row."""
        for it in items:
            if isinstance(it, dict):
                self.add_right_icon(
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
                self.add_right_icon(key, icon, tooltip, callback, visible, alt_icon, alt_tooltip)

    # ---- Cross-bar helpers (operate on both bars where applicable) ----

    def remove_icon(self, key: str):
        """
        Remove an icon from the bar.

        :param key: icon key
        """
        # Left bar
        btn = self._icons.pop(key, None)
        if btn is not None:
            self._icon_meta.pop(key, None)
            try:
                self._icon_order.remove(key)
            except ValueError:
                pass
            btn.setParent(None)
            btn.deleteLater()
            self._rebuild_icon_layout()
            self._update_icon_bar_geometry()
            self._apply_margins()
            return

        # Right-bottom bar
        btn = self._icons_right.pop(key, None)
        if btn is not None:
            self._right_text_buttons.discard(key)
            self._icon_meta_right.pop(key, None)
            try:
                self._icon_order_right.remove(key)
            except ValueError:
                pass
            btn.setParent(None)
            btn.deleteLater()
            self._rebuild_icon_layout_right()
            self._update_icon_bar_geometry_right()
            self._apply_margins()

    def set_icon_visible(self, key: str, visible: bool):
        """
        Show or hide an icon by key; layout margins are recalculated.

        :param key: icon key
        :param visible: True to show, False to hide
        """
        btn = self._icons.get(key)
        if btn:
            btn.setHidden(not visible)
            self._update_icon_bar_geometry()
            self._apply_margins()
            return
        btn = self._icons_right.get(key)
        if btn:
            btn.setHidden(not visible)
            self._update_icon_bar_geometry_right()
            self._apply_margins()

    def toggle_icon(self, key: str):
        """
        Toggle icon visibility and recalc margins.

        :param key: icon key
        """
        btn = self._icons.get(key)
        if btn:
            btn.setHidden(not btn.isHidden())
            self._update_icon_bar_geometry()
            self._apply_margins()
            return
        btn = self._icons_right.get(key)
        if btn:
            btn.setHidden(not btn.isHidden())
            self._update_icon_bar_geometry_right()
            self._apply_margins()

    def is_icon_visible(self, key: str) -> bool:
        """
        Return True if icon is visible (not hidden).

        :param key: icon key
        """
        btn = self._icons.get(key) or self._icons_right.get(key)
        return bool(btn and not btn.isHidden())

    def set_icon_order(self, keys):
        """
        Set rendering order for icons by a list of keys.
        Icons not listed keep their relative order at the end.

        :param keys: list of icon keys in desired order
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

    def set_right_icon_order(self, keys):
        """
        Set rendering order for icons in the bottom controls row.
        Icons not listed keep their relative order at the end.

        :param keys: list of icon keys in desired order
        """
        new_order = []
        seen = set()
        for k in keys:
            if k in self._icons_right and k not in seen:
                new_order.append(k)
                seen.add(k)
        for k in self._icon_order_right:
            if k not in seen and k in self._icons_right:
                new_order.append(k)
        self._icon_order_right = new_order
        self._rebuild_icon_layout_right()
        self._update_icon_bar_geometry_right()
        self._apply_margins()

    # ---- Runtime icon swap / state API ----

    def set_icon_state(self, key: str, active: bool):
        """
        Switch between base icon and alt icon at runtime.
        - active=False -> show base icon/tooltip
        - active=True  -> show alt icon/tooltip (if provided; falls back to base icon if not)

        :param key: icon key
        :param active: True to show alt icon, False for base icon
        """
        if key in self._icons:
            meta = self._icon_meta.get(key, {})
            meta["active"] = bool(active)
            self._icon_meta[key] = meta
            self._apply_icon_visual(key)
            return
        if key in self._icons_right:
            meta = self._icon_meta_right.get(key, {})
            meta["active"] = bool(active)
            self._icon_meta_right[key] = meta
            self._apply_icon_visual(key)

    def toggle_icon_state(self, key: str) -> bool:
        """
        Toggle active state and return new state.

        :param key: icon key
        :return: new active state (True if alt icon is now shown)
        """
        if key in self._icons:
            current = bool(self._icon_meta.get(key, {}).get("active", False))
            self.set_icon_state(key, not current)
            return not current
        if key in self._icons_right:
            current = bool(self._icon_meta_right.get(key, {}).get("active", False))
            self.set_icon_state(key, not current)
            return not current
        return False

    def set_icon_pixmap(self, key: str, icon: QIcon):
        """
        Replace base icon at runtime (does not touch alt icon).

        :param key: icon key
        :param icon: new QIcon
        """
        if key in self._icons:
            meta = self._icon_meta.get(key, {})
            meta["icon"] = icon
            self._icon_meta[key] = meta
            self._apply_icon_visual(key)
            return
        if key in self._icons_right:
            meta = self._icon_meta_right.get(key, {})
            meta["icon"] = icon
            self._icon_meta_right[key] = meta
            self._apply_icon_visual(key)

    def set_icon_alt(self, key: str, alt_icon: Optional[QIcon], alt_tooltip: Optional[str] = None):
        """
        Set/replace alternate icon and optional tooltip

        :param key: icon key
        :param alt_icon: new alternate QIcon (or None to clear)
        :param alt_tooltip: new alternate tooltip (or None to keep existing)
        """
        if key in self._icons:
            meta = self._icon_meta.get(key, {})
            meta["alt_icon"] = alt_icon
            if alt_tooltip is not None:
                meta["alt_tooltip"] = alt_tooltip
            self._icon_meta[key] = meta
            self._apply_icon_visual(key)
            return
        if key in self._icons_right:
            meta = self._icon_meta_right.get(key, {})
            meta["alt_icon"] = alt_icon
            if alt_tooltip is not None:
                meta["alt_tooltip"] = alt_tooltip
            self._icon_meta_right[key] = meta
            self._apply_icon_visual(key)

    def set_icon_tooltip(self, key: str, tooltip: str, for_alt: bool = False):
        """
        Update tooltip; for_alt=True updates alternate tooltip

        :param key: icon key
        :param tooltip: new tooltip text
        :param for_alt: if True, update alt tooltip instead of base tooltip
        """
        if key in self._icons:
            meta = self._icon_meta.get(key, {})
            if for_alt:
                meta["alt_tooltip"] = tooltip
            else:
                meta["tooltip"] = tooltip
            self._icon_meta[key] = meta
            self._apply_icon_visual(key)
            return
        if key in self._icons_right:
            meta = self._icon_meta_right.get(key, {})
            if for_alt:
                meta["alt_tooltip"] = tooltip
            else:
                meta["tooltip"] = tooltip
            self._icon_meta_right[key] = meta
            self._apply_icon_visual(key)

    def set_icon_callback(self, key: str, callback):
        """
        Update click callback at runtime.

        :param key: icon key
        :param callback: new callable (or None to disconnect)
        """
        btn = self._icons.get(key)
        if btn:
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            if callback is not None:
                btn.clicked.connect(callback)
            return
        btn = self._icons_right.get(key)
        if btn:
            try:
                btn.clicked.disconnect()
            except Exception:
                pass
            if callback is not None:
                btn.clicked.connect(callback)

    def get_icon_state(self, key: str) -> bool:
        """
        Return active state for icon (True if alt icon is displayed).

        :param key: icon key
        """
        if key in self._icon_meta:
            return bool(self._icon_meta.get(key, {}).get("active", False))
        if key in self._icon_meta_right:
            return bool(self._icon_meta_right.get(key, {}).get("active", False))
        return False

    def get_icon_button(self, key: str) -> Optional[QPushButton]:
        """
        Return the underlying QPushButton for advanced customization.

        :param key: icon key
        :return: QPushButton or None if key not found
        """
        return self._icons.get(key) or self._icons_right.get(key)

    # ---- Right icons sizing API ----

    def set_right_icon_sizes(
        self,
        icon_size: Optional[Union[QSize, Tuple[int, int], int]] = None,
        btn_size: Optional[Union[QSize, Tuple[int, int], int]] = None,
    ):
        """
        Public API: change sizes for icons in the bottom controls row.
        - icon_size: QSize | (w, h) | int (square)
        - btn_size : QSize | (w, h) | int (square)
        Applies to existing right icons immediately.
        """
        def _to_qsize(v, fallback: QSize) -> QSize:
            if v is None:
                return fallback
            if isinstance(v, QSize):
                return v
            if isinstance(v, int):
                return QSize(v, v)
            if isinstance(v, (tuple, list)) and len(v) >= 2:
                return QSize(int(v[0]), int(v[1]))
            return fallback

        new_icon_sz = _to_qsize(icon_size, self._icon_size_right)
        new_btn_sz = _to_qsize(btn_size, self._btn_size_right)

        self._icon_size_right = new_icon_sz
        self._btn_size_right = new_btn_sz

        for key, btn in self._icons_right.items():
            if key == self.REASONING_EFFORT_KEY:
                btn.setIconSize(QSize(0, 0))
                btn.setFixedHeight(self._btn_size_right.height())
            elif key in self._right_text_buttons:
                self._fit_right_text_button(btn)
            else:
                btn.setIconSize(self._icon_size_right)
                btn.setFixedSize(self._btn_size_right)

        if hasattr(self, "_icon_bar_right"):
            self._icon_bar_right.setFixedHeight(self._btn_size_right.height())

        self.update_reasoning_effort()
        self._update_icon_bar_geometry_right()
        self._reposition_icon_bar_right()
        self._apply_margins()
        self.update()

    def set_right_icon_px(self, icon_px: int, btn_px: Optional[int] = None):
        """
        Convenience helper to set square sizes for bottom-row icons.
        """
        btn = btn_px if btn_px is not None else self._btn_size_right.height()
        self.set_right_icon_sizes(icon_px, btn)

    # ---- Right bar margins/spacing/offset API ----

    def set_right_bar_margins(
        self,
        margin: Optional[int] = None,
        spacing: Optional[int] = None,
        offset_x: Optional[int] = None,
        offset_y: Optional[int] = None,
    ):
        """
        Public API: change layout params for the bottom controls row.
        - margin: inner padding from edges (px)
        - spacing: spacing between right-bar buttons (px)
        - offset_x: horizontal offset (+ rightwards, - leftwards)
        - offset_y: vertical offset (+ downwards, - upwards)
        """
        if margin is not None:
            try:
                self._icons_margin_right = int(margin)
            except Exception:
                pass
        if spacing is not None:
            try:
                self._icons_spacing_right = int(spacing)
                if hasattr(self, "_icon_bar_right") and self._icon_bar_right.layout():
                    self._icon_bar_right.layout().setSpacing(self._icons_spacing_right)
            except Exception:
                pass
        if offset_x is not None:
            try:
                self._icons_offset_x_right = int(offset_x)
            except Exception:
                pass
        if offset_y is not None:
            try:
                self._icons_offset_y_right = int(offset_y)
            except Exception:
                pass

        self._update_icon_bar_geometry_right()
        self._reposition_icon_bar_right()
        self._apply_margins()
        self.update()

    # ---- Internal layout helpers ----

    def _apply_icon_visual(self, key: str):
        """
        Apply correct icon and tooltip based on meta state.

        :param key: icon key
        """
        btn = self._icons.get(key) or self._icons_right.get(key)
        meta = self._icon_meta.get(key) if key in self._icon_meta else self._icon_meta_right.get(key, {})
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

    def _rebuild_icon_layout_right(self):
        """Rebuild the bottom controls row according to _icon_order_right."""
        if not hasattr(self, "_icon_bar_right"):
            return
        layout = self._icon_bar_right.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                layout.removeWidget(w)
        # The stretch makes the entire control group hug the right edge while
        # the row itself spans the full input width.
        layout.addStretch(1)
        for k in self._icon_order_right:
            btn = self._icons_right.get(k)
            if btn:
                layout.addWidget(btn)

    def _visible_buttons(self):
        """Helper to list icon buttons that are not hidden."""
        return [self._icons[k] for k in self._icon_order if k in self._icons and not self._icons[k].isHidden()]

    def _visible_buttons_right(self):
        """Helper to list icon buttons that are not hidden on right bar."""
        return [self._icons_right[k] for k in self._icon_order_right if k in self._icons_right and not self._icons_right[k].isHidden()]

    def _compute_icon_bar_width(self) -> int:
        """
        Compute width from button count to ensure padding before layout measures.

        :return: total width in pixels
        """
        vis = self._visible_buttons()
        if not vis:
            return 0
        count = len(vis)
        w = count * self._btn_size.width() + (count - 1) * self._icons_spacing
        return w

    def _compute_icon_bar_right_width(self) -> int:
        """Compute width of the visible control group inside the bottom row."""
        vis = self._visible_buttons_right()
        if not vis:
            return 0
        count = len(vis)
        w = sum(max(0, btn.width()) for btn in vis)
        w += (count - 1) * self._icons_spacing_right
        return w

    def _right_row_vertical_padding(self) -> tuple[int, int]:
        """Return top/bottom padding for the dedicated controls row."""
        total = max(0, int(self._icons_margin_right))
        top = total // 2
        bottom = total - top

        # Preserve the old vertical-offset API: positive values move controls
        # downward within the row, negative values move them upward.
        offset = int(self._icons_offset_y_right)
        top = max(0, top + offset)
        bottom = max(0, bottom - offset)
        return top, bottom

    def _right_row_height(self) -> int:
        """Return the height reserved below the text viewport for controls."""
        vis = self._visible_buttons_right()
        if not vis:
            return 0
        top, bottom = self._right_row_vertical_padding()
        btn_h = max([btn.height() for btn in vis] or [self._btn_size_right.height()])
        return max(0, btn_h + top + bottom)

    def _sync_right_row_layout(self):
        """Apply spacing and padding to the dedicated bottom controls row."""
        if not hasattr(self, "_icon_bar_right"):
            return
        layout = self._icon_bar_right.layout()
        if layout is None:
            return
        top, bottom = self._right_row_vertical_padding()
        # Positive x offset moves the control group rightwards by reducing the
        # normal right inset; negative values move it leftwards.
        right = max(0, int(self._icons_margin_right) - int(self._icons_offset_x_right))
        layout.setContentsMargins(0, top, right, bottom)
        layout.setSpacing(self._icons_spacing_right)

    def _update_icon_bar_geometry(self):
        """Update the bar width and keep it raised above the text viewport."""
        if not hasattr(self, "_icon_bar"):
            return
        width = self._compute_icon_bar_width()
        self._icon_bar.setFixedWidth(max(0, width))
        self._icon_bar.raise_()
        self._reposition_icon_bar()

    def _update_icon_bar_geometry_right(self):
        """Update the dedicated bottom-row geometry and visibility."""
        if not hasattr(self, "_icon_bar_right"):
            return
        self._sync_right_row_layout()
        row_h = self._right_row_height()
        self._icon_bar_right.setVisible(row_h > 0)
        self._icon_bar_right.raise_()
        self._reposition_icon_bar_right()

    def _reposition_icon_bar(self):
        """Keep the icon bar pinned to the top-left corner."""
        if hasattr(self, "_icon_bar"):
            fw = self.frameWidth()
            x = fw + self._icons_margin
            y = fw + self._icons_margin + self._icons_offset_y
            if y < 0:
                y = 0
            self._icon_bar.move(x, y)

    def _reposition_icon_bar_right(self):
        """Keep the dedicated controls row pinned below the text viewport."""
        if hasattr(self, "_icon_bar_right"):
            fw = self.frameWidth()
            row_h = self._right_row_height()
            width = max(0, self.width() - 2 * fw)
            x = fw
            y = max(fw, self.height() - fw - row_h)
            self._icon_bar_right.setGeometry(x, y, width, row_h)

    def _apply_margins(self):
        """Reserve top/left text space and a dedicated bottom controls row."""
        left_space = self._compute_icon_bar_width()
        if left_space > 0:
            left_space += self._icons_margin * 2

        # Right-side controls no longer consume a right viewport margin. They
        # live in their own full-width row below the text, so all text lines can
        # use the complete remaining width.
        bottom_space = self._right_row_height()
        self.setViewportMargins(left_space, self._text_top_padding, 0, bottom_space)

        # Reflow may change number of lines; adjust auto-height on next tick.
        try:
            QTimer.singleShot(0, self._schedule_auto_resize)
        except Exception:
            pass

    def resizeEvent(self, event):
        """Resize event keeps the icon bar in place."""
        super().resizeEvent(event)
        try:
            self._reposition_icon_bar()
        except Exception:
            pass
        try:
            self._reposition_icon_bar_right()
        except Exception:
            pass
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

    # ================== Prompt history helpers ==================

    def _is_effectively_empty(self) -> bool:
        """Returns True if input contains only whitespace or is empty."""
        try:
            return len(self.toPlainText().strip()) == 0
        except Exception:
            return True

    def _set_text_and_move_end(self, text: str):
        """Set durable history text and restore UI mention anchors."""
        self.set_mention_text(text or "")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

    def _history_begin(self):
        """Enter history navigation mode and snapshot current typed text."""
        if self._history_active:
            return
        try:
            self._history_saved_current = self.serialize_mentions()
        except Exception:
            self._history_saved_current = self.toPlainText()
        self._history_active = True
        self._history_index = len(self._history)

    def _history_end(self, restore_saved: bool = True):
        """Exit history navigation mode; optionally restore the saved typed text."""
        if restore_saved:
            self._set_text_and_move_end(self._history_saved_current)
        self._history_active = False
        self._history_index = -1
        self._history_saved_current = ""

    def _history_navigate(self, direction: int):
        """
        Navigate through history.
        direction: -1 for older (Up), +1 for newer (Down).
        """
        if not self._history:
            return
        if not self._history_active:
            self._history_begin()

        # Move within [0, len(history)-1]; moving past newest restores and exits navigation.
        if direction < 0:
            # Older
            if self._history_index > 0:
                self._history_index -= 1
                self._set_text_and_move_end(self._history[self._history_index])
            elif self._history_index == 0:
                # Stay at the oldest entry
                self._set_text_and_move_end(self._history[0])
            else:
                # Sentinel -> jump to last
                self._history_index = max(0, len(self._history) - 1)
                self._set_text_and_move_end(self._history[self._history_index])
        else:
            # Newer
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self._set_text_and_move_end(self._history[self._history_index])
            elif self._history_index == len(self._history) - 1:
                # Past newest -> restore typed and exit
                self._history_end(restore_saved=True)
            else:
                # Already at sentinel -> ensure restore
                self._history_end(restore_saved=True)

    def _normalize_history_text(self, text: str) -> str:
        """Normalize text before storing in history."""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""
        return text.strip()

    def history_push(self, text: str):
        """
        Public API: push a sent prompt to history.
        Controllers may call this when sending via buttons to keep history in sync.
        """
        s = self._normalize_history_text(text)
        if not s:
            return
        if self._history and self._history[-1] == s:
            return
        self._history.append(s)
        if len(self._history) > self._history_limit:
            # Keep most recent N entries
            overflow = len(self._history) - self._history_limit
            if overflow > 0:
                del self._history[:overflow]

    def history_clear(self):
        """Public API: clear stored prompt history."""
        self._history.clear()
        self._history_index = -1
        self._history_active = False
        self._history_saved_current = ""

    def _on_prompt_sent(self, text_before_send: str):
        """
        Internal hook executed after sending the input via Enter.
        Stores the prompt into history and resets navigation snapshot.
        """
        try:
            # Avoid recording while editing existing messages (best-effort).
            is_editing = bool(self.window.controller.ctx.extra.is_editing())
        except Exception:
            is_editing = False

        if not is_editing:
            self.history_push(text_before_send)

        # Leave history navigation after send
        self._history_active = False
        self._history_index = -1
        self._history_saved_current = ""

    def on_prompt_sent(self, text: Optional[str] = None):
        """
        Public API: controllers can call this when a prompt is sent by other means (e.g., send button).
        If text is None the current input text is used.
        """
        if text is None:
            text = self.toPlainText()
        self._on_prompt_sent(text)