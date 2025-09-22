#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.16 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QObject, Signal, Slot, QEvent, QUrl, QCoreApplication, QEventLoop
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QDialog, QVBoxLayout

from pygpt_net.core.events import RenderEvent
from pygpt_net.item.ctx import CtxMeta
from pygpt_net.core.text.web_finder import WebFinder
from pygpt_net.ui.widget.tabs.layout import FocusEventFilter
from pygpt_net.utils import trans


class ChatWebOutput(QWebEngineView):
    def __init__(self, window=None):
        """
        HTML output (WebEngine)

        :param window: Window instance
        """
        super(ChatWebOutput, self).__init__(window)
        self.window = window
        self.finder = WebFinder(window, self)
        self.loadFinished.connect(self.on_page_loaded)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.signals = WebEngineSignals(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter = FocusEventFilter(self, self.on_focus)
        self.installEventFilter(self)
        self.plain = None
        self.html_content = None
        self.meta = None
        self.tab = None
        self.setProperty('class', 'layout-output-web')

        # OpenGL widgets
        self._glwidget = None
        self._glwidget_filter_installed = False
        self._unloaded = False
        self._destroyed = False

        # set the page with a shared profile
        self.setUpdatesEnabled(False)  # disable updates until the page is set, re-enable in `on_page_loaded`

        # self._profile = self._make_profile(self)
        self.setPage(CustomWebEnginePage(self.window, self, profile=None))

    def _make_profile(self, parent=None) -> QWebEngineProfile:
        """Make profile"""
        profile = QWebEngineProfile(parent)
        # self._profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        # self._profile.setHttpCacheMaximumSize(32 * 1024 * 1024)  # 32MB
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        # self._profile.setHttpCacheType(QWebEngineProfile.NoCache)
        profile.setSpellCheckEnabled(False)
        return profile


    def _detach_gl_event_filter(self):
        """Detach OpenGL widget event filter if installed"""
        if self._glwidget and self._glwidget_filter_installed:
            try:
                self._glwidget.removeEventFilter(self)
            except Exception as e:
                self._on_delete_failed(e)
        self._glwidget = None
        self._glwidget_filter_installed = False

    def _on_delete_failed(self, e):
        """
        Handle delete failure

        :param e: Exception instance
        """
        pass
        # self.window.core.debug.log(e)

    def show_devtools(self, modal: bool = False, title: str = "DevTools"):
        """Show DevTools window"""
        if getattr(self, "_devtools_dlg", None) is None:
            dlg = QDialog(self.window)
            dlg.setWindowTitle(title)
            dlg.setModal(modal)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            dlg.resize(1100, 750)

            layout = QVBoxLayout(dlg)
            view = QWebEngineView(dlg)
            layout.addWidget(view)

            profile = self.page().profile()
            view.setPage(QWebEnginePage(profile, view))

            self.page().setDevToolsPage(view.page())

            dlg.destroyed.connect(lambda: setattr(self, "_devtools_dlg", None))

            self._devtools_dlg = dlg
            self._devtools_view = view

        self._devtools_dlg.show()
        self._devtools_dlg.raise_()
        self._devtools_dlg.activateWindow()

    def unload(self):
        """Unload the current page and free resources"""
        try:
            self.hide()
            p = self.page()
            p.triggerAction(QWebEnginePage.Stop)
            p.setUrl(QUrl("about:blank"))
            p.history().clear()
            p.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
        except Exception as e:
            self._on_delete_failed(e)
        finally:
            self._unloaded = True

    def on_delete(self):
        """Clean up on delete"""
        if self._destroyed:
            return
        if not self._unloaded:
            self.unload()

        self.hide()
        self._detach_gl_event_filter()

        if self.finder:
            try:
                self.finder.disconnect()
            except Exception as e:
                self._on_delete_failed(e)
            finally:
                self.finder = None

        self.tab = None
        self.meta = None

        # safely unhook signals (may not have been hooked)
        for sig, slot in (
                (self.loadFinished, self.on_page_loaded),
                (self.customContextMenuRequested, self.on_context_menu),
                (self.signals.save_as, getattr(self.window.controller.chat.render, "handle_save_as", None)),
                (self.signals.audio_read, getattr(self.window.controller.chat.render, "handle_audio_read", None)),
        ):
            if slot:
                try:
                    sig.disconnect(slot)
                except Exception as e:
                    self._on_delete_failed(e)

        page = self.page()
        page.set_loaded(False)

        try:
            page.triggerAction(QWebEnginePage.Stop)
        except Exception as e:
            self._on_delete_failed(e)

        try:
            page.setUrl(QUrl("about:blank"))
        except Exception as e:
            self._on_delete_failed(e)

        try:
            page.history().clear()
        except Exception as e:
            self._on_delete_failed(e)

        try:
            page.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
        except Exception as e:
            self._on_delete_failed(e)

        try:
            if hasattr(page, "setWebChannel"):
                page.setWebChannel(None)
        except Exception as e:
            self._on_delete_failed(e)

        prof = None
        try:
            prof = page.profile()
        except Exception as e:
            self._on_delete_failed(e)

        try:
            page.cleanup()
        except Exception as e:
            self._on_delete_failed(e)

        """
        if prof is not None:
            try:
                prof.deleteLater()
            except Exception as e:
                self._on_delete_failed(e)
        """

        try:
            self.deleteLater()
        except Exception as e:
            self._on_delete_failed(e)

        try:
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QCoreApplication.processEvents(QEventLoop.AllEvents, 50)
        except Exception as e:
            self._on_delete_failed(e)

        self._destroyed = True

    def eventFilter(self, source, event):
        """
        Event filter to handle child added events and mouse button presses

        :param source: QWidget - source of the event
        :param event: QEvent - event to filter
        """
        if event.type() == QEvent.ChildAdded and source is self and event.child().isWidgetType():
            self._detach_gl_event_filter()
            self._glwidget = event.child()
            try:
                self._glwidget.installEventFilter(self)
                self._glwidget_filter_installed = True
            except Exception:
                self._glwidget = None
                self._glwidget_filter_installed = False

        elif event.type() == QEvent.Type.MouseButtonPress:
            try:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
            except Exception:
                pass

        return super().eventFilter(source, event)

    def on_focus(self, widget):
        """
        On widget clicked

        :param widget: QWidget - widget that received focus
        """
        if self.tab is not None:
            self.window.controller.ui.tabs.on_column_focus(self.tab.column_idx)
        self.setFocus()

    def set_tab(self, tab):
        """
        Set tab for this output

        :param tab: Tab instance
        """
        self.tab = tab

    def get_tab(self):
        """
        Get current tab

        :return: Tab instance
        """
        return self.tab

    def set_meta(self, meta: CtxMeta):
        """
        Set meta for this output

        :param meta: CtxMeta instance
        """
        self.meta = meta

    def set_plaintext(self, text: str):
        """
        Set plain text content

        :param text: str - plain text content
        """
        self.plain = text

    def set_html_content(self, html: str):
        """
        Set HTML content

        :param html: str - HTML content
        """
        self.html_content = "<html>" + html + "</html>"

    def on_context_menu(self, position):
        """
        Context menu event

        :param position: QPoint - position of the context menu
        """
        menu = QMenu(self)

        has_selection = self.page().hasSelection()

        if has_selection:
            # copy
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
            action.triggered.connect(self.copy_selected_text)
            menu.addAction(action)

            # audio read (get text only on click, don't copy immediately)
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self._read_selected_text)
            menu.addAction(action)

            # copy to
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, self.get_selected_text())
            menu.addMenu(copy_to_menu)

            # save as (selected) - get selection at the moment of click
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self)
            action.triggered.connect(self._save_selected_txt)
            menu.addAction(action)
        else:
            # select all
            action = QAction(QIcon(":/icons/copy.svg"), trans('action.select_all'), self)
            action.triggered.connect(self.select_all_text)
            menu.addAction(action)

            # save as (all) - plain (lazy normalization only on click)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as') + " (text)", self)
            action.triggered.connect(self._save_as_text)
            menu.addAction(action)

            # save as (all) - html
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as') + " (html)", self)
            action.triggered.connect(self._save_as_html)
            menu.addAction(action)

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    @Slot()
    def _save_selected_txt(self):
        """Save selected content as text file"""
        self.signals.save_as.emit(self.get_selected_text(), 'txt')

    @Slot()
    def _read_selected_text(self):
        """
        Read selected text using text-to-speech
        """
        selected_text = self.get_selected_text()
        if selected_text:
            self.signals.audio_read.emit(selected_text)

    @Slot()
    def _save_as_text(self):
        """
        Save current content as text file
        """
        # TODO: normalize text (remove extra spaces, newlines, etc.)
        self.page().toPlainText(lambda txt: self.signals.save_as.emit(txt, 'txt'))

    @Slot()
    def _save_as_html(self):
        """
        Save current content as HTML file
        """
        self.page().toHtml(lambda html: self.signals.save_as.emit(html, 'html'))

    def update_zoom(self):
        """Update zoom from config"""
        try:
            if self.window.core.config.has("zoom"):
                p = self.page()
                if p:
                    p.setZoomFactor(self.window.core.config.get("zoom"))
        except Exception:
            pass

    def on_focus_js(self):
        """Focus JavaScript"""
        if self.tab is not None:
            self.window.controller.ui.tabs.on_column_focus(self.tab.column_idx)

    def get_zoom_value(self) -> float:
        """
        Get current zoom value

        :return: zoom factor
        """
        p = self.page()
        return p.zoomFactor() if p else 1.0

    def reset_current_content(self):
        """Reset current content"""
        self.plain = ""
        self.html_content = ""

    def on_page_loaded(self, success):
        """
        Page loaded event handler

        :param success: bool - True if page loaded successfully, False otherwise
        """
        if success:
            event = RenderEvent(RenderEvent.ON_PAGE_LOAD, {
                "meta": self.meta,
                "tab": self.tab,
            })
            self.window.dispatch(event)
            self.setUpdatesEnabled(True)
            p = self.page()
            if p and isinstance(p, CustomWebEnginePage):
                p.set_loaded(True)

    def get_selected_text(self) -> str:
        p = self.page()
        return p.selectedText() if p else ""

    def copy_selected_text(self):
        p = self.page()
        if p:
            p.triggerAction(QWebEnginePage.Copy)

    def select_all_text(self):
        p = self.page()
        if p:
            p.triggerAction(QWebEnginePage.SelectAll)

    def unselect_text(self):
        p = self.page()
        if p:
            p.triggerAction(QWebEnginePage.Unselect)

    def find_open(self):
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        if self.finder:
            self.finder.clear()

    def focusInEvent(self, e):
        super(ChatWebOutput, self).focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEnginePage to handle web events"""

    def __init__(self, window, view, profile: QWebEngineProfile = None):

        # use the profile if provided, otherwise the default
        if profile is not None:
            super(CustomWebEnginePage, self).__init__(profile, view)
        else:
            super(CustomWebEnginePage, self).__init__(view)

        self.window = window
        self.view = view
        self.loaded = False

        # signals have parent=page (automatic cleanup)
        self.signals = WebEnginePageSignals(self)

        self.findTextFinished.connect(self.on_find_finished)
        self.zoomFactorChanged.connect(self.on_view_changed)

        s = self.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setFontFamily(QWebEngineSettings.StandardFont, 'Lato')
        s.setFontFamily(QWebEngineSettings.FixedFont, 'Monaspace Neon')
        s.setFontFamily(QWebEngineSettings.SerifFont, 'Monaspace Neon')
        s.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        s.setAttribute(QWebEngineSettings.ScreenCaptureEnabled, False)
        s.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        s.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)
        s.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)

        if self.window.core.config.has("zoom"):
            self.setZoomFactor(self.window.core.config.get("zoom"))

        # bridge Python <> JavaScript
        # KEY: parent=page, -> disappears along with the page
        self.bridge = Bridge(self.window, parent=self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.setWebChannel(self.channel)

    def set_loaded(self, loaded: bool = True):
        self.loaded = loaded

    def on_find_finished(self, result):
        current = int(result.activeMatch())
        num = int(result.numberOfMatches())
        self.view.finder.current_match_index = current
        self.view.finder.matches = num
        self.view.finder.on_find_finished()

    def on_view_changed(self):
        if not self.loaded:
            return
        zoom = self.zoomFactor()
        self.window.core.config.set("zoom", zoom)
        option = self.window.controller.settings.editor.get_option('zoom')
        option['value'] = zoom
        self.window.controller.config.apply(
            parent_id='config',
            key='zoom',
            option=option,
        )

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            self.window.core.filesystem.url.handle(url)
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        print("[JS CONSOLE] Line", line_number, ":", message)
        self.signals.js_message.emit(line_number, message, source_id)  # handled in debug controller

    def cleanup(self):
        """Cleanup method to release resources"""
        self.loaded = False
        try:
            self.findTextFinished.disconnect()
            self.zoomFactorChanged.disconnect()
            self.selectionChanged.disconnect()
        except Exception:
            pass

        if self.bridge:
            try:
                self.bridge.cleanup()
            except Exception:
                pass
            self.bridge = None

        if self.channel:
            try:
                self.channel.unregisterObject("bridge")
            except Exception:
                pass
            self.channel = None

        if self.signals:
            try:
                self.signals.deleteLater()
            except Exception:
                pass
            self.signals = None


class Bridge(QObject):
    """Bridge between Python and JavaScript"""

    def __init__(self, window, parent=None):
        super(Bridge, self).__init__(parent)
        self.window = window

    chunk = Signal(str, str, str)  # name, chunk, type
    node = Signal(str)  # JSON payload
    nodeReplace = Signal(str)  # JSON payload
    nodeInput = Signal(str)  # raw text
    readyChanged = Signal(bool)

    @Slot(int)
    def js_ready(self, pid: int):
        self.readyChanged.emit(True)
        self.window.controller.chat.render.on_js_ready(pid)

    @Slot(str)
    def log(self, text: str):
        print(f"JS log: {text}")

    @Slot(str)
    def copy_text(self, text: str):
        self.window.controller.ctx.extra.copy_code_text(text)

    @Slot(str)
    def preview_text(self, text: str):
        self.window.controller.ctx.extra.preview_code_text(text)

    @Slot(str)
    def run_text(self, text: str):
        self.window.controller.ctx.extra.run_code_text(text)

    @Slot(int)
    def update_scroll_position(self, pos: int):
        self.window.controller.chat.render.scroll = pos

    def cleanup(self):
        """Cleanup method to release resources"""
        if self.window:
            try:
                self.window = None
            except Exception:
                pass

        # delete the bridge object
        self.deleteLater()


class WebEngineSignals(QObject):
    save_as = Signal(str, str)
    audio_read = Signal(str)


class WebEnginePageSignals(QObject):
    js_message = Signal(int, str, str)  # on JavaScript message