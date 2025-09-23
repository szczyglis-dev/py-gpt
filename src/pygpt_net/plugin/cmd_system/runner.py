#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.23 07:00:00                  #
# ================================================== #

import os.path
import re
import subprocess
import docker
import json
import os
import platform
import time
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QRect

from pygpt_net.item.ctx import CtxItem

from .winapi import WinAPI, InputSender


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self.signals = None
        self._winapi = None  # lazy

    def attach_signals(self, signals):
        """
        Attach signals

        :param signals: signals
        """
        self.signals = signals

    # -------------------------------
    # Common helpers / logging
    # -------------------------------
    def handle_result(self, stdout, stderr):
        """
        Handle result from subprocess

        :param stdout: stdout
        :param stderr: stderr
        :return: result
        """
        result = None
        if stdout:
            result = stdout.decode("utf-8", errors="replace")
            self.log("STDOUT: {}".format(result))
        if stderr:
            err = stderr.decode("utf-8", errors="replace")
            # Prefer stderr if non-empty
            result = err if err else result
            self.log("STDERR: {}".format(err))
        if result is None:
            result = "No result (STDOUT/STDERR empty)"
            self.log(result)
        return result

    def handle_result_docker(self, response) -> str:
        """
        Handle result from docker container

        :param response: response
        :return: result
        """
        result = None
        if response:
            try:
                result = response.decode('utf-8', errors="replace")
            except Exception:
                result = str(response)
        self.log(
            "Result: {}".format(result),
            sandbox=True,
        )
        return result

    def is_sandbox(self) -> bool:
        """
        Check if sandbox is enabled

        :return: True if sandbox is enabled
        """
        return self.plugin.get_option_value('sandbox_docker')

    def get_docker(self) -> docker.client.DockerClient:
        """
        Get docker client

        :return: docker client instance
        """
        return docker.from_env()

    def get_volumes(self) -> dict:
        """
        Get docker volumes

        :return: docker volumes
        """
        path = self.plugin.window.core.config.get_user_dir('data')
        mapping = {}
        mapping[path] = {
            "bind": "/data",
            "mode": "rw",
        }
        return mapping

    def run_docker(self, cmd: str) -> bytes or None:
        """
        Run docker container with command and return response

        :param cmd: command to run
        :return: response
        """
        client = self.get_docker()
        mapping = self.get_volumes()
        try:
            response = self.plugin.docker.execute(cmd)
        except Exception as e:
            response = str(e).encode("utf-8")
        return response

    def sys_exec_host(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command on host
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg)
        self.log("Running command: {}".format(item["params"]['command']))
        try:
            process = subprocess.Popen(
                item["params"]['command'],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
        except Exception as e:
            self.error(e)
            stdout = None
            stderr = str(e).encode("utf-8")
        result = self.handle_result(stdout, stderr)
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def sys_exec_sandbox(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command in sandbox (docker)
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg, sandbox=True)
        self.log(
            "Running command: {}".format(item["params"]['command']),
            sandbox=True,
        )
        response = self.run_docker(item["params"]['command'])
        result = self.handle_result_docker(response)
        return {
            "request": request,
            "result": str(result),
            "context": "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(result),
        }

    def parse_result(self, result):
        """
        Parse result

        :param result: result
        :return: parsed result
        """
        if result is None:
            return ""
        img_ext = ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]
        s = str(result).strip()
        if any(s.lower().endswith('.' + ext) for ext in img_ext):
            path = self.prepare_path(s.replace("file://", ""), on_host=True)
            if os.path.isfile(path):
                return "![Image](file://{})".format(path)
        return str(result)

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute
        """
        return os.path.isabs(path)

    def prepare_path(self, path: str, on_host: bool = True) -> str:
        """
        Prepare path

        :param path: path to prepare
        :param on_host: is on host
        :return: prepared path
        """
        if not path:
            return path
        if self.is_absolute_path(path):
            return path
        else:
            if not self.is_sandbox() or on_host:
                return os.path.join(
                    self.plugin.window.core.config.get_user_dir('data'),
                    path,
                )
            else:
                return path

    def error(self, err: any):
        """
        Log error message
        """
        if self.signals is not None:
            self.signals.error.emit(err)

    def status(self, msg: str):
        """
        Send status message
        """
        if self.signals is not None:
            self.signals.status.emit(msg)

    def debug(self, msg: any):
        """
        Log debug message
        """
        if self.signals is not None:
            self.signals.debug.emit(msg)

    def log(self, msg, sandbox: bool = False):
        """
        Log message to console
        """
        prefix = ''
        if sandbox:
            prefix += '[DOCKER]'
        full_msg = prefix + ' ' + str(msg)

        if self.signals is not None:
            self.signals.log.emit(full_msg)

    # -------------------------------
    # WinAPI helpers
    # -------------------------------
    def _ensure_windows(self):
        """Ensure the platform is Windows and WinAPI enabled."""
        if platform.system() != "Windows":
            raise RuntimeError("Windows API is available on Microsoft Windows only.")
        if not self.plugin.get_option_value("winapi_enabled"):
            raise RuntimeError("WinAPI is disabled in plugin options.")

    def _ensure_winapi(self) -> WinAPI:
        """Get or create WinAPI helper"""
        self._ensure_windows()
        if self._winapi is None:
            self._winapi = WinAPI()
        return self._winapi

    def _to_json(self, data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _resolve_window(self,
                        hwnd: Optional[int] = None,
                        title: Optional[str] = None,
                        exact: bool = False,
                        visible_only: bool = True,
                        class_name: Optional[str] = None,
                        exe: Optional[str] = None,
                        pid: Optional[int] = None) -> Tuple[Optional[int], Optional[List[Dict]], Optional[str]]:
        """
        Resolve a window handle by conditions. Returns (hwnd, candidates, error)
        """
        w = self._ensure_winapi()
        if hwnd:
            if w.is_window(hwnd):
                return hwnd, None, None
            return None, None, f"Window handle not valid: {hwnd}"

        items = w.enum_windows(visible_only=visible_only)
        def matches(item):
            ok = True
            if title:
                low = title.lower()
                ok = ok and ((item["title"] == title) if exact else (low in item["title"].lower()))
            if class_name:
                ok = ok and (item["class_name"].lower() == class_name.lower())
            if exe:
                ex = (item["exe"] or "")
                ok = ok and (os.path.basename(ex).lower() == os.path.basename(exe).lower())
            if pid is not None:
                ok = ok and (item["pid"] == int(pid))
            return ok

        matched = [it for it in items if matches(it)]
        if len(matched) == 0:
            return None, [], "No window matched."
        if len(matched) > 1:
            return None, matched, "Ambiguous: multiple windows matched."
        return matched[0]["hwnd"], None, None

    # -------------------------------
    # WinAPI: window listing / info
    # -------------------------------
    def win_list(self,
                 filter_title: Optional[str] = None,
                 visible_only: bool = True,
                 limit: Optional[int] = None) -> Dict:
        w = self._ensure_winapi()
        items = w.enum_windows(visible_only=visible_only)
        if filter_title:
            low = filter_title.lower()
            items = [x for x in items if low in x["title"].lower()]
        if limit and limit > 0:
            items = items[:limit]
        return {"result": self._to_json(items), "context": f"Found: {len(items)} windows"}

    def win_find(self,
                 title: Optional[str] = None,
                 class_name: Optional[str] = None,
                 exe: Optional[str] = None,
                 pid: Optional[int] = None,
                 exact: bool = False,
                 visible_only: bool = True) -> Dict:
        w = self._ensure_winapi()
        items = w.enum_windows(visible_only=visible_only)

        def matches(it):
            ok = True
            if title:
                low = title.lower()
                ok = ok and ((it["title"] == title) if exact else (low in it["title"].lower()))
            if class_name:
                ok = ok and (it["class_name"].lower() == class_name.lower())
            if exe:
                ex = (it["exe"] or "")
                ok = ok and (os.path.basename(ex).lower() == os.path.basename(exe).lower())
            if pid is not None:
                ok = ok and (it["pid"] == int(pid))
            return ok

        out = [it for it in items if matches(it)]
        return {"result": self._to_json(out), "context": f"Matches: {len(out)}"}

    def win_children(self, hwnd: int) -> Dict:
        w = self._ensure_winapi()
        if not hwnd:
            return {"result": "Missing hwnd", "context": "Param 'hwnd' is required."}
        kids = w.enum_child_windows(hwnd)
        return {"result": self._to_json(kids), "context": f"Children: {len(kids)}"}

    def win_foreground(self) -> Dict:
        w = self._ensure_winapi()
        hwnd = w.get_foreground_window()
        if not hwnd:
            return {"result": "None", "context": "No foreground window."}
        info = w.get_window_info(hwnd)
        return {"result": self._to_json(info), "context": f"Foreground HWND: {hwnd}"}

    def win_rect(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        r = w.get_window_rect(handle)
        return {"result": self._to_json(r), "context": f"Rect: {r}"}

    def win_get_state(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        info = w.get_window_info(handle)
        return {"result": self._to_json(info), "context": "Window state"}

    # -------------------------------
    # WinAPI: window control
    # -------------------------------
    def win_focus(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=True)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.bring_to_foreground(handle)
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_move_resize(self,
                        hwnd: Optional[int] = None,
                        title: Optional[str] = None,
                        exact: bool = False,
                        x: Optional[int] = None,
                        y: Optional[int] = None,
                        width: Optional[int] = None,
                        height: Optional[int] = None) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.move_resize(handle, x, y, width, height)
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_minimize(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.show_window(handle, state="minimize")
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_maximize(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.show_window(handle, state="maximize")
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_restore(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.show_window(handle, state="restore")
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_close(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.close_window(handle)
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_show(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.show_window(handle, state="show")
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_hide(self, hwnd: Optional[int] = None, title: Optional[str] = None, exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.show_window(handle, state="hide")
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_always_on_top(self,
                          topmost: bool,
                          hwnd: Optional[int] = None,
                          title: Optional[str] = None,
                          exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        if topmost is None:
            return {"result": "Missing 'topmost'", "context": "Param 'topmost' is required (true/false)."}
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        ok, msg = w.set_topmost(handle, bool(topmost))
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_set_opacity(self,
                        alpha: Optional[int] = None,
                        opacity: Optional[float] = None,
                        hwnd: Optional[int] = None,
                        title: Optional[str] = None,
                        exact: bool = False) -> Dict:
        w = self._ensure_winapi()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}
        # Normalize alpha
        if alpha is None:
            if opacity is None:
                return {"result": "Missing 'alpha' or 'opacity'", "context": "Provide alpha (0..255) or opacity (0..1)."}
            alpha = int(max(0, min(1.0, float(opacity))) * 255.0)
        else:
            alpha = int(max(0, min(255, int(alpha))))
        ok, msg = w.set_opacity(handle, alpha)
        return {"result": "OK" if ok else "FAILED", "context": msg}

    # -------------------------------
    # WinAPI: screenshots
    # -------------------------------
    def _save_pixmap(self, pix, path: str) -> Tuple[bool, str]:
        """Save QPixmap to disk, ensure dir."""
        abspath = self.prepare_path(path)
        try:
            os.makedirs(os.path.dirname(abspath), exist_ok=True)
        except Exception:
            # in case no directory part provided
            pass
        ok = pix.save(abspath, "PNG")
        return ok, abspath

    def win_screenshot(self,
                       hwnd: Optional[int] = None,
                       title: Optional[str] = None,
                       exact: bool = False,
                       path: Optional[str] = None) -> Dict:
        self._ensure_windows()
        handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
        if candidates is not None:
            return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
        if err:
            return {"result": err, "context": err}

        if not path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"win_screenshot_{handle}_{ts}.png"

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return {"result": "No screen", "context": "No QScreen available. Is Qt app running?"}

        pix = screen.grabWindow(int(handle))
        if pix.isNull():
            return {"result": "Failed", "context": "grabWindow returned null pixmap."}

        ok, abspath = self._save_pixmap(pix, path)
        if not ok:
            return {"result": "Failed", "context": f"Could not save screenshot to: {abspath}"}
        context = "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(abspath)
        return {"result": abspath, "context": context}

    def win_area_screenshot(self,
                            x: int, y: int, width: int, height: int,
                            hwnd: Optional[int] = None,
                            title: Optional[str] = None,
                            exact: bool = False,
                            relative: bool = False,
                            path: Optional[str] = None) -> Dict:
        self._ensure_windows()
        if any(v is None for v in [x, y, width, height]):
            return {"result": "Missing geometry", "context": "Params x,y,width,height are required."}

        x0, y0 = int(x), int(y)
        if relative and (hwnd or title):
            handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
            if candidates is not None:
                return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
            if err:
                return {"result": err, "context": err}
            rect = self._ensure_winapi().get_window_rect(handle)
            x0 += int(rect["left"])
            y0 += int(rect["top"])

        if not path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"win_area_{x0}_{y0}_{width}x{height}_{ts}.png"

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return {"result": "No screen", "context": "No QScreen available. Is Qt app running?"}

        pix = screen.grabWindow(0, x0, y0, int(width), int(height))
        if pix.isNull():
            return {"result": "Failed", "context": "grabWindow returned null pixmap."}

        ok, abspath = self._save_pixmap(pix, path)
        if not ok:
            return {"result": "Failed", "context": f"Could not save screenshot to: {abspath}"}
        context = "SYS OUTPUT:\n--------------------------------\n" + self.parse_result(abspath)
        return {"result": abspath, "context": context}

    # -------------------------------
    # WinAPI: clipboard / cursor / input / monitors
    # -------------------------------
    def win_clipboard_get(self) -> Dict:
        cb = QGuiApplication.clipboard()
        text = cb.text()
        return {"result": text, "context": "Clipboard text retrieved."}

    def win_clipboard_set(self, text: str) -> Dict:
        cb = QGuiApplication.clipboard()
        cb.setText(text or "")
        return {"result": "OK", "context": "Clipboard text set."}

    def win_cursor_get(self) -> Dict:
        w = self._ensure_winapi()
        x, y = w.get_cursor_pos()
        return {"result": self._to_json({"x": x, "y": y}), "context": f"Cursor: ({x}, {y})"}

    def win_cursor_set(self, x: int, y: int) -> Dict:
        w = self._ensure_winapi()
        ok = w.set_cursor_pos(x, y)
        return {"result": "OK" if ok else "FAILED", "context": f"Set cursor to ({x}, {y})"}

    def win_keys_text(self, text: str, per_char_delay_ms: Optional[int] = None) -> Dict:
        self._ensure_windows()
        if not text:
            return {"result": "No text", "context": "Param 'text' is required."}
        if per_char_delay_ms is None:
            per_char_delay_ms = int(self.plugin.get_option_value("win_keys_per_char_delay_ms"))
        sender = InputSender()
        sender.send_unicode_text(text, per_char_delay_ms=per_char_delay_ms)
        return {"result": "OK", "context": f"Typed {len(text)} characters."}

    def win_keys_send(self,
                      keys: List[str],
                      hold_ms: Optional[int] = None,
                      gap_ms: Optional[int] = None) -> Dict:
        self._ensure_windows()
        if not keys or not isinstance(keys, list):
            return {"result": "No keys", "context": "Param 'keys' must be a non-empty list of key tokens."}
        if hold_ms is None:
            hold_ms = int(self.plugin.get_option_value("win_keys_hold_ms"))
        if gap_ms is None:
            gap_ms = int(self.plugin.get_option_value("win_keys_gap_ms"))
        sender = InputSender()
        ok, msg = sender.send_keys(keys, hold_ms=hold_ms, gap_ms=gap_ms)
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_click(self,
                  x: Optional[int] = None,
                  y: Optional[int] = None,
                  button: str = "left",
                  double: bool = False,
                  hwnd: Optional[int] = None,
                  title: Optional[str] = None,
                  exact: bool = False,
                  relative: bool = False) -> Dict:
        self._ensure_windows()
        if x is None or y is None:
            return {"result": "Missing coords", "context": "Params 'x' and 'y' are required."}
        x0, y0 = int(x), int(y)
        if relative and (hwnd or title):
            handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
            if candidates is not None:
                return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
            if err:
                return {"result": err, "context": err}
            rect = self._ensure_winapi().get_window_rect(handle)
            x0 += int(rect["left"])
            y0 += int(rect["top"])
        sender = InputSender()
        ok, msg = sender.click_at(x0, y0, button=button, double=bool(double))
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_drag(self,
                 x1: int, y1: int, x2: int, y2: int,
                 hwnd: Optional[int] = None,
                 title: Optional[str] = None,
                 exact: bool = False,
                 relative: bool = False,
                 steps: int = 20,
                 hold_ms: Optional[int] = None) -> Dict:
        self._ensure_windows()
        if any(v is None for v in [x1, y1, x2, y2]):
            return {"result": "Missing coords", "context": "Params x1,y1,x2,y2 are required."}
        sx, sy, ex, ey = int(x1), int(y1), int(x2), int(y2)
        if relative and (hwnd or title):
            handle, candidates, err = self._resolve_window(hwnd, title, exact=exact, visible_only=False)
            if candidates is not None:
                return {"result": self._to_json(candidates), "context": "Multiple matches. Specify 'hwnd'."}
            if err:
                return {"result": err, "context": err}
            rect = self._ensure_winapi().get_window_rect(handle)
            offx, offy = int(rect["left"]), int(rect["top"])
            sx, sy, ex, ey = sx + offx, sy + offy, ex + offx, ey + offy
        if hold_ms is None:
            hold_ms = int(self.plugin.get_option_value("win_drag_step_delay_ms"))
        sender = InputSender()
        ok, msg = sender.drag_and_drop(sx, sy, ex, ey, steps=max(1, int(steps)), step_delay_ms=int(hold_ms))
        return {"result": "OK" if ok else "FAILED", "context": msg}

    def win_monitors(self) -> Dict:
        screens = QGuiApplication.screens()
        arr = []
        for i, s in enumerate(screens):
            g: QRect = s.geometry()
            arr.append({
                "index": i,
                "name": s.name(),
                "geometry": {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()},
                "dpi": s.logicalDotsPerInch(),
                "scale": s.devicePixelRatio(),
            })
        return {"result": self._to_json(arr), "context": f"Monitors: {len(arr)}"}