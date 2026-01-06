#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 19:00:00                  #
# ================================================== #

import hashlib
import os
import shutil
from typing import Dict, Optional, List, Tuple

from PySide6 import QtGui, QtCore
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog

from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.image_viewer.ui.dialogs import DialogSpawner
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class ImageViewer(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Image viewer

        :param window: Window instance
        """
        super(ImageViewer, self).__init__(*args, **kwargs)
        self.id = "viewer"
        self.width = 640
        self.height = 400
        self.instance_id = 0
        self.spawner = None

    def setup(self):
        """Setup tool"""
        self.spawner = DialogSpawner(self.window)

    def prepare_id(self, file: str):
        """
        Prepare unique id for file

        :param file: file name
        :return: unique id
        """
        return 'image_viewer_' + hashlib.md5(file.encode('utf-8')).hexdigest()

    def new(self):
        """New image viewer dialog"""
        self.open_preview()

    def open_file(self, id: str, auto_close: bool = True,):
        """
        Open image file dialog

        :param id: dialog id
        :param auto_close: auto close current dialog
        """
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.open"),
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *webp);; All files (*.*)")
        if path:
            self.open_preview(path, id, auto_close)

    def open_preview_batch(
            self,
            paths: list,
            current_id: str = None,
            auto_close: bool = True):
        """
        Open image preview batch in dialog

        :param paths:
        :param current_id:
        :param auto_close:
        :return:
        """
        for path in paths:
            self.open_preview(path, current_id, auto_close)

    def open_preview(
            self,
            path: str = None,
            current_id: str = None,
            auto_close: bool = True,
            reuse: bool = False):
        """
        Open image preview in dialog

        :param path: path to image
        :param current_id: current dialog id
        :param auto_close: auto close current dialog
        :param reuse: reuse existing dialog id (in-place reload)
        """
        # determine dialog id
        if path:
            if reuse and current_id:
                id = current_id
            else:
                id = self.prepare_id(path)
                if current_id and auto_close:
                    if id != current_id:
                        self.close_preview(current_id)
        else:
            # new instance id
            id = 'image_viewer_' + str(self.instance_id)
            self.instance_id += 1

        dialog_exists = id in self.window.ui.dialog
        if not dialog_exists:
            self.window.ui.dialogs.open_instance(
                id,
                width=self.width,
                height=self.height,
                type="image_viewer",
            )

        # dimensions: keep current size if dialog already exists
        if id in self.window.ui.dialog:
            w = self.window.ui.dialog[id].width()
            h = self.window.ui.dialog[id].height()
        else:
            w = self.width
            h = self.height

        img_suffix = ""

        # compute directory index/total for status bar if possible
        def _index_and_total(p: Optional[str]) -> Tuple[int, int]:
            if not p:
                return 0, 0
            files = self._list_images_in_dir(p)
            total = len(files)
            if total == 0:
                return 0, 0
            try:
                idx = files.index(p)
            except ValueError:
                low = [x.lower() for x in files]
                try:
                    idx = low.index(p.lower())
                except ValueError:
                    return 0, total
            # convert to 1-based for display
            return idx + 1, total

        if path is None:
            # reuse previous image path if any
            if id in self.window.ui.dialog and hasattr(self.window.ui.dialog[id].source, 'path'):
                path = self.window.ui.dialog[id].source.path

        if path is None:
            # blank image
            pixmap = QtGui.QPixmap(0, 0)
            self.window.ui.dialog[id].source.setPixmap(pixmap)
            self.window.ui.dialog[id].source.path = None
            self.window.ui.dialog[id].pixmap.path = None
            self.window.ui.dialog[id].pixmap.resize(w, h)
            self.window.ui.dialog[id].path = None
            self.window.ui.dialog[id].setWindowTitle("Image Viewer")

            # update status bar to empty state
            try:
                self.window.ui.dialog[id].set_status_meta(index=0, total=0, img_size=pixmap.size(), file_size_str="")
            except Exception:
                pass
        else:
            # load image
            src_pixmap = QtGui.QPixmap(path)
            img_suffix = " ({}x{}px)".format(src_pixmap.width(), src_pixmap.height())
            file_size = self.window.core.filesystem.sizeof_fmt(os.path.getsize(path))
            img_suffix += " - {}".format(file_size)

            # in-place reload when reusing the same dialog
            if reuse and (current_id == id) and (id in self.window.ui.dialog):
                dialog = self.window.ui.dialog[id]
                dialog.source.setPixmap(src_pixmap)
                dialog.source.path = path
                dialog.pixmap.path = path

                # reset zoom/pan to fit and update view without resizing window
                dialog._zoom_mode = 'fit'
                dialog._drag_active = False
                if dialog.scroll_area is not None:
                    dialog.scroll_area.setWidgetResizable(True)
                if dialog.pixmap is not None:
                    dialog.pixmap.setScaledContents(False)
                target = dialog._viewport_size()
                scaled = src_pixmap.scaled(target, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                dialog.pixmap.setPixmap(scaled)
                dialog._fit_factor = dialog._compute_fit_factor(src_pixmap.size(), target)
                dialog._last_src_key = src_pixmap.cacheKey()
                dialog._last_target_size = target

                dialog.path = path
                dialog.setWindowTitle(os.path.basename(path) + img_suffix)

                # update status bar metadata (index/total, original size, file size)
                try:
                    idx, total = _index_and_total(path)
                    dialog.set_status_meta(index=idx, total=total, img_size=src_pixmap.size(), file_size_str=file_size)
                except Exception:
                    pass

                # keep dialog visible but do not force reposition
                if not dialog.isVisible():
                    dialog.show()
            else:
                # standard open path
                self.window.ui.dialog[id].source.setPixmap(src_pixmap)
                self.window.ui.dialog[id].source.path = path
                self.window.ui.dialog[id].pixmap.path = path
                self.window.ui.dialog[id].pixmap.resize(w, h)
                self.window.ui.dialog[id].path = path
                self.window.ui.dialog[id].setWindowTitle(os.path.basename(path) + img_suffix)

                # update status bar metadata before first resizeEvent recomputes fit
                try:
                    idx, total = _index_and_total(path)
                    self.window.ui.dialog[id].set_status_meta(index=idx, total=total, img_size=src_pixmap.size(), file_size_str=file_size)
                except Exception:
                    pass

        # ensure dialog visible without altering user-set position if already shown
        dlg = self.window.ui.dialog[id]
        if not dlg.isVisible():
            dlg.show()

        # refresh drawing when needed (avoid forcing default size on reuse)
        if not (reuse and (current_id == id)):
            dlg.resize(w - 1, h - 1)  # redraw fix
            dlg.resize(w, h)

        # update toolbar actions availability
        self._update_toolbar_actions_state(id)

    def close_preview(self, id: str):
        """
        Close image preview dialog

        :param id: dialog id
        """
        self.window.ui.dialog[id].resize(self.width - 1, self.height - 1)  # redraw fix
        self.window.ui.dialog[id].close()

    def open_images(self, paths: list):
        """
        Open image in dialog

        :param paths: paths to images
        """
        num_images = len(paths)
        resize_to = 512
        if num_images > 1:
            resize_to = 256
        w = 520
        h = 520
        i = 0
        for path in paths:
            pixmap = QtGui.QPixmap(path)
            pixmap = pixmap.scaled(resize_to, resize_to, QtCore.Qt.KeepAspectRatio)
            self.window.ui.nodes['dialog.image.pixmap'][i].path = path
            self.window.ui.nodes['dialog.image.pixmap'][i].setPixmap(pixmap)
            self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(True)
            i += 1

        # hide unused images
        for j in range(i, 4):
            self.window.ui.nodes['dialog.image.pixmap'][j].setVisible(False)

        # resize dialog
        self.window.ui.dialog['image'].resize(w, h)
        self.window.ui.dialog['image'].show()

    def close_images(self):
        """Close image dialog"""
        self.window.ui.dialog['image'].close()

    def open(self, path: str):
        """
        Open image in default image viewer

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open(path)

    def open_dir(self, path: str):
        """
        Open directory in file manager

        :param path: path to image
        """
        if os.path.exists(path):
            self.window.controller.files.open_dir(
                path,
                True,
            )

    def save_by_id(self, id: str):
        """
        Save image by dialog id

        :param id: dialog id
        """
        if id in self.window.ui.dialog:
            path = self.window.ui.dialog[id].path
            if path:
                self.save(path)
            else:
                self.window.update_status("No image to save")

    def save(self, path: str):
        """
        Save image

        :param path: path to image
        """
        if path is None:
            self.window.update_status("No image to save")
            return

        save_path = QFileDialog.getSaveFileName(
            self.window,
            trans('img.save.title'),
            os.path.basename(path),
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *webp);; All files (*.*)"
        )
        if save_path:
            try:
                if save_path[0] == '':
                    return
                shutil.copyfile(path, save_path[0])
                self.window.update_status(trans('status.img.saved') + ": {}".format(os.path.basename(save_path[0])))
            except Exception as e:
                self.window.core.debug.log(e)

    def delete(self, path: str, force: bool = False):
        """
        Delete image

        :param path: path to image
        :param force: force delete without confirmation
        """
        if path is None:
            self.window.update_status("No image to delete")
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='img_delete',
                id=path,
                msg=trans('confirm.img.delete'),
            )
            return
        try:
            os.remove(path)
            for i in range(0, 4):
                if self.window.ui.nodes['dialog.image.pixmap'][i].path == path:
                    self.window.ui.nodes['dialog.image.pixmap'][i].setVisible(False)
        except Exception as e:
            self.window.core.debug.log(e)

    # =========================
    # Toolbar actions (prev/next/open dir/copy/fullscreen)
    # =========================

    def prev_by_id(self, id: str):
        """
        Show previous image in the same directory (with wrap-around).
        """
        dialog = self.window.ui.dialog.get(id)
        if dialog is None or dialog.path is None:
            self.window.update_status("No image selected")
            return

        prev_path, _ = self._get_neighbors(dialog.path)
        if prev_path:
            self.open_preview(prev_path, current_id=id, auto_close=False, reuse=True)
        else:
            self.window.update_status("No previous image")

    def next_by_id(self, id: str):
        """
        Show next image in the same directory (with wrap-around).
        """
        dialog = self.window.ui.dialog.get(id)
        if dialog is None or dialog.path is None:
            self.window.update_status("No image selected")
            return

        _, next_path = self._get_neighbors(dialog.path)
        if next_path:
            self.open_preview(next_path, current_id=id, auto_close=False, reuse=True)
        else:
            self.window.update_status("No next image")

    def open_dir_by_id(self, id: str):
        """
        Open current image in file manager (select in directory if supported).
        """
        dialog = self.window.ui.dialog.get(id)
        if not dialog or not dialog.path:
            self.window.update_status("No image to open in directory")
            return
        self.open_dir(dialog.path)

    def copy_by_id(self, id: str):
        """
        Copy current image to clipboard.
        """
        dialog = self.window.ui.dialog.get(id)
        if not dialog:
            self.window.update_status("No dialog")
            return
        pixmap = None
        try:
            if dialog.source is not None and dialog.source.pixmap() is not None and not dialog.source.pixmap().isNull():
                pixmap = dialog.source.pixmap()
            elif dialog.path and os.path.exists(dialog.path):
                pixmap = QtGui.QPixmap(dialog.path)
        except Exception as e:
            self.window.core.debug.log(e)
        if pixmap is None or pixmap.isNull():
            self.window.update_status("No image to copy")
            return
        QtGui.QGuiApplication.clipboard().setPixmap(pixmap)
        self.window.update_status("Image copied to clipboard")

    def toggle_fullscreen_by_id(self, id: str):
        """
        Maximize dialog to screen edges using geometry (toggle).
        This avoids platform issues with WindowFullScreen on dialogs.
        """
        dialog = self.window.ui.dialog.get(id)
        if not dialog:
            return

        try:
            # restore if already maximized by geometry
            if getattr(dialog, "_edge_max", False):
                dialog.showNormal()  # ensure normal state before applying geometry
                normal = getattr(dialog, "_edge_normal_geom", None)
                if normal is not None:
                    dialog.setGeometry(normal)
                dialog._edge_max = False
                return

            # store current geometry to allow restoring later
            dialog._edge_normal_geom = dialog.geometry()
            dialog.showNormal()  # leave any native maximize/fullscreen state

            # pick the screen under the dialog, fallback to primary
            screen = None
            try:
                if dialog.windowHandle() is not None:
                    screen = dialog.windowHandle().screen()
                if screen is None:
                    screen = QtGui.QGuiApplication.screenAt(dialog.frameGeometry().center())
            except Exception:
                screen = None
            if screen is None:
                screen = QtGui.QGuiApplication.primaryScreen()

            available = screen.availableGeometry()
            dialog.setGeometry(available)
            dialog._edge_max = True
        except Exception as e:
            # fallback to native maximize if anything goes wrong
            try:
                if dialog.isMaximized():
                    dialog.showNormal()
                else:
                    dialog.showMaximized()
            except Exception:
                # last resort: ignore
                self.window.core.debug.log(e)

    # =========================
    # Helpers for directory navigation
    # =========================

    def _image_exts(self) -> Tuple[str, ...]:
        """Return supported image extensions."""
        return ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp')

    def _list_images_in_dir(self, path: str) -> List[str]:
        """
        Return sorted list of image paths in the directory of given image.
        """
        try:
            base_dir = os.path.dirname(path)
            if not os.path.isdir(base_dir):
                return []
            exts = self._image_exts()
            files = []
            for name in os.listdir(base_dir):
                full = os.path.join(base_dir, name)
                if os.path.isfile(full) and name.lower().endswith(exts):
                    files.append(full)
            files.sort(key=lambda s: s.lower())
            return files
        except Exception as e:
            self.window.core.debug.log(e)
            return []

    def _get_neighbors(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get previous and next image paths with wrap-around.
        If there is only one image in directory returns (None, None).
        """
        files = self._list_images_in_dir(path)
        if len(files) <= 1:
            return None, None
        try:
            idx = files.index(path)
        except ValueError:
            low = [p.lower() for p in files]
            try:
                idx = low.index(path.lower())
            except ValueError:
                return None, None

        n = len(files)
        prev_idx = (idx - 1) % n
        next_idx = (idx + 1) % n
        return files[prev_idx], files[next_idx]

    def _has_multiple_in_dir(self, path: Optional[str]) -> bool:
        """Check if directory of path has more than one image."""
        if not path:
            return False
        return len(self._list_images_in_dir(path)) > 1

    def _update_toolbar_actions_state(self, id: str):
        """
        Enable/disable toolbar actions based on current state.
        - Prev/Next enabled only if there are at least 2 images in directory.
        - Copy/OpenDir/SaveAs enabled only if image path is set.
        """
        dialog = self.window.ui.dialog.get(id)
        if not dialog:
            return
        has_img = bool(getattr(dialog, 'path', None))
        has_multi = self._has_multiple_in_dir(dialog.path) if has_img else False

        actions = getattr(dialog, 'actions', {})
        prev_act = actions.get('tb_prev')
        next_act = actions.get('tb_next')
        open_dir_act = actions.get('tb_open_dir')
        save_as_act = actions.get('tb_save_as')
        copy_act = actions.get('tb_copy')
        fullscreen_act = actions.get('tb_fullscreen')

        if prev_act:
            prev_act.setEnabled(has_multi)
        if next_act:
            next_act.setEnabled(has_multi)

        if open_dir_act:
            open_dir_act.setEnabled(has_img)
        if save_as_act:
            save_as_act.setEnabled(has_img)
        if copy_act:
            copy_act.setEnabled(has_img)
        if fullscreen_act:
            fullscreen_act.setEnabled(True)

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["image.viewer"] = QAction(
            QIcon(":/icons/image.svg"),
            trans("menu.tools.image.viewer"),
            self.window,
            checkable=False,
        )
        actions["image.viewer"].triggered.connect(
            lambda: self.open_preview()
        )
        return actions

    def get_instance(
            self,
            type_id: str,
            dialog_id: Optional[str] = None
    ) -> Optional[BaseDialog]:
        """
        Spawn and return dialog instance

        :param type_id: dialog instance type ID
        :param dialog_id: dialog instance ID
        :return dialog instance
        """
        if type_id == "image_viewer":
            return self.spawner.setup(dialog_id)

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.image.viewer': 'menu.tools.image.viewer',
            }
        }