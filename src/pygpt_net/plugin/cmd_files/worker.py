#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 00:30:00                  #
# ================================================== #

import fnmatch
import mimetypes
import os.path
import shutil
import ssl
import stat
import tarfile
import zipfile

from typing import Tuple, List, Dict
from urllib.request import Request, urlopen
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):
                        self.check_security(item)

                        # save file
                        if item["cmd"] == "save_file":
                            response = self.cmd_save_file(item)

                        # append to file
                        elif item["cmd"] == "append_file":
                            response = self.cmd_append_file(item)

                        # read file
                        elif item["cmd"] == "read_file":
                            response = self.cmd_read_file(item)

                        # query file
                        elif item["cmd"] == "query_file":
                            response = self.cmd_query_file(item)

                        # delete file
                        elif item["cmd"] == "delete_file":
                            response = self.cmd_delete_file(item)

                        # list files
                        elif item["cmd"] == "list_dir":
                            response = self.cmd_list_dir(item)

                        # tree
                        elif item["cmd"] == "tree":
                            response = self.cmd_tree(item)

                        # mkdir
                        elif item["cmd"] == "mkdir":
                            response = self.cmd_mkdir(item)

                        # rmdir
                        elif item["cmd"] == "rmdir":
                            response = self.cmd_rmdir(item)

                        # download
                        elif item["cmd"] == "download_file":
                            response = self.cmd_download_file(item)

                        # copy file
                        elif item["cmd"] == "copy_file":
                            response = self.cmd_copy_file(item)

                        # copy dir
                        elif item["cmd"] == "copy_dir":
                            response = self.cmd_copy_dir(item)

                        # move
                        elif item["cmd"] == "move":
                            response = self.cmd_move(item)

                        # pack archive
                        elif item["cmd"] == "pack_archive":
                            response = self.cmd_pack_archive(item)

                        # unpack archive
                        elif item["cmd"] == "unpack_archive":
                            response = self.cmd_unpack_archive(item)

                        # is dir
                        elif item["cmd"] == "is_dir":
                            response = self.cmd_is_dir(item)

                        # is file
                        elif item["cmd"] == "is_file":
                            response = self.cmd_is_file(item)

                        # file exists
                        elif item["cmd"] == "file_exists":
                            response = self.cmd_file_exists(item)

                        # file size
                        elif item["cmd"] == "file_size":
                            response = self.cmd_file_size(item)

                        # file info
                        elif item["cmd"] == "file_info":
                            response = self.cmd_file_info(item)

                        # cwd
                        elif item["cmd"] == "cwd":
                            response = self.cmd_cwd(item)

                        # get file as attachment
                        elif item["cmd"] == "send_file":
                            response = self.cmd_send_file(item)

                        # index file or directory
                        elif item["cmd"] == "file_index":
                            response = self.cmd_file_index(item)

                        # find file or directory
                        elif item["cmd"] == "find":
                            response = self.cmd_find(item)

                        # store response
                        if response:
                            responses.append(response)

                except Exception as e:
                    responses.append(
                        self.make_response(
                            item,
                            self.throw_error(e)
                        )
                    )

            if len(responses) > 0:
                self.reply_more(responses) # send response

            if self.msg is not None:
                self.status(self.msg)

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def check_security(self, item: dict):
        """Validate host filesystem access requested by a Files I/O command."""
        cmd = item.get("cmd")
        params = item.get("params") or {}

        def paths(name):
            value = params.get(name)
            if value is None:
                return []
            if isinstance(value, (list, tuple, set)):
                return [self.prepare_path(v) for v in value if v not in (None, "")]
            return [self.prepare_path(value)] if value != "" else []

        read_path = {
            "read_file", "query_file", "list_dir", "tree", "is_dir", "is_file",
            "file_exists", "file_size", "file_info", "send_file", "file_index", "find",
        }
        write_path = {"save_file", "append_file", "delete_file", "mkdir", "rmdir"}

        if cmd in read_path:
            requested = paths("path")
            if not requested and cmd in {"list_dir", "tree", "find"}:
                requested = [self.plugin.window.core.config.get_user_dir("data")]
            for path in requested:
                self.security_read(path)
        elif cmd in write_path:
            for path in paths("path"):
                self.security_write(path)
        elif cmd in {"copy_file", "copy_dir"}:
            for path in paths("src"):
                self.security_read(path)
            for path in paths("dst"):
                self.security_write(path)
        elif cmd == "move":
            for path in paths("src"):
                self.security_read(path)
                self.security_write(path)
            for path in paths("dst"):
                self.security_write(path)
        elif cmd == "pack_archive":
            for path in paths("src"):
                self.security_read(path)
            for path in paths("dst"):
                self.security_write(path)
        elif cmd == "unpack_archive":
            for path in paths("src"):
                self.security_read(path)
            for path in paths("dst"):
                self.security_write(path)
        elif cmd == "download_file":
            src = params.get("src")
            if src and not str(src).lower().startswith(("http://", "https://")):
                self.security_read(self.prepare_path(src))
            for path in paths("dst"):
                self.security_write(path)

    def cmd_save_file(self, item: dict) -> dict:
        """
        Save file

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"] or "data" not in item["params"]:
                return self.make_response(item, "Path or data not provided")
            path = self.prepare_path(item["params"]['path'])
            data = item["params"]['data']
            self.msg = "Saving file: {}".format(path)
            self.log(self.msg)
            with open(path, 'w', encoding="utf-8") as file:
                file.write(data)
                result = "OK"
                self.log("File saved: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_append_file(self, item: dict) -> dict:
        """
        Append to file

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"] or "data" not in item["params"]:
                return self.make_response(item, "Path or data not provided")
            path = self.prepare_path(item["params"]['path'])
            data = item["params"]['data']
            self.msg = "Appending file: {}".format(path)
            self.log(self.msg)
            with open(path, 'a', encoding="utf-8") as file:
                file.write(data)
                result = "OK"
                self.log("File appended: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_read_file(self, item: dict) -> dict:
        """
        Read file

        :param item: item with parameters
        :return: response item
        """
        context_result = ""
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            self.msg = "Reading file: {}".format(item["params"]['path'])
            self.log(self.msg)
            path = item["params"]['path']
            paths = []
            if isinstance(path, list):
                paths = path
            elif isinstance(path, str):
                paths = [path]
            data, context = self.read_files(paths)
            context_str = None
            if context:
                context_str = "\n\n".join(context)
            result = data
            if context_str:
                context_result = context_str
        except Exception as e:
            result = self.throw_error(e)
        extra = self.prepare_extra(item, context_result)
        return self.make_response(item, result, extra=extra)

    def cmd_query_file(self, item: dict) -> dict:
        """
        Query file

        :param item: item with parameters
        :return: response item
        """
        result = None
        context = None
        query = None
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Reading path: {}".format(path)
            self.log(self.msg)
            if "query" in item["params"] and item["params"]["query"]:
                query = item["params"]["query"]

            # check if file exists
            if os.path.exists(path):
                if query is not None:
                    # query file using temp index (created on the fly)
                    self.log("Querying file: {}".format(path))
                    # get tmp query model
                    model = self.plugin.window.core.models.from_defaults()
                    tmp_model = self.plugin.get_option_value("model_tmp_query")
                    if self.plugin.window.core.models.has(tmp_model):
                        model = self.plugin.window.core.models.get(tmp_model)
                    answer = self.plugin.window.core.idx.chat.query_file(
                        ctx=self.ctx,
                        path=path,
                        query=query,
                        model=model,
                    )
                    self.log("Response from temporary in-memory index: {}".format(answer))
                    if answer:
                        result = answer
                        context = "From: " + os.path.basename(path) + ":\n--------------------------------\n" + answer

                # + auto-index file to main index using Llama-index
                if self.plugin.get_option_value("auto_index"):
                    for idx_name in self.plugin.get_index_names():
                        self.plugin.window.core.idx.index_files(
                            idx_name,
                            path,
                        )
            else:
                result = "File not found"
                self.log("File not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, context)
        return self.make_response(item, result, extra=extra)

    def cmd_delete_file(self,item: dict) -> dict:
        """
        Delete file

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Deleting file: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                os.remove(path)
                result = "OK"
                self.log("File deleted: {}".format(path))
            else:
                result = "File not found"
                self.log("File not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_list_dir(self, item: dict) -> dict:
        """
        List directory

        :param item: item with parameters
        :return: response item
        """
        try:
            path = self.plugin.window.core.config.get_user_dir('data')
            if "path" in item["params"]:
                path = self.prepare_path(item["params"]['path'])
            self.msg = "Listing directory: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                files = os.listdir(path)
                result = files
                self.log("Files listed: {}".format(path))
                self.log("Result: {}".format(files))
            else:
                result = "Directory not found"
                self.log("Directory not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_tree(self, item: dict) -> dict:
        """
        Get directory tree

        :param item: item with parameters
        :return: response item
        """
        context = None
        try:
            path = self.plugin.window.core.config.get_user_dir('data')
            if "path" in item["params"]:
                path = self.prepare_path(item["params"]['path'])
            self.msg = "Listing directory: {}".format(path)
            self.log(self.msg)
            tree_str = ""
            tree = {}
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    dirs.sort()
                    files.sort()
                    level = root.replace(path, '').count(os.sep)
                    indent = ' ' * 4 * (level)
                    tree_str += '{}{}/\n'.format(indent, os.path.basename(root))
                    sub_indent = ' ' * 4 * (level + 1)
                    files = sorted(files)
                    for f in files:
                        tree_str += '{}{}\n'.format(sub_indent, f)
                    tree[os.path.basename(root)] = files
                result = tree
                context = path + "\n--------------------------------\n" + tree_str
                self.log("Directory tree: {}".format(path))
                self.log("Result: {}".format(tree_str))
            else:
                result = "Directory not found"
                self.log("Directory not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_mkdir(self, item: dict) -> dict:
        """
        Make directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Creating directory: {}".format(path)
            self.log(self.msg)
            if not os.path.exists(path):
                os.makedirs(path)
                result = "OK"
                self.log("Directory created: {}".format(path))
            else:
                result = "Directory already exists"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_rmdir(self, item: dict) -> dict:
        """
        Remove directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Deleting directory: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                shutil.rmtree(path)
                result = "OK"
                self.log("Directory deleted: {}".format(path))
            else:
                result = "Directory not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_download_file(self, item: dict) -> dict:
        """
        Download file

        :param item: item with parameters
        :return: response item
        """
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")
            dst = self.prepare_path(item["params"]['dst'])
            self.msg = "Downloading file: {} into {}".format(item["params"]['src'], dst)
            self.log(self.msg)
            size = 0
            # Check if src is URL
            if item["params"]['src'].startswith("http"):
                src = item["params"]['src']
                # Download file from URL
                try:
                    req = Request(
                        url=src,
                        headers={'User-Agent': 'Mozilla/5.0'},
                    )
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    with urlopen(
                            req,
                            context=context,
                            timeout=5) as response, \
                            open(dst, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                        size = os.path.getsize(dst)
                except Exception as e:
                    return self.make_response(item, f"Failed to download file: {e}")
            else:
                # Handle local file paths
                src = os.path.join(
                    self.plugin.window.core.config.get_user_dir('data'),
                    item["params"]['src'],
                )
                # Copy local file
                with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                    shutil.copyfileobj(in_file, out_file)
                size = os.path.getsize(dst)

            # handle result
            result = {
                "result": "OK",
                "size_bytes": size,
                "size_human": self.get_human_readable_size(size),
            }
            self.log("File downloaded: {} into {}".format(src, dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_copy_file(self, item: dict) -> dict:
        """
        Copy file

        :param item: item with parameters
        :return: response item
        """
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")
            src = self.prepare_path(item["params"]['src'])
            dst = self.prepare_path(item["params"]['dst'])
            self.msg = "Copying file: {} into {}".format(src, dst)
            self.log(self.msg)
            shutil.copyfile(src, dst)
            result = "OK"
            self.log("File copied: {} into {}".format(src, dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_copy_dir(self, item: dict) -> dict:
        """
        Copy directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")
            src = self.prepare_path(item["params"]['src'])
            dst = self.prepare_path(item["params"]['dst'])
            self.msg = "Copying directory: {} into {}".format(src, dst)
            self.log(self.msg)
            shutil.copytree(src, dst)
            result = "OK"
            self.log("Directory copied: {} into {}".format(src, dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_move(self, item: dict) -> dict:
        """
        Move file or directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")
            src = self.prepare_path(item["params"]['src'])
            dst = self.prepare_path(item["params"]['dst'])
            self.msg = "Moving: {} into {}".format(src, dst)
            self.log(self.msg)
            shutil.move(src, dst)
            result = "OK"
            self.log("Moved: {} into {}".format(src, dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    @staticmethod
    def _archive_format(path: str) -> tuple[str, str]:
        """Return archive family and write mode from file extension."""
        lower = str(path).lower()
        if lower.endswith(".zip"):
            return "zip", "w"
        if lower.endswith((".tar.gz", ".tgz")):
            return "tar", "w:gz"
        if lower.endswith((".tar.bz2", ".tbz2", ".tbz")):
            return "tar", "w:bz2"
        if lower.endswith((".tar.xz", ".txz")):
            return "tar", "w:xz"
        if lower.endswith(".tar"):
            return "tar", "w"
        raise ValueError(
            "Unsupported archive format. Use .zip, .tar, .tar.gz/.tgz, "
            ".tar.bz2/.tbz2 or .tar.xz/.txz"
        )

    @staticmethod
    def _archive_member_target(dst: str, member_name: str) -> str:
        """Resolve an archive member path and reject path traversal."""
        name = str(member_name or "").replace("\\", "/")
        if not name or name.startswith("/"):
            raise ValueError(f"Unsafe archive member path: {member_name}")
        drive, _ = os.path.splitdrive(name)
        if drive:
            raise ValueError(f"Unsafe archive member path: {member_name}")

        target = os.path.realpath(os.path.abspath(os.path.join(dst, *name.split("/"))))
        base = os.path.realpath(os.path.abspath(dst))
        try:
            if os.path.commonpath([base, target]) != base:
                raise ValueError(f"Unsafe archive member path: {member_name}")
        except ValueError:
            raise ValueError(f"Unsafe archive member path: {member_name}")
        return target

    @staticmethod
    def _archive_sources(value) -> list:
        """Normalize archive source parameter to a non-empty list."""
        if isinstance(value, (list, tuple, set)):
            sources = [str(v) for v in value if v not in (None, "")]
        elif value not in (None, ""):
            sources = [str(value)]
        else:
            sources = []
        if not sources:
            raise ValueError("Source path(s) not provided")
        return sources

    def _zip_add_path(self, archive: zipfile.ZipFile, src: str) -> int:
        """Add a file or directory recursively to a ZIP archive."""
        count = 0
        src = os.path.abspath(src)
        arc_root = os.path.basename(os.path.normpath(src)) or "data"

        if os.path.isdir(src):
            for root, dirs, files in os.walk(src, followlinks=False):
                rel_root = os.path.relpath(root, src)
                arc_dir = arc_root if rel_root == "." else os.path.join(arc_root, rel_root)
                archive.write(root, arc_dir)
                count += 1

                # Do not follow directory symlinks; store only normal directory trees.
                dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(root, name))]
                for filename in files:
                    path = os.path.join(root, filename)
                    if os.path.islink(path):
                        continue
                    archive.write(path, os.path.join(arc_dir, filename))
                    count += 1
        else:
            if os.path.islink(src):
                raise ValueError(f"Refusing to archive symbolic link: {src}")
            archive.write(src, arc_root)
            count += 1
        return count

    def cmd_pack_archive(self, item: dict) -> dict:
        """Pack files or directories into ZIP/TAR archive."""
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")

            src_values = self._archive_sources(item["params"]["src"])
            sources = [self.prepare_path(value) for value in src_values]
            dst = self.prepare_path(item["params"]["dst"])
            kind, mode = self._archive_format(dst)

            dst_real = os.path.realpath(os.path.abspath(dst))
            for src in sources:
                if not os.path.exists(src):
                    return self.make_response(item, f"File or directory not found: {src}")
                src_real = os.path.realpath(os.path.abspath(src))
                if src_real == dst_real:
                    raise ValueError("Destination archive must be different from source path")
                if os.path.isdir(src_real):
                    try:
                        if os.path.commonpath([src_real, dst_real]) == src_real:
                            raise ValueError("Destination archive cannot be created inside a source directory")
                    except ValueError as exc:
                        if str(exc).startswith("Destination archive"):
                            raise

            self.msg = "Packing archive: {}".format(dst)
            self.log(self.msg)
            count = 0

            if kind == "zip":
                with zipfile.ZipFile(dst, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for src in sources:
                        count += self._zip_add_path(archive, src)
            else:
                with tarfile.open(dst, mode) as archive:
                    for src in sources:
                        if os.path.islink(src):
                            raise ValueError(f"Refusing to archive symbolic link: {src}")
                        arcname = os.path.basename(os.path.normpath(src)) or "data"
                        archive.add(src, arcname=arcname, recursive=True, filter=self._tar_pack_filter)
                    count = len(archive.getmembers())

            size = os.path.getsize(dst)
            result = {
                "result": "OK",
                "archive": dst,
                "format": kind,
                "sources": len(sources),
                "entries": count,
                "size_bytes": size,
                "size_human": self.get_human_readable_size(size),
            }
            self.log("Archive created: {}".format(dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    @staticmethod
    def _tar_pack_filter(member: tarfile.TarInfo):
        """Skip symlinks, hard links and special files while creating TAR archives."""
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            return None
        return member

    def _unpack_zip(self, src: str, dst: str) -> int:
        """Safely extract ZIP archive without path traversal or symlinks."""
        count = 0
        with zipfile.ZipFile(src, "r") as archive:
            for info in archive.infolist():
                target = self._archive_member_target(dst, info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise ValueError(f"Refusing to extract symbolic link: {info.filename}")

                if info.is_dir() or info.filename.endswith("/"):
                    os.makedirs(target, exist_ok=True)
                    continue

                os.makedirs(os.path.dirname(target), exist_ok=True)
                with archive.open(info, "r") as source, open(target, "wb") as output:
                    shutil.copyfileobj(source, output)
                if mode & 0o777:
                    try:
                        os.chmod(target, mode & 0o777)
                    except OSError:
                        pass
                count += 1
        return count

    def _unpack_tar(self, src: str, dst: str) -> int:
        """Safely extract TAR archive without path traversal, links or special files."""
        count = 0
        with tarfile.open(src, "r:*") as archive:
            for member in archive.getmembers():
                target = self._archive_member_target(dst, member.name)
                if member.issym() or member.islnk():
                    raise ValueError(f"Refusing to extract archive link: {member.name}")
                if member.isdev() or member.isfifo():
                    raise ValueError(f"Refusing to extract special archive member: {member.name}")

                if member.isdir():
                    # Keep destination directories writable while extracting child entries.
                    os.makedirs(target, exist_ok=True)
                    continue
                if not member.isfile():
                    continue

                source = archive.extractfile(member)
                if source is None:
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with source, open(target, "wb") as output:
                    shutil.copyfileobj(source, output)
                try:
                    os.chmod(target, member.mode & 0o777)
                except OSError:
                    pass
                count += 1
        return count

    def cmd_unpack_archive(self, item: dict) -> dict:
        """Unpack ZIP/TAR archive into a directory."""
        try:
            if "src" not in item["params"] or "dst" not in item["params"]:
                return self.make_response(item, "Source or destination not provided")

            src = self.prepare_path(item["params"]["src"])
            dst = self.prepare_path(item["params"]["dst"])
            if not os.path.isfile(src):
                return self.make_response(item, "Archive file not found")

            self.msg = "Unpacking archive: {} into {}".format(src, dst)
            self.log(self.msg)
            os.makedirs(dst, exist_ok=True)

            if zipfile.is_zipfile(src):
                kind = "zip"
                count = self._unpack_zip(src, dst)
            elif tarfile.is_tarfile(src):
                kind = "tar"
                count = self._unpack_tar(src, dst)
            else:
                raise ValueError("Unsupported or invalid archive. Expected ZIP or TAR archive")

            result = {
                "result": "OK",
                "archive": src,
                "destination": dst,
                "format": kind,
                "files_extracted": count,
            }
            self.log("Archive unpacked: {} into {}".format(src, dst))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_is_dir(self, item: dict) -> dict:
        """
        Check if directory exists

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Checking if directory exists: {}".format(path)
            self.log(self.msg)
            if os.path.isdir(path):
                result = "OK"
                self.log("Directory exists: {}".format(path))
            else:
                result = "Directory not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_is_file(self, item: dict) -> dict:
        """
        Check if file exists

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Checking if file exists: {}".format(path)
            self.log(self.msg)
            if os.path.isfile(path):
                result = "OK"
                self.log("File exists: {}".format(path))
            else:
                result = "File not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_file_exists(self, item: dict) -> dict:
        """
        Check if file exists

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Checking if path exists: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                result = "OK"
                self.log("Path exists: {}".format(path))
            else:
                result = "File or directory not found"
                self.log("Path not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_file_size(self, item: dict) -> dict:
        """
        Check file size

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Checking file size: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                size = os.path.getsize(path)
                result = {
                    'size_bytes': size,
                    'size_human': self.plugin.human_readable_size(size),
                }
                self.log("File size: {}".format(size))
            else:
                result = "File not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_file_info(self, item: dict) -> dict:
        """
        Check file info

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Checking file info: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                size = os.path.getsize(path)
                result = {
                    "size": size,
                    "size_human": self.get_human_readable_size(size),
                    'mime_type': mimetypes.guess_type(path)[0] or 'application/octet-stream',
                    "last_access": os.path.getatime(path),
                    "last_modification": os.path.getmtime(path),
                    "creation_time": os.path.getctime(path),
                    "is_dir": os.path.isdir(path),
                    "is_file": os.path.isfile(path),
                    "is_link": os.path.islink(path),
                    "is_mount": os.path.ismount(path),
                    'stat': os.stat(path),
                }
                self.log("File info: {}".format(result))
            else:
                result = "File not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_cwd(self, item: dict) -> dict:
        """
        Get current working directory

        :param item: item with parameters
        :return: response item
        """
        try:
            self.msg = "Getting CWD: {}".format(self.plugin.window.core.config.get_user_dir('data'))
            self.log(self.msg)
            result = self.plugin.window.core.config.get_user_dir('data')
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_send_file(self, item: dict) -> dict:
        """
        Get/send file as attachment

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                return self.make_response(item, "Path not provided")
            path = self.prepare_path(item["params"]['path'])
            self.msg = "Adding attachment: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                # make attachment
                mode = self.plugin.window.core.config.get('mode')
                title = os.path.basename(path)
                self.plugin.window.core.attachments.new(mode, title, path, False)
                self.plugin.window.core.attachments.save()
                self.plugin.window.controller.attachment.update()
                result = "Sending attachment: {}".format(title)
                self.log("Added attachment: {}".format(path))
            else:
                result = "File not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_file_index(self, item: dict) -> dict:
        """
        Index file or directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "path" not in item["params"]:
                self.log("Path not provided")
                return self.make_response(item, "Path not provided")

            # prepare path
            p = item["params"]['path']
            if isinstance(p, list):
                p = p[0]  # take first path if list provided
            path = self.prepare_path(p)
            self.msg = "Indexing path: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                index_names = self.plugin.get_index_names()
                indexed = {}
                errors = []
                num_indexed = 0
                for idx_name in index_names:
                    # index path using Llama-index
                    files, idx_errors = self.plugin.window.core.idx.index_files(
                        idx_name,
                        path,
                    )
                    num_indexed += len(files)
                    indexed[idx_name] = {
                        'num_indexed': len(files),
                        'errors': idx_errors,
                    }
                    errors.extend([f"{idx_name}: {error}" for error in idx_errors])
                result = {
                    'num_indexed': num_indexed,
                    'index_name': ','.join(index_names),
                    'index_names': index_names,
                    'indexes': indexed,
                    'errors': errors,
                    'path': path,
                }
            else:
                result = "File or directory not found"
                self.log("File not found: {}".format(path))
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_find(self, item: dict) -> dict:
        """
        Search for files in directory

        :param item: item with parameters
        :return: response item
        """
        try:
            if "pattern" not in item["params"]:
                return self.make_response(item, "Search pattern not provided")
            recursive = True
            path = self.plugin.window.core.config.get_user_dir('data')
            pattern = item["params"]['pattern']
            if "path" in item["params"]:
                path = self.prepare_path(item["params"]['path'])
            if "recursive" in item["params"]:
                recursive = item["params"]['recursive']
            self.msg = "Searching in directory: {}".format(path)
            self.log(self.msg)
            if os.path.exists(path):
                files = self.find_files(path, pattern, recursive)
                result = files
                self.log("Result: {}".format(files))
            else:
                result = "Directory not found"
                self.log("{}: {}".format(result, path))
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def find_files(self, directory: str, pattern: str, recursive: bool = True) -> list:
        """
        Find files in directory

        :param directory: search directory
        :param pattern: search pattern
        :param recursive: search recursively
        :return: list of files
        """
        matches = []
        if recursive:
            for root, dirs, files in os.walk(directory):
                for filename in fnmatch.filter(files, pattern):
                    matches.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                if fnmatch.fnmatch(filename, pattern):
                    matches.append(os.path.join(directory, filename))
        return matches

    def get_human_readable_size(self, size: int, decimal_places: int = 2):
        """
        Return a human-readable file size.

        :param size: file size in bytes
        :param decimal_places: number of decimal places
        :return: human-readable file size
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                break
            size /= 1024.0
        return f"{size:.{decimal_places}f} {unit}"

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute

        :param path: path to check
        :return: True if absolute
        """
        return os.path.isabs(path)

    def prepare_path(self, path: str) -> str:
        """
        Prepare path

        :param path: path to prepare
        :return: prepared path
        """
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir('data')

        if self.is_absolute_path(path):
            return path
        else:
            return os.path.join(
                self.plugin.window.core.config.get_user_dir('data'),
                path,
            )

    def read_files(self, paths: List[str]) -> Tuple[List[Dict], List[str]]:
        """
        Read files from directory

        :param paths: list of paths
        :return: response data(s), context(s)
        """
        data = []
        context = []
        for path in paths:
            path = self.prepare_path(path)
            if os.path.exists(path):
                # + auto-index file using Llama-index
                if self.plugin.get_option_value("auto_index") \
                        or self.plugin.get_option_value("only_index"):
                    index_names = self.plugin.get_index_names()
                    indexed = {}
                    errors = []
                    num_indexed = 0
                    for idx_name in index_names:
                        files, idx_errors = self.plugin.window.core.idx.index_files(
                            idx_name,
                            path,
                        )
                        num_indexed += len(files)
                        indexed[idx_name] = {
                            'num_indexed': len(files),
                            'errors': idx_errors,
                        }
                        errors.extend([f"{idx_name}: {error}" for error in idx_errors])
                    # if only index, return response and continue
                    if self.plugin.get_option_value("only_index"):
                        data.append({
                            'num_indexed': num_indexed,
                            'index_name': ','.join(index_names),
                            'index_names': index_names,
                            'indexes': indexed,
                            'errors': errors,
                            'path': path,
                        })
                        self.log("File read (index only): {}".format(path))
                        return data, context

                # read file as text
                content = self.plugin.read_as_text(
                    path,
                    use_loaders=self.plugin.get_option_value("use_loaders"),
                )
                data.append({
                    "path": os.path.basename(path),
                    "content": content,
                })
                context.append(os.path.basename(path) + ":\n--------------------------------\n" + content)
                self.log("File read: {}".format(path))
            else:
                self.log("File not found: {}".format(path))
                data.append({
                    "path": os.path.basename(path),
                    "content": "File not found",
                })

        return data, context

    def prepare_extra(self, item: dict, context: str) -> dict:
        """
        Prepare extra data for response

        :param item: command item
        :param context: context data
        :return: extra data
        """
        # disabled in v2.6.31
        # reason: do not duplicate context in chat
        return {}
        cmd = item["cmd"]
        extra = {
            'plugin': "cmd_files",
            'cmd': cmd,
            'code': {
                'output': {
                    'lang': "bash",
                    'content': str(context),
                }
            }
        }
        # extra["context"] = str(context)
        return extra

    def get_extra_data(self) -> dict:
        """
        Return extra data for response

        :return: extra data
        """
        return {
            "post_update": ["file_explorer"],  # update file explorer after processing
        }
