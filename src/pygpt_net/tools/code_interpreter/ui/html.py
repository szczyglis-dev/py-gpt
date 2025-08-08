#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.08 21:00:00                  #
# ================================================== #

import json
import re
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, Slot, QEvent, QTimer
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QMenu

from pygpt_net.item.ctx import CtxMeta, CtxItem
from pygpt_net.core.text.web_finder import WebFinder
from pygpt_net.tools.code_interpreter.body import Body
from pygpt_net.utils import trans

import pygpt_net.icons_rc

class CodeBlock:
    def __init__(
            self,
            content: str = "",
            type: str = "stdout",
            images: Optional[list] = None,
            files: Optional[list] = None):
        """
        Code block

        :param content: Code content
        :param type: Type of code block (e.g., stdout, stderr)
        :param images: List of images
        :param files: List of files
        """
        self.content = content
        self.type = type
        self.images = []  # list of images
        self.files = []  # list of files

        if images is not None:
            self.images = images
        if files is not None:
            self.files = files

    def as_dict(self):
        """
        Convert to dictionary

        :return: Dictionary representation
        """
        return {
            "content": self.content,
            "type": self.type,
            "images": self.images,
            "files": self.files,
        }

    def from_dict(self, data: dict):
        """
        Load from dictionary

        :param data: Dictionary data
        """
        self.content = data.get("content", "")
        self.type = data.get("type", "stdout")
        self.images = data.get("images", [])
        self.files = data.get("files", [])

    def __str__(self):
        """
        String representation

        :return: String representation
        """
        return f"CodeBlock(type={self.type}, content={self.content})"


class HtmlOutput(QWebEngineView):
    def __init__(self, window=None, tool=None):
        """
        HTML output (Webkit)

        :param window: main window
        """
        super(HtmlOutput, self).__init__(window)
        self.window = window
        self.finder = WebFinder(window, self)
        self.body = Body(self.window)
        self.loadFinished.connect(self.on_page_loaded)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.signals = WebEngineSignals()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.plain = ""
        self.html_content = ""
        self.meta = None
        self.tab = None
        self.tool = tool  # tool instance
        self.installEventFilter(self)
        self.initialized = False  # flag to check if initialized
        self.loaded = False  # flag to check if loaded
        self.is_dialog = False
        self.nodes = []  # code blocks

    def on_delete(self):
        """Clean up on delete"""
        if self.finder:
            self.finder.disconnect()  # disconnect finder
            self.finder = None  # delete finder

        self.tab = None  # clear tab reference

        # delete page
        page = self.page()
        if page:
            if hasattr(page, 'bridge'):
                page.bridge.deleteLater()
            if hasattr(page, 'channel'):
                page.channel.deleteLater()
            if hasattr(page, 'signals') and page.signals:
                page.signals.deleteLater()
            page.deleteLater()  # delete page

        # disconnect signals
        self.loadFinished.disconnect(self.on_page_loaded)
        self.customContextMenuRequested.disconnect(self.on_context_menu)
        self.signals.save_as.disconnect(self.window.controller.chat.render.handle_save_as)
        self.signals.audio_read.disconnect(self.window.controller.chat.render.handle_audio_read)

        self.deleteLater()  # delete widget

    def init(self, force: bool = False):
        """
        Initialize HTML output

        :param force: Force initialization
        """
        if self.initialized and not force:
            return
        body = self.body.get_html(0)
        self.setHtml(body, baseUrl="file://")
        self.initialized = True
        QTimer.singleShot(100, self.scroll_to_bottom)  # wait for rendering to complete

    def reload_css(self):
        """Reload CSS - all, global"""
        to_json = json.dumps(self.body.prepare_styles())
        if not self.page():
            return
        self.page().runJavaScript(
            "if (typeof window.updateCSS !== 'undefined') updateCSS({});".format(to_json))
        if self.window.core.config.get('render.blocks'):
            self.page().runJavaScript("if (typeof window.enableBlocks !== 'undefined') enableBlocks();")
        else:
            self.page().runJavaScript(
                "if (typeof window.disableBlocks !== 'undefined') disableBlocks();")

    def reload(self):
        """Reload HTML output"""
        #return
        self.reload_css()

    def get_nodes(self) -> list:
        """
        Get output nodes

        :return: Nodes
        """
        return self.nodes

    def from_plaintext(self):
        """
        Convert plain text to HTML content
        """
        self.set_output(self.get_plaintext(), store_plain=False)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def set_meta(self, meta: CtxMeta):
        """
        Assign ctx meta

        :param meta: context meta
        """
        self.meta = meta

    def append_plaintext(self, text: str):
        """
        Set plain text

        :param text: text
        """
        self.plain+= str(text)

    def set_plaintext(self, text: str):
        """
        Set plain text

        :param text: text
        """
        self.plain = text

    def get_plaintext(self) -> str:
        """
        Get plain text

        :return: plain text
        """
        return self.plain

    def clear_plaintext(self):
        """
        Clear plain text
        """
        self.plain = ""

    def set_html_content(self, html: str):
        """
        Set HTML content

        :param html: HTML content
        """
        self.html_content = html

    def get_html_content(self) -> str:
        """
        Get HTML content

        :return: HTML content
        """
        return self.html_content

    def restore_nodes(self, nodes: list):
        """
        Restore output nodes

        :param nodes: Nodes
        """
        self.init()
        self.nodes = []
        if not self.page():
            return
        self.page().runJavaScript(
            f"clearOutput();")
        self.insert_nodes(nodes)

    def insert_nodes(self, nodes: list):
        """
        Insert multiple output nodes

        :param nodes: List of CodeBlock instances
        """
        for node in nodes:
            if node.content != "":
                self.nodes.append(node)
                if self.loaded:
                        self.insert_output(node)
        self.update_current_content()
        QTimer.singleShot(100, self.scroll_to_bottom)  # wait for rendering to complete

    def scroll_to_bottom(self):
        """Scroll to bottom of the output"""
        if not self.page():
            return
        self.page().runJavaScript(
            f"scrollToBottom();")

    def insert_output(self, node: CodeBlock):
        """
        Insert output node

        :param node: CodeBlock instance
        """
        if not self.page():
            return
        escaped_chunk = json.dumps(node.content)
        self.page().runJavaScript(
            f"insertOutput({escaped_chunk}, '{node.type}');")
        # append images
        if node.images:
            for img in node.images:
                url, path = self.window.core.filesystem.extract_local_url(img)
                self.page().runJavaScript(
                    f"appendImage('{path}', '{url}');")
        self.update_current_content()

    def begin_output(self, type: str = "stdout"):
        """
        Begin output content

        :param type: Output type (stdout, stderr, etc.)
        """
        self.init()
        self.nodes.append(CodeBlock("", type))
        if not self.page():
            return
        self.page().runJavaScript(
            f"beginOutput('{type}');")

        self.update_current_content()

    def end_output(self, type: str = "stdout", ctx: CtxItem = None):
        """
        End output content

        :param type: Output type (stdout, stderr, etc.)
        :param ctx: Context item (optional)
        """
        self.init()
        # update images and files
        # if images then append to last node
        if ctx.images:
            if self.nodes and isinstance(self.nodes[-1], CodeBlock):
                self.nodes[-1].images.extend(ctx.images)
        if ctx.files:
            if self.nodes and isinstance(self.nodes[-1], CodeBlock):
                self.nodes[-1].files.extend(ctx.files)

        if not self.page():
            return
        self.page().runJavaScript(
            f"endOutput('{type}');")

        # render images
        if ctx.images:
            for img in ctx.images:
                url, path = self.window.core.filesystem.extract_local_url(img)
                self.page().runJavaScript(
                    f"appendImage('{path}', '{url}');")

        self.update_current_content()

    def set_output(self, content: str, store_plain: bool = True):
        """
        Set output content

        :param content: Content
        :param store_plain: Store plain text
        """
        if store_plain:
            self.set_plaintext(content)
            self.nodes = []
            self.nodes.append(CodeBlock(content))
        try:
            if not self.loaded:
                return  # wait for page to load
            self.init()
            escaped_chunk = json.dumps(content)
            if not self.page():
                return
            self.page().runJavaScript(
                f"replaceOutput({escaped_chunk});")
        except Exception as e:
            print(e)
        self.update_current_content()

    def set_history(self, content: str):
        """
        Set history content

        :param content: Content
        """
        self.set_plaintext(content)
        self.nodes = []
        self.nodes.append(CodeBlock(content))
        try:
            if not self.loaded:
                return  # wait for page to load
            self.init()
            escaped_chunk = json.dumps(content)
            if not self.page():
                return
            self.page().runJavaScript(
                f"replaceOutput({escaped_chunk});")
        except Exception as e:
            print(e)
        self.update_current_content()

    def append_output(self, content: str, type: str = "stdout"):
        """
        Append output content

        :param content: Content
        :param type: Output type (stdout, stderr, etc.)
        """
        self.append_plaintext(content)

        # buffer output
        if self.nodes and isinstance(self.nodes[-1], CodeBlock):
            self.nodes[-1].content += content
        else:
            self.nodes.append(CodeBlock(content, type))
        try:
            if not self.loaded:
                return  # wait for page to load
            self.init()
            escaped_chunk = json.dumps(content)
            if not self.page():
                return
            self.page().runJavaScript(
                f"appendToOutput({escaped_chunk});")
        except Exception as e:
            print(e)
        self.update_current_content()

    def clear(self):
        """Clear output content"""
        self.set_plaintext("")
        self.nodes = []
        try:
            if not self.loaded:
                return  # wait for page to load
            self.init()
            if not self.page():
                return
            self.page().runJavaScript(
                f"clearOutput();")
        except Exception as e:
            print(e)
        self.update_current_content()

    def on_context_menu(self, position):
        """
        Context menu event

        :param position: position
        """
        menu = QMenu(self)
        selected_text = ""
        is_selection = self.page().hasSelection()
        if is_selection:
            selected_text = self.get_selected_text()

        if is_selection:
            # copy
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
            action.triggered.connect(self.copy_selected_text)
            menu.addAction(action)

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(
                lambda: self.signals.audio_read.emit(selected_text)
            )
            menu.addAction(action)

            # copy to
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(self, selected_text)
            menu.addMenu(copy_to_menu)

            # save as (selected)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.signals.save_as.emit(selected_text, 'txt')
            )
            menu.addAction(action)
        else:
            # select all
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.select_all'), self)
            action.triggered.connect(self.select_all_text)
            menu.addAction(action)

            # save as (all) - plain
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as') + " (text)", self)
            action.triggered.connect(
                lambda: self.signals.save_as.emit(re.sub(r'\n{2,}', '\n\n', self.plain), 'txt')
            )
            menu.addAction(action)

            # save as (all) - html
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as') + " (html)", self)
            action.triggered.connect(
                lambda: self.signals.save_as.emit(re.sub(r'\n{2,}', '\n\n', self.html_content), 'html')
            )
            menu.addAction(action)

        # restart and close
        menu.addSeparator()
        action = QAction(QIcon(":/icons/close.svg"), trans('interpreter.menu.file.clear_output'), self)
        action.triggered.connect(
            lambda: self.tool.clear_output()
        )
        menu.addAction(action)
        action = QAction(QIcon(":/icons/close.svg"), trans('interpreter.menu.file.clear_history'), self)
        action.triggered.connect(
            lambda: self.tool.clear_history()
        )
        menu.addAction(action)
        action = QAction(QIcon(":/icons/reload.svg"), trans('interpreter.menu.kernel.restart'), self)
        action.triggered.connect(
            lambda: self.tool.restart_kernel()
        )
        menu.addAction(action)

        menu.addSeparator()
        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        #action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def update_zoom(self):
        """Update zoom from config"""
        if self.window.core.config.has("zoom"):
            if not self.page():
                return
            self.page().setZoomFactor(self.window.core.config.get("zoom"))

    def get_zoom_value(self) -> float:
        """
        Get zoom value

        :return: zoom value
        """
        return self.page().zoomFactor()

    def reset_current_content(self):
        """Reset current content"""
        self.plain = ""
        self.html_content = ""

    def update_current_content(self):
        """Update current content"""
        if self.loaded:
            self.page().runJavaScript("document.documentElement.innerHTML", 0, self.set_html_content)

    def clear_content(self):
        """Clear content"""
        self.clear_plaintext()

    def on_page_loaded(self, success):
        """
        On page loaded

        :param success: True if loaded successfully
        """
        if success:
            self.init()
            if self.nodes:
                for node in list(self.nodes):
                    self.insert_output(node)
                if not self.loaded:
                    if self.is_dialog:
                        self.nodes = []
            self.loaded = True
            QTimer.singleShot(100, self.scroll_to_bottom)  # wait for rendering to complete
            self.update_current_content()

    def get_selected_text(self) -> str:
        """
        Get selected text

        :return: selected text
        """
        if not self.page():
            return ""
        return self.page().selectedText()

    def copy_selected_text(self):
        """Copy selected text"""
        if not self.page():
            return
        self.page().triggerAction(QWebEnginePage.Copy)

    def select_all_text(self):
        """Select all text"""
        if not self.page():
            return
        self.page().triggerAction(QWebEnginePage.SelectAll)

    def unselect_text(self):
        """Unselect text"""
        if not self.page():
            return
        self.page().triggerAction(QWebEnginePage.Unselect)

    def find_open(self):
        """Open find dialog"""
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        """On content update"""
        self.finder.clear()  # clear finder

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        super(HtmlOutput, self).focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if (event.type() == QEvent.ChildAdded and
                source is self and
                event.child().isWidgetType()):
            self._glwidget = event.child()
            self._glwidget.installEventFilter(self)
        elif event.type() == event.Type.MouseButtonPress:
            if self.tab:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        elif event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        elif event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_F and (event.modifiers() & Qt.ControlModifier):
                self.find_open()
        return super().eventFilter(source, event)


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage to handle web events"""
    def __init__(self, window, parent):
        super(CustomWebEnginePage, self).__init__(window)
        self.window = window
        self.parent = parent
        self.signals = WebEnginePageSignals()
        self.findTextFinished.connect(self.on_find_finished)
        self.zoomFactorChanged.connect(self.on_view_changed)
        self.selectionChanged.connect(self.on_selection_changed)
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )
        self.settings().setFontFamily(QWebEngineSettings.StandardFont, 'Lato')
        self.settings().setFontFamily(QWebEngineSettings.FixedFont, 'Monaspace Neon')
        self.settings().setFontFamily(QWebEngineSettings.SerifFont, 'Monaspace Neon')
        if self.window.core.config.has("zoom"):
            self.setZoomFactor(self.window.core.config.get("zoom"))

        # bridge Python <> JavaScript
        self.bridge = Bridge(self.window)
        self.channel = QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.setWebChannel(self.channel)

    def on_find_finished(self, result):
        """
        On find text finished

        :param result: Find result
        """
        current = int(result.activeMatch())
        num = int(result.numberOfMatches())
        self.parent.finder.current_match_index = current
        self.parent.finder.matches = num
        self.parent.finder.on_find_finished()

    def on_view_changed(self):
        """On view changed"""
        zoom = self.zoomFactor()
        self.window.core.config.set("zoom", zoom)
        option = self.window.controller.settings.editor.get_option('zoom')
        option['value'] = zoom
        self.window.controller.config.apply(
            parent_id='config',
            key='zoom',
            option=option,
        )

    def on_selection_changed(self):
        """On selection changed"""
        pass

    def acceptNavigationRequest(self, url,  _type, isMainFrame):
        """
        On navigation (link click) event

        :param url: URL
        :param _type: Navigation type
        :param isMainFrame: True if main frame
        """
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            self.window.core.filesystem.url.handle(url)
            return False
        return super().acceptNavigationRequest(url,  _type, isMainFrame)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        """
        On JavaScript console message

        :param level: log level
        :param message: message
        :param line_number: line number
        :param source_id: source ID
        """
        self.signals.js_message.emit(line_number, message, source_id)  # handled in debug controller


class Bridge(QObject):
    """Bridge between Python and JavaScript"""
    def __init__(self, window):
        super(Bridge, self).__init__(window)
        self.window = window

    @Slot(str)
    def log(self, text: str):
        """
        Log message from JS

        :param text: text
        """
        print(f"JS log: {text}")

    @Slot(str)
    def copy_text(self, text: str):
        """
        Copy text from web to clipboard

        :param text: text
        """
        self.window.controller.ctx.extra.copy_code_text(text)

    @Slot(str)
    def preview_text(self, text: str):
        """
        Preview code

        :param text: text
        """
        self.window.controller.ctx.extra.preview_code_text(text)

    @Slot(int)
    def update_scroll_position(self, pos: int):
        """
        Update scroll position from web view

        :param pos: scroll position
        """
        self.window.controller.chat.render.scroll = pos

class WebEngineSignals(QObject):
    save_as = Signal(str, str)
    audio_read = Signal(str)

class WebEnginePageSignals(QObject):
    js_message = Signal(int, str, str)  # on Javascript message

