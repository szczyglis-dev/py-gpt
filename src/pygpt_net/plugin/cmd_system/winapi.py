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

import platform
import ctypes
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple

# Guard for non-Windows platforms: provide stubs that fail at call-time
if platform.system() != "Windows":
    class WinAPI:
        def __init__(self): raise RuntimeError("Windows only")
    class InputSender:
        def __init__(self): raise RuntimeError("Windows only")
else:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    gdi32 = ctypes.windll.gdi32

    # Constants
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    LWA_ALPHA = 0x00000002

    SW_HIDE = 0
    SW_SHOWNORMAL = 1
    SW_SHOWMINIMIZED = 2
    SW_SHOWMAXIMIZED = 3
    SW_RESTORE = 9

    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    HWND_TOP = 0
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2

    WM_CLOSE = 0x0010
    SMTO_BLOCK = 0x0001
    SMTO_ABORTIFHUNG = 0x0002
    SEND_TIMEOUT = 2000

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    # Input constants
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1

    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040

    # VK map
    VK = {
        "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12, "WIN": 0x5B,
        "ENTER": 0x0D, "ESC": 0x1B, "TAB": 0x09, "SPACE": 0x20, "BACKSPACE": 0x08, "DELETE": 0x2E,
        "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
        "HOME": 0x24, "END": 0x23, "PGUP": 0x21, "PGDN": 0x22,
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75,
        "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
        "F13": 0x7C, "F14": 0x7D, "F15": 0x7E, "F16": 0x7F, "F17": 0x80, "F18": 0x81,
        "F19": 0x82, "F20": 0x83, "F21": 0x84, "F22": 0x85, "F23": 0x86, "F24": 0x87,
    }

    # Structures
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", wintypes.ULONG_PTR),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", wintypes.ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class INPUT_union(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("union", INPUT_union)]

    # Function prototypes (partial)
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    # Helpers for Get/SetWindowLongPtr
    try:
        GetWindowLongPtrW = user32.GetWindowLongPtrW
        SetWindowLongPtrW = user32.SetWindowLongPtrW
        GetWindowLongPtrW.restype = ctypes.c_longlong
        GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
        SetWindowLongPtrW.restype = ctypes.c_longlong
        SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_longlong)
        _use_long_ptr = True
    except AttributeError:
        GetWindowLongW = user32.GetWindowLongW
        SetWindowLongW = user32.SetWindowLongW
        GetWindowLongW.restype = ctypes.c_long
        GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        SetWindowLongW.restype = ctypes.c_long
        SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        _use_long_ptr = False

    def _get_window_text(hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(wintypes.HWND(hwnd), buf, 512)
        return buf.value or ""

    def _get_class_name(hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(wintypes.HWND(hwnd), buf, 256)
        return buf.value or ""

    def _get_pid_exe(hwnd: int) -> Tuple[int, Optional[str]]:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid))
        exe_path = None
        access = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        hProcess = kernel32.OpenProcess(access, False, pid.value)
        if hProcess:
            try:
                buf_len = wintypes.DWORD(4096)
                buf = ctypes.create_unicode_buffer(4096)
                QueryFullProcessImageNameW = getattr(kernel32, "QueryFullProcessImageNameW", None)
                if QueryFullProcessImageNameW:
                    if QueryFullProcessImageNameW(hProcess, 0, buf, ctypes.byref(buf_len)):
                        exe_path = buf.value
                if not exe_path:
                    GetModuleFileNameExW = getattr(psapi, "GetModuleFileNameExW", None)
                    if GetModuleFileNameExW:
                        if GetModuleFileNameExW(hProcess, 0, buf, 4096):
                            exe_path = buf.value
            finally:
                kernel32.CloseHandle(hProcess)
        return pid.value, exe_path

    def _get_rect(hwnd: int) -> Dict:
        rect = wintypes.RECT()
        user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        return {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom,
                "width": width, "height": height}

    def _is_visible(hwnd: int) -> bool:
        return bool(user32.IsWindowVisible(wintypes.HWND(hwnd)))

    def _is_minimized(hwnd: int) -> bool:
        return bool(user32.IsIconic(wintypes.HWND(hwnd)))

    class WinAPI:
        """Thin ctypes wrapper around common WinAPI tasks"""

        def enum_windows(self, visible_only: bool = True) -> List[Dict]:
            items: List[Dict] = []

            @EnumWindowsProc
            def callback(hWnd, lParam):
                try:
                    if visible_only and not _is_visible(hWnd):
                        return True
                    title = _get_window_text(hWnd)
                    cls = _get_class_name(hWnd)
                    pid, exe = _get_pid_exe(hWnd)
                    rect = _get_rect(hWnd)
                    minimized = _is_minimized(hWnd)
                    items.append({
                        "hwnd": int(hWnd),
                        "title": title,
                        "class_name": cls,
                        "pid": pid,
                        "exe": exe or "",
                        "rect": rect,
                        "is_visible": _is_visible(hWnd),
                        "is_minimized": minimized,
                    })
                except Exception:
                    return True
                return True

            user32.EnumWindows(callback, 0)
            return items

        def enum_child_windows(self, parent_hwnd: int) -> List[Dict]:
            items: List[Dict] = []

            @EnumChildProc
            def callback(hChild, lParam):
                try:
                    title = _get_window_text(hChild)
                    cls = _get_class_name(hChild)
                    pid, exe = _get_pid_exe(hChild)
                    rect = _get_rect(hChild)
                    items.append({
                        "hwnd": int(hChild),
                        "title": title,
                        "class_name": cls,
                        "pid": pid,
                        "exe": exe or "",
                        "rect": rect,
                        "is_visible": _is_visible(hChild),
                        "is_minimized": _is_minimized(hChild),
                    })
                except Exception:
                    return True
                return True

            user32.EnumChildWindows(wintypes.HWND(parent_hwnd), callback, 0)
            return items

        def is_window(self, hwnd: int) -> bool:
            return bool(user32.IsWindow(wintypes.HWND(hwnd)))

        def get_window_info(self, hwnd: int) -> Dict:
            return {
                "hwnd": int(hwnd),
                "title": _get_window_text(hwnd),
                "class_name": _get_class_name(hwnd),
                "pid": _get_pid_exe(hwnd)[0],
                "exe": _get_pid_exe(hwnd)[1] or "",
                "rect": _get_rect(hwnd),
                "is_visible": _is_visible(hwnd),
                "is_minimized": _is_minimized(hwnd),
            }

        def bring_to_foreground(self, hwnd: int) -> Tuple[bool, str]:
            if _is_minimized(hwnd):
                user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)
            if user32.SetForegroundWindow(wintypes.HWND(hwnd)):
                return True, "SetForegroundWindow succeeded."
            fg = user32.GetForegroundWindow()
            if fg:
                target_tid = user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), None)
                fg_tid = user32.GetWindowThreadProcessId(wintypes.HWND(fg), None)
                cur_tid = kernel32.GetCurrentThreadId()
                user32.AttachThreadInput(fg_tid, cur_tid, True)
                user32.AttachThreadInput(target_tid, cur_tid, True)
                user32.BringWindowToTop(wintypes.HWND(hwnd))
                ok = user32.SetForegroundWindow(wintypes.HWND(hwnd))
                user32.AttachThreadInput(fg_tid, cur_tid, False)
                user32.AttachThreadInput(target_tid, cur_tid, False)
                if ok:
                    return True, "Foreground set via AttachThreadInput."
            return False, "Could not bring window to foreground (OS prevented focus change)."

        def move_resize(self, hwnd: int,
                        x: Optional[int], y: Optional[int],
                        width: Optional[int], height: Optional[int]) -> Tuple[bool, str]:
            rect = _get_rect(hwnd)
            new_x = rect["left"] if x is None else int(x)
            new_y = rect["top"] if y is None else int(y)
            new_w = rect["width"] if width is None else max(1, int(width))
            new_h = rect["height"] if height is None else max(1, int(height))
            ok = user32.SetWindowPos(wintypes.HWND(hwnd), HWND_TOP, new_x, new_y, new_w, new_h, 0)
            return (ok != 0), f"Moved to ({new_x},{new_y}) size ({new_w}x{new_h})."

        def show_window(self, hwnd: int, state: str) -> Tuple[bool, str]:
            m = {
                "minimize": SW_SHOWMINIMIZED,
                "maximize": SW_SHOWMAXIMIZED,
                "restore": SW_RESTORE,
                "show": SW_SHOWNORMAL,
                "hide": SW_HIDE,
            }
            if state not in m:
                return False, f"Invalid state: {state}"
            ok = user32.ShowWindow(wintypes.HWND(hwnd), m[state])
            return (ok != 0), f"ShowWindow {state}"

        def close_window(self, hwnd: int) -> Tuple[bool, str]:
            res = user32.SendMessageTimeoutW(
                wintypes.HWND(hwnd), WM_CLOSE, 0, 0,
                SMTO_BLOCK | SMTO_ABORTIFHUNG, SEND_TIMEOUT, None
            )
            return (res != 0), "WM_CLOSE sent."

        def set_topmost(self, hwnd: int, topmost: bool) -> Tuple[bool, str]:
            flag = HWND_TOPMOST if topmost else HWND_NOTOPMOST
            ok = user32.SetWindowPos(wintypes.HWND(hwnd), flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
            return (ok != 0), ("Topmost set" if topmost else "Topmost cleared")

        def _get_exstyle(self, hwnd: int) -> int:
            if '_use_long_ptr' in globals() and _use_long_ptr:
                return int(GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE))
            return int(GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE))

        def _set_exstyle(self, hwnd: int, val: int) -> int:
            if '_use_long_ptr' in globals() and _use_long_ptr:
                return int(SetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE, val))
            return int(SetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE, val))

        def set_opacity(self, hwnd: int, alpha: int) -> Tuple[bool, str]:
            ex = self._get_exstyle(hwnd)
            if (ex & WS_EX_LAYERED) == 0:
                self._set_exstyle(hwnd, ex | WS_EX_LAYERED)
            ok = user32.SetLayeredWindowAttributes(wintypes.HWND(hwnd), 0, wintypes.BYTE(alpha), LWA_ALPHA)
            return (ok != 0), f"Opacity set to alpha={alpha}"

        def get_foreground_window(self) -> Optional[int]:
            h = user32.GetForegroundWindow()
            return int(h) if h else None

        def get_window_rect(self, hwnd: int) -> Dict:
            return _get_rect(hwnd)

        def get_cursor_pos(self) -> Tuple[int, int]:
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y

        def set_cursor_pos(self, x: int, y: int) -> bool:
            return bool(user32.SetCursorPos(int(x), int(y)))

    class InputSender:
        """Keyboard and mouse input sender using SendInput"""

        def __init__(self):
            pass

        def _send_input(self, inputs):
            n = len(inputs)
            arr = (INPUT * n)(*inputs)
            sent = user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))
            return sent == n

        # ---- Keyboard ----
        def send_unicode_text(self, text: str, per_char_delay_ms: int = 2):
            for ch in text:
                code = ord(ch)
                down = INPUT(type=INPUT_KEYBOARD, union=INPUT_union(ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)))
                up = INPUT(type=INPUT_KEYBOARD, union=INPUT_union(ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                self._send_input([down, up])
                if per_char_delay_ms > 0:
                    kernel32.Sleep(per_char_delay_ms)

        def send_keys(self, keys: List[str], hold_ms: int = 50, gap_ms: int = 30) -> Tuple[bool, str]:
            tokens = [str(k).strip().upper() for k in keys if str(k).strip()]
            if not tokens:
                return False, "No key tokens."
            modifiers = [t for t in tokens if t in ("CTRL", "ALT", "SHIFT", "WIN")]
            normals = [t for t in tokens if t not in modifiers]

            def mk_down(vk):
                return INPUT(type=INPUT_KEYBOARD, union=INPUT_union(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))

            def mk_up(vk):
                return INPUT(type=INPUT_KEYBOARD, union=INPUT_union(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))

            # Press modifiers
            for mod in modifiers:
                vk = VK.get(mod)
                if vk is None: return False, f"Unsupported modifier: {mod}"
                if not self._send_input([mk_down(vk)]):
                    return False, f"Failed to press modifier: {mod}"

            # Tap normals
            for key in normals:
                vk = None
                if key in VK:
                    vk = VK[key]
                elif len(key) == 1:
                    c = key.upper()
                    if 'A' <= c <= 'Z' or '0' <= c <= '9':
                        vk = ord(c)
                if vk is None:
                    # Release modifiers before exit
                    for mod in reversed(modifiers):
                        vkmod = VK.get(mod)
                        if vkmod is not None:
                            self._send_input([mk_up(vkmod)])
                    return False, f"Unsupported key token: {key}"

                if not self._send_input([mk_down(vk), mk_up(vk)]):
                    # Release modifiers before exit
                    for mod in reversed(modifiers):
                        vkmod = VK.get(mod)
                        if vkmod is not None:
                            self._send_input([mk_up(vkmod)])
                    return False, f"Failed to tap: {key}"
                if gap_ms > 0:
                    kernel32.Sleep(gap_ms)

            # Release modifiers
            for mod in reversed(modifiers):
                vk = VK.get(mod)
                if vk is not None:
                    self._send_input([mk_up(vk)])

            return True, "Keys sent."

        # ---- Mouse ----
        def _mouse_event(self, flags: int):
            mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0)
            inp = INPUT(type=INPUT_MOUSE, union=INPUT_union(mi=mi))
            return self._send_input([inp])

        def move_cursor(self, x: int, y: int) -> bool:
            return bool(user32.SetCursorPos(int(x), int(y)))

        def click_at(self, x: int, y: int, button: str = "left", double: bool = False) -> Tuple[bool, str]:
            self.move_cursor(x, y)
            btn = (button or "left").lower()
            if btn == "left":
                down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
            elif btn == "right":
                down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
            elif btn == "middle":
                down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
            else:
                return False, f"Unsupported button: {button}"
            if not self._mouse_event(down) or not self._mouse_event(up):
                return False, "Mouse click failed."
            if double:
                kernel32.Sleep(80)
                if not self._mouse_event(down) or not self._mouse_event(up):
                    return False, "Mouse double-click failed."
            return True, "Click sent."

        def drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, steps: int = 20, step_delay_ms: int = 10) -> Tuple[bool, str]:
            self.move_cursor(x1, y1)
            if not self._mouse_event(MOUSEEVENTF_LEFTDOWN):
                return False, "Mouse down failed."
            try:
                if steps < 1:
                    steps = 1
                dx = (x2 - x1) / float(steps)
                dy = (y2 - y1) / float(steps)
                cx, cy = float(x1), float(y1)
                for i in range(steps):
                    cx += dx
                    cy += dy
                    self.move_cursor(int(cx), int(cy))
                    if step_delay_ms > 0:
                        kernel32.Sleep(step_delay_ms)
            finally:
                self._mouse_event(MOUSEEVENTF_LEFTUP)
            return True, "Drag-and-drop completed."