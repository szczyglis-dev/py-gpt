#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 00:00:00                  #
# ================================================== #
import base64
import mimetypes
import os
import shutil
from urllib.parse import unquote, unquote_to_bytes, urlparse

from PySide6 import QtCore
from PySide6.QtCore import Qt, QObject, Signal, Slot, QEvent, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEngineSettings, QWebEnginePage, QWebEngineProfile, QWebEngineDownloadRequest,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import QMenu, QDialog, QVBoxLayout, QWidget, QFileDialog

from pygpt_net.core.qt import safe_emit
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
        self.setMouseTracking(True)

        # Context-menu downloads are handed back to Chromium/WebEngine, so
        # they reuse the page profile, cookies, redirects and content handling.
        # The pending entry supplies the exact path chosen in our save dialog.
        self._pending_link_downloads = []

        # OpenGL widgets
        self._glwidget = None
        self._glwidget_filter_installed = False
        self._unloaded = False
        self._destroyed = False

        # set the page with a shared profile
        self.setUpdatesEnabled(False)  # disable updates until the page is set, re-enable in `on_page_loaded`

        # self._profile = self._make_profile(self)
        self.setPage(CustomWebEnginePage(self.window, self, profile=None))

        # Every ChatWebOutput owns a separate page.  Bind its JS console signal
        # immediately so new tabs and renderer-recycled views are visible in
        # Debug -> Logger as well, not only the page active during startup.
        try:
            self.window.controller.debug.connect_page_signals(self.page())
        except (AttributeError, RuntimeError):
            pass

        self._install_web_content_filters()
        try:
            self.page().profile().downloadRequested.connect(self._on_download_requested)
        except Exception:
            pass

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

    def _install_web_content_filters(self, root=None):
        """Observe Chromium child widgets so clicks inside loaded HTML activate the column."""
        if root is None:
            root = self
        try:
            children = root.children()
        except Exception:
            return
        for child in children:
            if not isinstance(child, QWidget):
                continue
            try:
                if not child.property("_pygpt_chat_web_focus_filter"):
                    child.installEventFilter(self)
                    child.setProperty("_pygpt_chat_web_focus_filter", True)
            except Exception:
                continue
            self._install_web_content_filters(child)

    def _activate_tab_column(self):
        """Mark the owning output column as active without stealing WebEngine focus."""
        try:
            if self.tab is not None:
                self.window.controller.ui.tabs.on_column_focus(self.tab.column_idx)
        except Exception:
            pass

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
        """Clean up on delete without entering a nested Qt event loop."""
        if self._destroyed:
            return

        # Mark cleanup as started before scheduling deletion.  ``deleteLater`` is
        # intentionally asynchronous: forcing DeferredDelete processing here can
        # re-enter renderer/timer code while registries still reference this
        # Python wrapper, producing "Internal C++ object ... already deleted".
        self._destroyed = True

        if not self._unloaded:
            self.unload()

        self.hide()
        self._detach_gl_event_filter()

        self._pending_link_downloads.clear()

        try:
            self.page().profile().downloadRequested.disconnect(self._on_download_requested)
        except Exception:
            pass

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

    def eventFilter(self, source, event):
        """
        Event filter to handle child added events and mouse button presses

        :param source: QWidget - source of the event
        :param event: QEvent - event to filter
        """
        if event.type() == QEvent.ChildAdded:
            try:
                child = event.child()
                if child is not None and child.isWidgetType():
                    if source is self:
                        self._glwidget = child
                    if isinstance(child, QWidget):
                        if not child.property("_pygpt_chat_web_focus_filter"):
                            child.installEventFilter(self)
                            child.setProperty("_pygpt_chat_web_focus_filter", True)
                        if source is self:
                            self._glwidget_filter_installed = True
                        self._install_web_content_filters(child)
            except Exception:
                pass

        elif event.type() == QEvent.Type.MouseButtonPress:
            self._activate_tab_column()

        return super().eventFilter(source, event)

    def on_focus(self, widget):
        """
        On widget clicked

        :param widget: QWidget - widget that received focus
        """
        self._activate_tab_column()
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

    def _context_link_url(self) -> str:
        """Return the resource URL under the WebEngine context-menu request.

        Prefer the anchor href. When RMB is used directly on an image/media
        element without an anchor, fall back to mediaUrl() so the same open /
        download actions are still available.
        """
        try:
            getter = getattr(self, "lastContextMenuRequest", None)
            request = getter() if callable(getter) else None
            if request is None:
                return ""

            link = request.linkUrl()
            if link is not None and not link.isEmpty() and link.isValid():
                return link.toString()

            media_getter = getattr(request, "mediaUrl", None)
            media = media_getter() if callable(media_getter) else None
            if media is not None and not media.isEmpty() and media.isValid():
                return media.toString()
        except Exception:
            pass
        return ""

    def _resolve_web_link(self, url: str):
        """Resolve a href/media URL through the shared filesystem resolver."""
        try:
            return self.window.core.filesystem.url.resolver.resolve(
                url,
                ctx=self.meta,
            )
        except Exception as exc:
            self.window.core.debug.error(exc)
            return None

    def _open_link_external(self, link):
        """Open a resolved href in the OS/default external application."""
        if isinstance(link, str):
            link = self._resolve_web_link(link)
        if link is None or not link.can_open_external:
            return

        if link.kind == "local" and link.local_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(link.local_path))
            return
        if link.target:
            QDesktopServices.openUrl(QUrl(link.target, QUrl.TolerantMode))

    def _open_link_internal(self, link):
        """Open a resolved href in PyGPT's internal Web Browser tool."""
        if isinstance(link, str):
            link = self._resolve_web_link(link)
        if link is None or not link.can_open_internal or not link.target:
            return
        try:
            tool = self.window.tools.get("web_browser")
            if tool is None:
                return
            # Always force the internal browser for this context-menu action,
            # independently from the global external/internal URL preference.
            tool.set_url(link.target)
            tool.auto_open(load=False)
        except Exception as exc:
            self.window.core.debug.error(exc)

    @staticmethod
    def _download_filename(link) -> str:
        """Build a safe suggested filename for a resolved resource."""
        if link is None:
            return "download.bin"

        if link.local_path:
            name = os.path.basename(link.local_path.rstrip(os.sep)).strip()
            if name:
                return name

        if link.kind == "data":
            try:
                header = link.target.split(',', 1)[0]
                mime = header[5:].split(';', 1)[0].strip()
                ext = mimetypes.guess_extension(mime) if mime else None
                return "download" + (ext or ".bin")
            except Exception:
                return "download.bin"

        try:
            parsed = urlparse(link.target or "")
            name = os.path.basename(unquote(parsed.path or "")).strip()
        except Exception:
            name = ""
        if not name or name in (".", ".."):
            name = "download.bin"
        return name

    @staticmethod
    def _write_data_url(url: str, target: str) -> bool:
        """Write a data: URL directly instead of handing it to Chromium."""
        try:
            header, payload = url.split(',', 1)
            if ';base64' in header.lower():
                data = base64.b64decode(unquote_to_bytes(payload), validate=False)
            else:
                data = unquote_to_bytes(payload)
            with open(target, 'wb') as handle:
                handle.write(data)
            return True
        except Exception:
            return False

    def _download_link(self, link):
        """Download a resolved href (remote/local/data/blob) to disk."""
        if isinstance(link, str):
            link = self._resolve_web_link(link)
        if link is None or not link.can_download:
            return

        # A directory is not a file download. Reuse the existing folder copy
        # flow, which prompts for a target directory instead of Save As.
        if link.kind == "local" and link.local_path and os.path.isdir(link.local_path):
            self.window.controller.files.download_local(link.local_path)
            return

        filename = self._download_filename(link)
        try:
            base_dir = self.window.core.filesystem.get_data_dir(ctx=self.meta)
            configured = str(self.window.core.config.get("download.dir") or "").strip()
            if configured:
                base_dir = os.path.join(base_dir, configured)
            os.makedirs(base_dir, exist_ok=True)
            suggested = os.path.join(base_dir, filename)
        except Exception:
            suggested = filename

        target, _ = QFileDialog.getSaveFileName(
            self,
            trans("web.context_menu.download"),
            suggested,
        )
        if not target:
            return

        if link.kind == "local":
            source = link.local_path
            if not source or not os.path.isfile(source):
                self.window.update_status(f"{trans('status.error')} File not found: {source or link.target}")
                return
            try:
                if os.path.realpath(source) != os.path.realpath(target):
                    shutil.copy2(source, target)
                self.window.update_status(f"{trans('status.saved')}: {target}")
            except Exception as exc:
                self.window.update_status(f"{trans('status.error')} {exc}")
            return

        if link.kind == "data":
            if self._write_data_url(link.target, target):
                self.window.update_status(f"{trans('status.saved')}: {target}")
            else:
                self.window.update_status(f"{trans('status.error')} Invalid data URL")
            return

        # HTTP(S) and blob: downloads are handed back to this exact WebEngine
        # page. This preserves Chromium cookies/session/redirects and is also
        # required for blob: URLs, which only exist in the current page.
        source_url = link.target
        entry = {
            "url": QUrl(source_url, QUrl.TolerantMode).toString(),
            "target": os.path.abspath(target),
        }
        self._pending_link_downloads.append(entry)
        try:
            self.page().download(QUrl(source_url, QUrl.TolerantMode), os.path.basename(target))
            QtCore.QTimer.singleShot(10000, lambda e=entry: self._expire_pending_download(e))
        except Exception as exc:
            self._expire_pending_download(entry)
            self.window.update_status(f"{trans('status.error')} {exc}")

    def _expire_pending_download(self, entry):
        """Drop an unmatched WebEngine download request token."""
        try:
            self._pending_link_downloads.remove(entry)
        except ValueError:
            pass

    def _on_download_requested(self, download):
        """Accept only a link download initiated by this ChatWebOutput instance."""
        if not self._pending_link_downloads:
            return

        try:
            request_page = download.page()
        except Exception:
            request_page = None
        if request_page is not None and request_page is not self.page():
            return

        try:
            request_url = download.url().toString()
        except Exception:
            request_url = ""

        match = None
        for entry in self._pending_link_downloads:
            if entry.get("url") == request_url:
                match = entry
                break
        # Redirects or provider-normalized URLs can differ from the original.
        # Page identity is sufficient when this view has one pending request.
        if match is None and request_page is self.page() and len(self._pending_link_downloads) == 1:
            match = self._pending_link_downloads[0]
        if match is None:
            return

        self._expire_pending_download(match)
        target = match.get("target") or ""
        try:
            download.setDownloadDirectory(os.path.dirname(target))
            download.setDownloadFileName(os.path.basename(target))
            download.isFinishedChanged.connect(
                lambda d=download, path=target: self._on_link_download_finished(d, path)
            )
            download.accept()
        except Exception as exc:
            try:
                download.cancel()
            except Exception:
                pass
            self.window.update_status(f"{trans('status.error')} {exc}")

    def _on_link_download_finished(self, download, target: str):
        """Report final WebEngine download state in the global status line."""
        try:
            if not download.isFinished():
                return
            state = download.state()
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                self.window.update_status(f"{trans('status.saved')}: {target}")
            elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
                reason = download.interruptReasonString()
                self.window.update_status(
                    f"{trans('status.error')} {reason}".strip()
                )
        except Exception:
            pass

    def on_context_menu(self, position):
        """
        Context menu event

        :param position: QPoint - position of the context menu
        """
        menu = QMenu(self)

        # QWebEngineContextMenuRequest is short-lived. Resolve the href now
        # and capture the plain string in actions that may fire after the menu
        # event itself has returned.
        link_url = self._context_link_url()
        resolved_link = self._resolve_web_link(link_url) if link_url else None
        link_actions_added = False

        if resolved_link is not None and resolved_link.can_open_external:
            action = QAction(
                QIcon(":/icons/public_filled.svg"),
                trans("web.context_menu.open_browser"),
                self,
            )
            action.triggered.connect(
                lambda checked=False, link=resolved_link: self._open_link_external(link)
            )
            menu.addAction(action)
            link_actions_added = True

        if resolved_link is not None and resolved_link.can_open_internal:
            action = QAction(
                QIcon(":/icons/web_on.svg"),
                trans("web.context_menu.open_internal"),
                self,
            )
            action.triggered.connect(
                lambda checked=False, link=resolved_link: self._open_link_internal(link)
            )
            menu.addAction(action)
            link_actions_added = True

        if resolved_link is not None and resolved_link.can_download:
            action = QAction(
                QIcon(":/icons/download.svg"),
                trans("web.context_menu.download"),
                self,
            )
            action.triggered.connect(
                lambda checked=False, link=resolved_link: self._download_link(link)
            )
            menu.addAction(action)
            link_actions_added = True

        if link_actions_added:
            menu.addSeparator()

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

        # Add zoom submenu
        zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "zoom", self.get_zoom_value(), self.on_zoom_changed)
        menu.addMenu(zoom_menu)

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        menu.addAction(action)

        menu.exec_(self.mapToGlobal(position))

    def on_zoom_changed(self, zoom: float):
        """
        On zoom changed from context menu

        :param zoom: float - new zoom factor
        """
        p = self.page()
        if p:
            self.window.core.config.set("zoom", zoom)
            self.update_zoom()

    @Slot()
    def _save_selected_txt(self):
        """Save selected content as text file"""
        safe_emit(self.signals, "save_as", self.get_selected_text(), 'txt')

    @Slot()
    def _read_selected_text(self):
        """
        Read selected text using text-to-speech
        """
        selected_text = self.get_selected_text()
        if selected_text:
            safe_emit(self.signals, "audio_read", selected_text)

    @Slot()
    def _save_as_text(self):
        """
        Save current content as text file
        """
        # TODO: normalize text (remove extra spaces, newlines, etc.)
        self.page().toPlainText(lambda txt: safe_emit(self.signals, "save_as", txt, 'txt'))

    @Slot()
    def _save_as_html(self):
        """
        Save current content as HTML file
        """
        self.page().toHtml(lambda html: safe_emit(self.signals, "save_as", html, 'html'))

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
        self._activate_tab_column()

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
        input_container = self.window.ui.nodes.get('input.container')
        if input_container is not None and hasattr(input_container, 'sync_width'):
            input_container.sync_width()

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            self.window.core.filesystem.url.handle(url, ctx=self.view.meta)
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        print("[JS CONSOLE] Line", line_number, ":", message)
        safe_emit(self.signals, "js_message", line_number, message, source_id)  # handled in debug controller

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