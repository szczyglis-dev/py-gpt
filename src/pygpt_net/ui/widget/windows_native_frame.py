#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.10.01 17:25:00                  #
# ================================================== #

"""Windows native frame bridge for the custom PyGPT window chrome.

Qt creates a normal HWND on Windows so its platform plugin retains native DWM
rendering. This bridge keeps the Win32 frame styles required by DWM, including
``WS_CAPTION`` and ``WS_THICKFRAME``, while ``WM_NCCALCSIZE`` expands the client
area over the entire native frame. The caption therefore exists only as a Win32
style contract for DWM shadow/Snap and has no visible title-bar area. On
non-Windows platforms this helper is an inert no-op.
"""

import sys


class WindowsNativeFrame:
    """Keep native Windows DWM frame semantics with fully custom chrome."""

    def __init__(self, window):
        self.window = window
        self.hwnd = 0
        self.is_active = False
        self._event_filter = None

    @staticmethod
    def is_supported() -> bool:
        return sys.platform.startswith("win")

    def setup(self) -> bool:
        """Enable the native custom-frame path. Returns ``False`` on failure."""
        if not self.is_supported():
            return False
        try:
            self._load_win32()
            self.hwnd = int(self.window.winId())
            if not self.hwnd:
                return False

            from PySide6.QtCore import QAbstractNativeEventFilter
            from PySide6.QtWidgets import QApplication

            bridge = self

            class FrameEventFilter(QAbstractNativeEventFilter):
                def nativeEventFilter(self, event_type, message):
                    result = bridge.native_event(message)
                    return result if result is not None else (False, 0)

            # Observe HWND messages directly, including messages that Qt does
            # not forward to QWidget.nativeEvent during window recreation.
            self._event_filter = FrameEventFilter()
            QApplication.instance().installNativeEventFilter(self._event_filter)
            self.is_active = True
            # Changing styles synchronously sends WM_NCCALCSIZE. The handler
            # must already be active to suppress the native caption.
            self._ensure_window_styles()
            self._apply_dwm_attributes()
            self._refresh_frame()
            return True
        except Exception as exc:
            self.is_active = False
            print(f"[Window] Native Windows frame unavailable: {exc}")
            return False

    def refresh(self):
        """Reapply native styles/DWM attributes after state or theme changes."""
        if not self.is_active:
            return
        try:
            hwnd = int(self.window.winId())
            if not hwnd:
                return
            self.hwnd = hwnd
            if not self._is_fullscreen():
                self._ensure_window_styles()
            self._apply_dwm_attributes()
            # Qt can restore non-client geometry without changing style bits.
            # Recalculate it even when the styles already match.
            self._refresh_frame()
        except Exception:
            pass

    def native_event(self, message):
        """Handle Win32 messages needed by the custom non-client frame.

        Returns ``(handled, result)`` or ``None`` when Qt should continue with
        its normal native-event processing.
        """
        if not self.is_active or not self.hwnd:
            return None
        try:
            msg = self.wintypes.MSG.from_address(int(message))
        except Exception:
            return None
        if int(msg.hWnd or 0) != self.hwnd:
            # Theme/platform changes may replace the HWND. Only adopt the
            # main window's current handle; never consume another window's events.
            current = int(self.window.effectiveWinId())
            if not current or int(msg.hWnd or 0) != current:
                return None
            self.hwnd = current

        if msg.message == self.WM_NCCALCSIZE:
            # WS_CAPTION is intentionally present so DWM keeps the native
            # shadow/frame. Returning 0 for NCCALCSIZE removes the complete
            # standard non-client area, so the caption itself is never shown.
            self._handle_nc_calc_size(msg.wParam, msg.lParam)
            return True, 0

        if msg.message == self.WM_NCHITTEST:
            hit = self._hit_test_resize_border(msg.lParam)
            if hit is not None:
                return True, hit
            # Everything except the outer resize border remains Qt client area,
            # including our custom menu/title bar and window buttons.
            return True, self.HTCLIENT

        if msg.message == self.WM_GETMINMAXINFO and not self._is_fullscreen():
            self._handle_get_min_max_info(msg.lParam)
            return True, 0

        if msg.message == self.WM_ACTIVATE:
            # DWM custom-frame guidance recommends extending the frame again
            # when activation/non-client rendering changes.
            self._apply_dwm_attributes()
            return None

        if msg.message in (self.WM_DWMCOMPOSITIONCHANGED, self.WM_THEMECHANGED):
            self.refresh()
            return None

        if msg.message == self.WM_STYLECHANGED and not self._is_fullscreen():
            # Qt may rewrite native styles during state transitions. Keep the
            # DWM contract deterministic: the native caption/frame styles stay
            # present, while WM_NCCALCSIZE continues to suppress their visible
            # non-client area. _ensure_window_styles() is idempotent, so the
            # WM_STYLECHANGED generated by our own write falls through without
            # another write.
            if self._ensure_window_styles():
                self._refresh_frame()
            return None

        return None

    def _hit_test_resize_border(self, l_param):
        """Return native HT* code for the outer resize border, if any."""
        if self._is_fullscreen() or self.user32.IsZoomed(self.hwnd):
            return None

        # WM_NCHITTEST packs signed screen coordinates into LPARAM.
        packed = int(l_param)
        x = self.ctypes.c_short(packed & 0xFFFF).value
        y = self.ctypes.c_short((packed >> 16) & 0xFFFF).value

        rect = self.wintypes.RECT()
        if not self.user32.GetWindowRect(self.hwnd, self.ctypes.byref(rect)):
            return None

        dpi = self._window_dpi()
        # Keep the hit area compact; Qt uses logical pixels while the native
        # message coordinates are physical pixels. 6 px at 96 DPI feels close
        # to the standard Windows resize affordance without eating our toolbar.
        margin = max(4, int(round(6 * (dpi / 96.0))))
        left = x < rect.left + margin
        right = x >= rect.right - margin
        top = y < rect.top + margin
        bottom = y >= rect.bottom - margin

        if top and left:
            return self.HTTOPLEFT
        if top and right:
            return self.HTTOPRIGHT
        if bottom and left:
            return self.HTBOTTOMLEFT
        if bottom and right:
            return self.HTBOTTOMRIGHT
        if left:
            return self.HTLEFT
        if right:
            return self.HTRIGHT
        if top:
            return self.HTTOP
        if bottom:
            return self.HTBOTTOM
        return None

    def _is_fullscreen(self) -> bool:
        try:
            return bool(self.window.isFullScreen())
        except Exception:
            return False

    def _handle_nc_calc_size(self, w_param, l_param):
        """Expand the Qt client area over the normal caption/frame.

        When maximized, clamp the client rect to the monitor work area so the
        custom frame never covers the taskbar.
        """
        if not l_param:
            return

        if w_param:
            params = self.ctypes.cast(
                l_param,
                self.ctypes.POINTER(self.NCCALCSIZE_PARAMS),
            ).contents
            rect = params.rgrc[0]
        else:
            rect = self.ctypes.cast(
                l_param,
                self.ctypes.POINTER(self.wintypes.RECT),
            ).contents

        if self.user32.IsZoomed(self.hwnd) and not self._is_fullscreen():
            work = self._monitor_work_rect()
            if work is not None:
                rect.left = work.left
                rect.top = work.top
                rect.right = work.right
                rect.bottom = work.bottom

    def _handle_get_min_max_info(self, l_param):
        if not l_param:
            return
        monitor = self.user32.MonitorFromWindow(
            self.hwnd,
            self.MONITOR_DEFAULTTONEAREST,
        )
        if not monitor:
            return

        info = self.MONITORINFO()
        info.cbSize = self.ctypes.sizeof(self.MONITORINFO)
        if not self.user32.GetMonitorInfoW(monitor, self.ctypes.byref(info)):
            return

        mmi = self.ctypes.cast(
            l_param,
            self.ctypes.POINTER(self.MINMAXINFO),
        ).contents
        work = info.rcWork
        monitor_rect = info.rcMonitor
        mmi.ptMaxPosition.x = work.left - monitor_rect.left
        mmi.ptMaxPosition.y = work.top - monitor_rect.top
        mmi.ptMaxSize.x = work.right - work.left
        mmi.ptMaxSize.y = work.bottom - work.top

        # Consuming WM_GETMINMAXINFO means Qt will not get another chance to
        # publish its minimum size to Win32. Mirror it here in physical pixels.
        dpi = self._window_dpi()
        scale = dpi / 96.0 if dpi > 0 else 1.0
        try:
            min_w = max(1, int(round(self.window.minimumWidth() * scale)))
            min_h = max(1, int(round(self.window.minimumHeight() * scale)))
            mmi.ptMinTrackSize.x = max(mmi.ptMinTrackSize.x, min_w)
            mmi.ptMinTrackSize.y = max(mmi.ptMinTrackSize.y, min_h)
        except Exception:
            pass

    def _window_dpi(self) -> int:
        get_dpi = getattr(self.user32, "GetDpiForWindow", None)
        if get_dpi is not None:
            try:
                return int(get_dpi(self.hwnd) or 0)
            except Exception:
                pass
        return 96

    def _monitor_work_rect(self):
        monitor = self.user32.MonitorFromWindow(
            self.hwnd,
            self.MONITOR_DEFAULTTONEAREST,
        )
        if not monitor:
            return None
        info = self.MONITORINFO()
        info.cbSize = self.ctypes.sizeof(self.MONITORINFO)
        if not self.user32.GetMonitorInfoW(monitor, self.ctypes.byref(info)):
            return None
        return info.rcWork

    def _apply_dwm_attributes(self):
        if self.dwmapi is None:
            return

        # Keep native non-client rendering enabled. The HWND carries the normal
        # caption/thick-frame contract required by DWM, but WM_NCCALCSIZE removes
        # the visible non-client area so only our Qt chrome is painted.
        policy = self.ctypes.c_int(self.DWMNCRP_ENABLED)
        self.dwmapi.DwmSetWindowAttribute(
            self.hwnd,
            self.DWMWA_NCRENDERING_POLICY,
            self.ctypes.byref(policy),
            self.ctypes.sizeof(policy),
        )

        # A one-pixel DWM extension is the documented custom-frame pattern and
        # keeps composition/shadow attached to the window on Windows 10/11.
        margins = self.MARGINS(1, 1, 1, 1)
        self.dwmapi.DwmExtendFrameIntoClientArea(
            self.hwnd,
            self.ctypes.byref(margins),
        )

        # Windows 11: request a native black 1px DWM border. Older Windows
        # versions simply reject/ignore this attribute.
        border_color = self.wintypes.DWORD(0x00000000)
        self.dwmapi.DwmSetWindowAttribute(
            self.hwnd,
            self.DWMWA_BORDER_COLOR,
            self.ctypes.byref(border_color),
            self.ctypes.sizeof(border_color),
        )

    def _refresh_frame(self):
        self.user32.SetWindowPos(
            self.hwnd,
            0,
            0,
            0,
            0,
            0,
            self.SWP_NOMOVE
            | self.SWP_NOSIZE
            | self.SWP_NOZORDER
            | self.SWP_NOOWNERZORDER
            | self.SWP_NOACTIVATE
            | self.SWP_FRAMECHANGED,
        )

    def _ensure_window_styles(self) -> bool:
        style = self._get_window_style(self.hwnd)
        # Win32/DWM needs a normal overlapped frame
        # contract for native shadow, Snap and resize semantics. WS_CAPTION is
        # therefore kept at the style level and hidden exclusively by handling
        # WM_NCCALCSIZE above.
        desired = (
            style
            | self.WS_CAPTION
            | self.WS_THICKFRAME
            | self.WS_SYSMENU
            | self.WS_MINIMIZEBOX
            | self.WS_MAXIMIZEBOX
        )
        if desired == style:
            return False
        self._set_window_style(self.hwnd, desired)
        return True

    def _get_window_style(self, hwnd):
        return int(self._get_window_long_ptr(hwnd, self.GWL_STYLE))

    def _set_window_style(self, hwnd, style):
        self._set_window_long_ptr(hwnd, self.GWL_STYLE, style)

    def _load_win32(self):
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        try:
            self.dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        except OSError:
            self.dwmapi = None

        self.GWL_STYLE = -16
        self.WS_CAPTION = 0x00C00000
        self.WS_THICKFRAME = 0x00040000
        self.WS_SYSMENU = 0x00080000
        self.WS_MINIMIZEBOX = 0x00020000
        self.WS_MAXIMIZEBOX = 0x00010000

        self.WM_ACTIVATE = 0x0006
        self.WM_NCCALCSIZE = 0x0083
        self.WM_NCHITTEST = 0x0084
        self.WM_GETMINMAXINFO = 0x0024
        self.WM_DWMCOMPOSITIONCHANGED = 0x031E
        self.WM_THEMECHANGED = 0x031A
        self.WM_STYLECHANGED = 0x007D

        self.HTCLIENT = 1
        self.HTLEFT = 10
        self.HTRIGHT = 11
        self.HTTOP = 12
        self.HTTOPLEFT = 13
        self.HTTOPRIGHT = 14
        self.HTBOTTOM = 15
        self.HTBOTTOMLEFT = 16
        self.HTBOTTOMRIGHT = 17

        self.MONITOR_DEFAULTTONEAREST = 2

        self.SWP_NOSIZE = 0x0001
        self.SWP_NOMOVE = 0x0002
        self.SWP_NOZORDER = 0x0004
        self.SWP_NOACTIVATE = 0x0010
        self.SWP_FRAMECHANGED = 0x0020
        self.SWP_NOOWNERZORDER = 0x0200

        self.DWMWA_NCRENDERING_POLICY = 2
        self.DWMNCRP_ENABLED = 2
        self.DWMWA_BORDER_COLOR = 34

        class NCCALCSIZE_PARAMS(ctypes.Structure):
            _fields_ = [
                ("rgrc", wintypes.RECT * 3),
                ("lppos", wintypes.LPVOID),
            ]

        class MINMAXINFO(ctypes.Structure):
            _fields_ = [
                ("ptReserved", wintypes.POINT),
                ("ptMaxSize", wintypes.POINT),
                ("ptMaxPosition", wintypes.POINT),
                ("ptMinTrackSize", wintypes.POINT),
                ("ptMaxTrackSize", wintypes.POINT),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]

        self.NCCALCSIZE_PARAMS = NCCALCSIZE_PARAMS
        self.MINMAXINFO = MINMAXINFO
        self.MONITORINFO = MONITORINFO
        self.MARGINS = MARGINS

        self.user32.IsZoomed.argtypes = [wintypes.HWND]
        self.user32.IsZoomed.restype = wintypes.BOOL
        self.user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user32.MonitorFromWindow.restype = wintypes.HMONITOR
        self.user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
        self.user32.GetMonitorInfoW.restype = wintypes.BOOL
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        self.user32.SetWindowPos.restype = wintypes.BOOL
        if hasattr(self.user32, "GetDpiForWindow"):
            self.user32.GetDpiForWindow.argtypes = [wintypes.HWND]
            self.user32.GetDpiForWindow.restype = wintypes.UINT
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            self._get_window_long_ptr = self.user32.GetWindowLongPtrW
            self._set_window_long_ptr = self.user32.SetWindowLongPtrW
        else:
            self._get_window_long_ptr = self.user32.GetWindowLongW
            self._set_window_long_ptr = self.user32.SetWindowLongW
        self._get_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int]
        self._get_window_long_ptr.restype = ctypes.c_ssize_t
        self._set_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self._set_window_long_ptr.restype = ctypes.c_ssize_t

        if self.dwmapi is not None:
            self.dwmapi.DwmSetWindowAttribute.argtypes = [
                wintypes.HWND,
                wintypes.DWORD,
                wintypes.LPCVOID,
                wintypes.DWORD,
            ]
            self.dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
            self.dwmapi.DwmExtendFrameIntoClientArea.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(MARGINS),
            ]
            self.dwmapi.DwmExtendFrameIntoClientArea.restype = ctypes.c_long
