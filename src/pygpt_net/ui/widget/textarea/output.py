#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.20 06:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtGui import QAction, QIcon, QTextOption, QKeySequence

from pygpt_net.core.text.finder import Finder
from pygpt_net.core.text.web_finder import WebFinder
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ChatOutput(QTextBrowser):
    def __init__(self, window=None):
        """
        Chat output

        :param window: main window
        """
        super(ChatOutput, self).__init__(window)
        self.window = window
        self.finder = Finder(window, self)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setStyleSheet(self.window.controller.theme.style('font.chat.output'))
        self.value = self.window.core.config.get('font_size')
        self.max_font_size = 42
        self.min_font_size = 8
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.open_external_link)
        self.setWordWrapMode(QTextOption.WordWrap)

    def open_external_link(self, url):
        """
        Handle external link

        :param url: url
        """
        self.window.core.filesystem.url.handle(url)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        selected_text = self.textCursor().selectedText()

        if selected_text:
            # plain text
            plain_text = self.textCursor().selection().toPlainText()

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            # copy to
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(self, selected_text)
            menu.addMenu(copy_to_menu)

            # save as (selected)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            # save as (all)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def find_open(self):
        """Open find dialog"""
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        """On content update"""
        self.finder.clear()  # clear finder

    def keyPressEvent(self, e):
        """
        Key press event

        :param e: Event
        """
        if e.key() == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self.find_open()
        else:
            super(ChatOutput, self).keyPressEvent(e)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            self.window.core.config.data['font_size'] = self.value
            self.window.core.config.save()
            option = self.window.controller.settings.editor.get_option('font_size')
            option['value'] = self.value
            self.window.controller.config.apply(
                parent_id='config', 
                key='font_size', 
                option=option,
            )
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(ChatOutput, self).wheelEvent(event)

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        super(ChatOutput, self).focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)


class ChatWebOutput(QWebEngineView):
    def __init__(self, window=None):
        """
        HTML output (Webkit)

        :param window: main window
        """
        super(ChatWebOutput, self).__init__(window)
        self.window = window
        self.finder = WebFinder(window, self)
        self.loadFinished.connect(self.on_page_loaded)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page().settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )

    def update_zoom(self):
        """Update zoom from config"""
        if self.window.core.config.has("zoom"):
            self.page().setZoomFactor(self.window.core.config.get("zoom"))

    def get_zoom_value(self) -> float:
        """
        Get zoom value

        :return: zoom value
        """
        return self.page().zoomFactor()

    def on_page_loaded(self, success):
        """
        On page loaded

        :param success: True if loaded successfully
        """
        if success:
            self.window.controller.chat.render.on_page_loaded()

    def open_external_link(self, url):
        """
        Handle external link

        :param url: url
        """
        self.window.core.filesystem.url.handle(url)

    def get_selected_text(self) -> str:
        """
        Get selected text

        :return: selected text
        """
        return self.page().selectedText()

    def on_context_menu(self, position):
        """
        Context menu event

        :param position: position
        """
        menu = self.createStandardContextMenu()

        # remove all items from menu
        for action in menu.actions()[::-1]:
            menu.removeAction(action)

        if self.page().hasSelection():
            selected_text = self.get_selected_text()

            # copy
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
            action.triggered.connect(self.copy_selected_text)
            menu.addAction(action)

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(
                lambda: self.audio_read_selection(selected_text)
            )
            menu.addAction(action)

            # copy to
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(self, selected_text)
            menu.addMenu(copy_to_menu)

            # save as (selected)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(selected_text))
            menu.addAction(action)
        else:
            # select all
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.select_all'), self)
            action.triggered.connect(self.select_all_text)
            menu.addAction(action)

            # save as (all)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(selected_text))
            menu.addAction(action)

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def copy_selected_text(self):
        self.page().triggerAction(QWebEnginePage.Copy)

    def select_all_text(self):
        self.page().triggerAction(QWebEnginePage.SelectAll)

    def audio_read_selection(self, text):
        """
        Read selected text (audio)

        :param text: text to read
        """
        self.window.controller.audio.read_text(text)

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
        super(ChatWebOutput, self).focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage to handle web events"""
    def __init__(self, window, parent):
        super(CustomWebEnginePage, self).__init__(window)
        self.window = window
        self.findTextFinished.connect(self.on_find_finished)
        self.contentsSizeChanged.connect(self.on_view_changed)
        self.selectionChanged.connect(self.on_selection_changed)
        self.parent = parent
        if self.window.core.config.has("zoom"):
            self.setZoomFactor(self.window.core.config.get("zoom"))
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )
        self.settings().setFontFamily(QWebEngineSettings.StandardFont, 'Lato')
        self.settings().setFontFamily(QWebEngineSettings.FixedFont, 'Monaspace Neon')
        self.settings().setFontFamily(QWebEngineSettings.SerifFont, 'Monaspace Neon')

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
        """On navigation (link click) event"""
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            self.window.core.filesystem.url.handle(url)
            return False
        return super().acceptNavigationRequest(url,  _type, isMainFrame)
