#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QAction, QIcon, QCursor
from PySide6.QtWidgets import QMenu


from pygpt_net.utils import trans


class Menus:
    """Files menus for one explorer frontend."""

    def __init__(self, explorer):
        self.explorer = explorer

    def index_all(self, menu: QMenu) -> bool:
        """Add available indexes to an Index all menu and return whether any were added."""
        explorer = self.explorer
        idx_list = list(explorer.window.core.config.get('llama.idx.list') or [])
        if explorer.window.core.idx.project.get_current_group_id() is not None:
            idx_list.insert(0, {
                'id': explorer.window.core.idx.project.VIRTUAL_ID,
                'name': trans('idx.current_project'),
            })
        for idx in idx_list:
            idx_id = idx['id']
            name = idx['name'] if explorer.window.core.idx.project.is_virtual(idx_id) \
                else f"{idx['name']} ({idx_id})"
            action = menu.addAction(f"IDX: {name}")
            action.triggered.connect(
                lambda checked=False, id=idx_id: explorer.window.controller.idx.indexer.index_all_files(id)
            )
        return bool(idx_list)

    def clear_index(self, menu: QMenu) -> bool:
        """Add configured indexes to a Clear index menu and return whether any were added."""
        explorer = self.explorer
        idx_list = list(explorer.window.core.config.get('llama.idx.list') or [])
        for idx in idx_list:
            idx_id = idx['id']
            name = f"{idx['name']} ({idx_id})"
            action = menu.addAction(f"IDX: {name}")
            action.triggered.connect(
                lambda checked=False, id=idx_id: explorer.window.controller.idx.indexer.clear(id)
            )
        return bool(idx_list)

    def index_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        explorer = self.explorer
        menu = QMenu(explorer)
        self.index_all(menu)
        menu.exec(parent.mapToGlobal(pos))

    def clear_menu(self, parent, pos):
        """
        Clear btn context menu

        :param parent: parent widget
        :param pos: mouse position
        """
        explorer = self.explorer
        menu = QMenu(explorer)
        self.clear_index(menu)
        menu.exec(parent.mapToGlobal(pos))

    def context(self, position):
        """
        Open context menu

        :param position: mouse position
        """
        explorer = self.explorer
        paths = explorer.selected_paths()
        if paths:
            first_path = paths[0]
            multiple = len(paths) > 1
            target_multi = paths if multiple else first_path
            actions = {}
            preview_actions = []
            use_actions = []

            can_preview = False
            try:
                can_preview = explorer.window.core.filesystem.actions.has_preview(target_multi)
            except Exception:
                try:
                    can_preview = explorer.window.core.filesystem.actions.has_preview(first_path)
                except Exception:
                    can_preview = False

            if can_preview:
                try:
                    preview_actions = explorer.window.core.filesystem.actions.get_preview(explorer, target_multi)
                except Exception:
                    try:
                        preview_actions = explorer.window.core.filesystem.actions.get_preview(explorer, first_path)
                    except Exception:
                        preview_actions = []

            parent = explorer.parent_for_selection(paths)

            actions['open'] = QAction(explorer._icons['open'], trans('action.open'), explorer)
            actions['open'].triggered.connect(lambda: explorer.tool.paths.open(target_multi))

            actions['open_dir'] = QAction(explorer._icons['open_dir'], trans('action.open_dir'), explorer)
            actions['open_dir'].triggered.connect(lambda: explorer.tool.paths.reveal(target_multi, True))

            actions['download'] = QAction(explorer._icons['download'], trans('action.download'), explorer)
            actions['download'].triggered.connect(lambda: explorer.tool.transfers.download(target_multi))

            actions['rename'] = QAction(explorer._icons['rename'], trans('action.rename'), explorer)
            actions['rename'].triggered.connect(lambda: explorer.tool.operations.rename(target_multi))

            actions['duplicate'] = QAction(explorer._icons['duplicate'], trans('action.duplicate'), explorer)
            actions['duplicate'].triggered.connect(lambda: explorer.tool.operations.duplicate(target_multi, ""))

            actions['touch'] = QAction(explorer._icons['touch'], trans('action.touch'), explorer)
            actions['touch'].triggered.connect(lambda: explorer.tool.operations.touch(parent))

            actions['mkdir'] = QAction(explorer._icons['mkdir'], trans('action.mkdir'), explorer)
            actions['mkdir'].triggered.connect(lambda: explorer.tool.operations.prompt_directory(parent))

            actions['refresh'] = QAction(explorer._icons['refresh'], trans('action.refresh'), explorer)
            actions['refresh'].triggered.connect(lambda: explorer.tool.refresh())

            actions['upload'] = QAction(explorer._icons['upload'], trans('action.upload'), explorer)
            actions['upload'].triggered.connect(lambda: explorer.tool.transfers.upload(parent))

            actions['delete'] = QAction(explorer._icons['delete'], trans('action.delete'), explorer)
            actions['delete'].triggered.connect(lambda: explorer.tool.operations.delete(target_multi))

            actions['copy'] = QAction(explorer._icons['copy'], trans('action.copy'), explorer)
            actions['copy'].triggered.connect(explorer.clipboard.copy)
            actions['cut'] = QAction(explorer._icons['cut'], trans('action.cut'), explorer)
            actions['cut'].triggered.connect(explorer.clipboard.cut)
            actions['paste'] = QAction(explorer._icons['paste'], trans('action.paste'), explorer)
            actions['paste'].triggered.connect(lambda: explorer.clipboard.paste(parent))
            actions['paste'].setEnabled(explorer.clipboard.can_paste())

            # Pack / Unpack availability
            try:
                can_unpack_all = all(
                    os.path.isfile(p) and explorer.window.core.filesystem.packer.can_unpack(p)
                    for p in paths
                )
            except Exception:
                can_unpack_all = False

            # Build menu
            menu = QMenu(explorer)
            if preview_actions:
                for action in preview_actions:
                    menu.addAction(action)
            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])

            use_menu = QMenu(trans('action.use'), explorer)

            # Keep the direct AI action first in the Use submenu.
            actions['use_read_cmd'] = QAction(explorer._icons['read'], trans('action.use.read_cmd'), explorer)
            actions['use_read_cmd'].triggered.connect(
                lambda: explorer.tool.chat.mention(target_multi)
            )
            use_menu.addAction(actions['use_read_cmd'])

            files_only = all(os.path.isfile(p) for p in paths)
            if files_only:
                actions['use_attachment'] = QAction(explorer._icons['attachment'], trans('action.use.attachment'), explorer)
                actions['use_attachment'].triggered.connect(
                    lambda: explorer.tool.chat.attach(target_multi)
                )
                use_menu.addAction(actions['use_attachment'])

            if explorer.window.core.filesystem.actions.has_use(first_path):
                use_actions = explorer.window.core.filesystem.actions.get_use(explorer, first_path)

            if use_actions:
                for action in use_actions:
                    use_menu.addAction(action)

            actions['use_copy_work_path'] = QAction(explorer._icons['copy'], trans('action.use.copy_work_path'), explorer)
            actions['use_copy_work_path'].triggered.connect(
                lambda: explorer.tool.chat.copy_relative_path(target_multi)
            )

            actions['use_copy_sys_path'] = QAction(explorer._icons['copy'], trans('action.use.copy_sys_path'), explorer)
            actions['use_copy_sys_path'].triggered.connect(
                lambda: explorer.tool.chat.copy_path(target_multi)
            )

            use_menu.addAction(actions['use_copy_work_path'])
            use_menu.addAction(actions['use_copy_sys_path'])
            menu.addMenu(use_menu)

            allowed_any = any(explorer.window.core.idx.indexing.is_allowed(p) for p in paths)
            if allowed_any:
                idx_menu = QMenu(trans('action.idx'), explorer)
                idx_list = list(explorer.window.core.config.get('llama.idx.list') or [])
                if explorer.window.core.idx.project.get_current_group_id() is not None:
                    idx_list.insert(0, {'id': explorer.window.core.idx.project.VIRTUAL_ID, 'name': trans('idx.current_project')})
                # Resolve current per-path state once.  The lazy status cache is
                # also used by the Indexed column, so the menu and column stay
                # consistent without hydrating the whole idx_file table.
                path_status = {p: explorer.model.get_index_status(p) for p in paths}

                if len(idx_list) > 0:
                    for idx in idx_list:
                        id = idx['id']
                        physical_id = explorer.window.core.idx.resolve_idx(id)

                        # Hide a target from the Index section when every selected
                        # path is already present in it.  The same target is then
                        # exposed only in the Remove from index section below.
                        if physical_id is not None:
                            already_indexed = True
                            for p in paths:
                                status = path_status[p]
                                ids = set(status.get('global_indexes', []))
                                ids.update(status.get('project_indexes', []))
                                if physical_id not in ids:
                                    already_indexed = False
                                    break
                            if already_indexed:
                                continue

                        name = idx['name'] if explorer.window.core.idx.project.is_virtual(id) \
                            else f"{idx['name']} ({id})"
                        action = QAction(explorer._icons['db'], f"IDX: {name}", explorer)
                        action.triggered.connect(
                            lambda checked=False, id=id, target=target_multi:
                                explorer.window.controller.idx.indexer.index_file(target, id, show_loader=True)
                        )
                        idx_menu.addAction(action)

                remove_idx_set = set()
                for p in paths:
                    status = path_status[p]
                    if status.get('indexed'):
                        for ix in status.get('global_indexes', []):
                            remove_idx_set.add(ix)
                        for ix in status.get('project_indexes', []):
                            remove_idx_set.add(ix)

                if len(remove_idx_set) > 0:
                    idx_menu.addSeparator()
                    current_project_idx = explorer.window.core.idx.get_current_project_idx(virtual=False)
                    for ix in sorted(remove_idx_set):
                        label = trans('idx.current_project') if ix == current_project_idx else ix
                        action = QAction(explorer._icons['delete'], trans("action.idx.remove") + ": " + label, explorer)
                        action.triggered.connect(
                            lambda checked=False, ix=ix, target=target_multi: explorer.window.controller.idx.indexer.index_file_remove(target, ix, show_loader=True)
                        )
                        idx_menu.addAction(action)

                menu.addMenu(idx_menu)

            menu.addSeparator()
            menu.addAction(actions['copy'])
            menu.addAction(actions['cut'])
            menu.addAction(actions['paste'])
            menu.addSeparator()

            # Pack submenu (available for any selection)
            pack_menu = QMenu(trans("action.pack"), explorer)
            a_zip = QAction(explorer._icons['pack'], "ZIP (.zip)", explorer)
            a_zip.triggered.connect(lambda: explorer.archives.pack(target_multi, 'zip'))
            a_tgz = QAction(explorer._icons['pack'], "Tar GZip (.tar.gz)", explorer)
            a_tgz.triggered.connect(lambda: explorer.archives.pack(target_multi, 'tar.gz'))
            pack_menu.addAction(a_zip)
            pack_menu.addAction(a_tgz)
            menu.addMenu(pack_menu)

            # Unpack (only when all selected are supported archives)
            if can_unpack_all:
                a_unpack = QAction(explorer._icons['unpack'], trans("action.unpack"), explorer)
                a_unpack.triggered.connect(lambda: explorer.archives.unpack(target_multi))
                menu.addAction(a_unpack)

            menu.addSeparator()
            menu.addAction(actions['refresh'])
            menu.addAction(actions['touch'])
            menu.addAction(actions['mkdir'])
            menu.addSeparator()
            menu.addAction(actions['upload'])
            menu.addAction(actions['download'])
            menu.addSeparator()
            menu.addAction(actions['rename'])
            menu.addAction(actions['duplicate'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())
        else:
            actions = {}

            actions['touch'] = QAction(explorer._icons['touch'], trans('action.touch'), explorer)
            actions['touch'].triggered.connect(
                lambda: explorer.tool.operations.touch(explorer.directory),
            )

            actions['open_dir'] = QAction(explorer._icons['open_dir'], trans('action.open_dir'), explorer)
            actions['open_dir'].triggered.connect(
                lambda: explorer.tool.paths.reveal(explorer.directory, True),
            )

            actions['mkdir'] = QAction(explorer._icons['mkdir'], trans('action.mkdir'), explorer)
            actions['mkdir'].triggered.connect(
                lambda: explorer.tool.operations.prompt_directory(explorer.directory),
            )

            actions['upload'] = QAction(explorer._icons['upload'], trans('action.upload'), explorer)
            actions['upload'].triggered.connect(
                lambda: explorer.tool.transfers.upload(),
            )

            actions['paste'] = QAction(explorer._icons['paste'], trans('action.paste'), explorer)
            actions['paste'].triggered.connect(lambda: explorer.clipboard.paste(explorer.directory))
            actions['paste'].setEnabled(explorer.clipboard.can_paste())

            menu = QMenu(explorer)
            menu.addAction(actions['touch'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['mkdir'])
            menu.addAction(actions['upload'])
            menu.addAction(actions['paste'])
            menu.exec(QCursor.pos())

    def header(self, position):
        explorer = self.explorer
        menu = QMenu(explorer.header)
        menu.addAction(trans('files.tree.collapse_all'), explorer.tree_search.collapse_all)
        menu.addAction(trans('files.tree.expand_all'), explorer.tree_search.expand_all)
        menu.exec(explorer.header.mapToGlobal(position))
        menu.deleteLater()

