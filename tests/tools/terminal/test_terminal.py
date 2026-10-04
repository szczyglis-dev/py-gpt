import os
import sys
import time
from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication, QWidget
from pygpt_net.tools.terminal import Terminal
from pygpt_net.tools.terminal.core.process import TerminalProcess


def wait_for(app, predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.01)
    assert predicate()


@pytest.mark.skipif(sys.platform == 'win32', reason='Unix PTY integration')
def test_real_shell_cwd_tty_resize_and_close(tmp_path):
    app = QApplication.instance() or QApplication([])
    process = TerminalProcess()
    output = []
    process.output.connect(output.append)
    try:
        process.start(str(tmp_path), command=['/bin/sh', '-i'])
        process.write("printf '__CWD__'; pwd; test -t 0 && echo '__TTY__';\r")
        wait_for(app, lambda: str(tmp_path) in ''.join(output) and '\r\n__TTY__' in ''.join(output))
        process.resize(31, 91)
        process.write('stty size\r')
        wait_for(app, lambda: '31 91' in ''.join(output))
        process.write('sleep 30\r')
        process.write('\x03')
    finally:
        process.close()
    assert not process.process.isalive()
    process.close()


def test_independent_frontends_and_cleanup(tmp_path):
    pytest.importorskip('pyte')
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(filesystem=SimpleNamespace(get_data_dir=lambda: str(tmp_path)))
    window.ui = SimpleNamespace(dialog={})
    tool = Terminal()
    tool.attach(window)
    tab1, tab2 = SimpleNamespace(), SimpleNamespace()
    first, second = tool.as_tab(tab1), tool.as_tab(tab2)
    try:
        first.resize(800, 500)
        second.resize(800, 500)
        wait_for(app, lambda: first.process.process is not None and second.process.process is not None)
        assert first.process.process.pid != second.process.process.pid
        first.process.write("echo __FIRST__\r")
        wait_for(app, lambda: '__FIRST__' in '\n'.join(first.screen.display))
        assert '__FIRST__' not in '\n'.join(second.screen.display)
        first.on_delete()
        assert not first.process.process.isalive()
        assert second.process.process.isalive()
        assert tool.allow_dialog and tool.multi_tab and tool.hide_in_tab_tools
        assert tool.get_toolbar()[0].icon == ':/icons/terminal.svg'
    finally:
        tool.on_exit()
        app.focusChanged.disconnect(tool._on_surface_focus_changed)
        window.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not tool.widgets


def test_alternate_screen_restores_shell():
    pytest.importorskip('pyte')
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    import pyte
    screen = TerminalScreen(80, 24, history=2000)
    stream = pyte.Stream(screen)
    stream.feed('shell prompt\x1b[?1049hfullscreen')
    assert 'fullscreen' in screen.display[0]
    assert 'shell prompt' not in screen.display[0]
    stream.feed('\x1b[?1049l')
    assert 'shell prompt' in screen.display[0]


def test_windows_backend_dispatch(monkeypatch, tmp_path):
    from unittest.mock import Mock
    import pygpt_net.tools.terminal.core.process as backend
    proc = Mock()
    proc.read.side_effect = EOFError
    factory = Mock()
    factory.spawn.return_value = proc
    monkeypatch.setitem(sys.modules, 'winpty', SimpleNamespace(PtyProcess=factory))
    monkeypatch.setattr(backend.sys, 'platform', 'win32')
    monkeypatch.setattr(backend.shutil, 'which', lambda name: 'pwsh.exe')
    process = TerminalProcess()
    process.start(str(tmp_path), 31, 91)
    process.reader.join(1)
    assert factory.spawn.call_args.args[0] == ['pwsh.exe']
    assert factory.spawn.call_args.kwargs['dimensions'] == (31, 91)
    assert factory.spawn.call_args.kwargs['cwd'] == str(tmp_path)
    process.close()
    proc.terminate.assert_called_once_with(force=True)


def test_dialog_reuses_session_and_reopens_after_close(tmp_path):
    pytest.importorskip('pyte')
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(filesystem=SimpleNamespace(get_data_dir=lambda: str(tmp_path)))
    window.ui = SimpleNamespace(dialog={})
    tool = Terminal()
    tool.attach(window)
    first = tool.open()
    try:
        wait_for(app, lambda: first.widget.process.process is not None)
        assert tool.open() is first
        first.close()
        assert not tool.widgets and not window.ui.dialog
        second = tool.open()
        assert second is not first
        wait_for(app, lambda: second.widget.process.process is not None)
        second.close()
    finally:
        tool.on_exit()
        app.focusChanged.disconnect(tool._on_surface_focus_changed)
        window.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_grid_uses_painted_font_despite_application_stylesheet():
    pytest.importorskip('pyte')
    import pyte
    from PySide6.QtGui import QFontMetricsF
    from pygpt_net.tools.terminal.ui.widget import TerminalWidget
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    app = QApplication.instance() or QApplication([])
    previous = app.styleSheet()
    widget = None
    try:
        app.setStyleSheet('QWidget { font-family: Sans; font-size: 9px; }')
        widget = TerminalWidget(SimpleNamespace())
        widget.timer.stop()
        widget.resize(880, 460)
        fm = QFontMetricsF(widget.terminal_font)
        assert fm.horizontalAdvance('i') == pytest.approx(fm.horizontalAdvance('M'))
        assert widget.cell_width == pytest.approx(fm.horizontalAdvance('M'))
        widget.screen = TerminalScreen(2, 2, history=2000)
        widget.stream = pyte.Stream(widget.screen)
        widget.show()
        app.processEvents()
        widget.sync_size()
        rows, cols = widget.dimensions()
        assert cols > 80
        assert (widget.screen.lines, widget.screen.columns) == (rows, cols)
        widget.feed('marcin@host:~/data$ ls')
        assert widget.screen.display[0].startswith('marcin@host:~/data$ ls')
        assert not widget.grab().isNull()
    finally:
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        app.setStyleSheet(previous)


def test_tab_input_zoom_cursor_and_scrollback(tmp_path):
    pytest.importorskip('pyte')
    from PySide6.QtCore import Qt, QCoreApplication, QEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QVBoxLayout
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(filesystem=SimpleNamespace(get_data_dir=lambda: str(tmp_path)))
    window.ui = SimpleNamespace(dialog={})
    tool = Terminal()
    tool.attach(window)
    widget = tool.as_tab(SimpleNamespace())
    QVBoxLayout(window).addWidget(widget)
    window.resize(800, 400)
    window.show()
    window.activateWindow()
    try:
        wait_for(app, lambda: widget.process.process is not None)
        QTest.mouseClick(widget.viewport(), Qt.LeftButton)
        assert widget.hasFocus()
        QTest.keyClicks(widget, 'echo __KEYBOARD__')
        QTest.keyClick(widget, Qt.Key_Return)
        wait_for(app, lambda: '__KEYBOARD__' in '\n'.join(widget.screen.display))
        assert widget.cursor_timer.isActive()
        assert widget.cursor_timer.interval() == 500
        previous = widget.dimensions()
        widget.apply_font(widget.value + 4)
        assert widget.dimensions()[1] < previous[1]
        assert widget.terminal_font.family() != 'Monaspace Neon'
        widget.feed('\r\n'.join('line '+str(i) for i in range(100)))
        app.processEvents()
        bar = widget.verticalScrollBar()
        assert bar.isVisible() and bar.maximum() > 0
        bar.setValue(0)
        assert widget.offset == bar.maximum()
        bar.setValue(bar.maximum())
        assert widget.offset == 0
    finally:
        tool.on_exit()
        app.focusChanged.disconnect(tool._on_surface_focus_changed)
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_resize_preserves_output_and_cursor_without_duplicating_lines():
    pytest.importorskip('pyte')
    import pyte
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    screen = TerminalScreen(80, 12, history=2000)
    stream = pyte.Stream(screen)
    stream.feed('\r\n'.join('line-' + str(i) + '-abcdefghijklmnop' for i in range(10)))
    original = screen.display[:10]
    screen.resize(lines=5, columns=10)
    assert screen.cursor.y == 4
    assert len(screen.history.top) == 25
    screen.resize(lines=12, columns=80)
    assert screen.display[:10] == original
    assert screen.cursor.y == 9
    assert not screen.history.top
    for _ in range(3):
        screen.resize(lines=5, columns=10)
        screen.resize(lines=12, columns=80)
    assert screen.display[:10] == original


def test_selection_clipboard_menu_and_reserved_shortcuts(monkeypatch):
    pytest.importorskip('pyte')
    import pyte
    from unittest.mock import Mock
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu
    from pygpt_net.tools.terminal.ui.widget import TerminalWidget
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    app = QApplication.instance() or QApplication([])
    context_menu = SimpleNamespace(get_zoom_menu=lambda *args: QMenu('Zoom'))
    widget = TerminalWidget(SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(context_menu=context_menu))))
    widget.timer.stop()
    widget.resize(700, 300)
    widget.screen = TerminalScreen(80, 12, history=2000)
    widget.stream = pyte.Stream(widget.screen)
    widget.show()
    app.processEvents()
    widget.feed('hello terminal')
    try:
        assert widget.verticalScrollBar().isVisible()
        left = QPoint(widget.padding + 1, widget.padding + 2)
        right = QPoint(round(widget.padding + 5 * widget.cell_width + 1), widget.padding + 2)
        QTest.mousePress(widget.viewport(), Qt.LeftButton, pos=left)
        QTest.mouseMove(widget.viewport(), right)
        QTest.mouseRelease(widget.viewport(), Qt.LeftButton, pos=right)
        assert widget.selected_text() == 'hello'
        QTest.keyClick(widget, Qt.Key_C, Qt.ControlModifier | Qt.ShiftModifier)
        assert app.clipboard().text() == 'hello'
        menu = widget.build_context_menu()
        assert len(menu.actions()) == 5
        assert menu.actions()[0].isEnabled()
        write = Mock()
        monkeypatch.setattr(widget.process, 'write', write)
        QTest.keyClick(widget, Qt.Key_C, Qt.ControlModifier)
        QTest.keyClick(widget, Qt.Key_V, Qt.ControlModifier)
        assert [call.args[0] for call in write.call_args_list] == ['\x03', '\x16']
        widget.select_all()
        assert 'hello terminal' in widget.selected_text()
        app.clipboard().setText('pasted')
        QTest.keyClick(widget, Qt.Key_V, Qt.ControlModifier | Qt.ShiftModifier)
        assert write.call_args.args[0] == 'pasted'
    finally:
        widget.cursor_timer.stop()
        widget.resize_timer.stop()
        widget.hide()
        widget.deleteLater()


def test_zoom_burst_coalesces_pty_resize_and_skips_global_theme(qapp):
    pytest.importorskip('pyte')
    import pyte
    from unittest.mock import MagicMock, Mock
    from PySide6.QtTest import QTest
    from pygpt_net.tools.terminal.ui.widget import TerminalWidget
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    values = {'font_size': 14}
    window = MagicMock()
    window.core.config.get.side_effect = values.get
    window.core.config.set.side_effect = values.__setitem__
    widget = TerminalWidget(SimpleNamespace(window=window))
    widget.timer.stop()
    widget.resize(800, 400)
    widget.screen = TerminalScreen(80, 20, history=2000)
    widget.stream = pyte.Stream(widget.screen)
    widget.show()
    qapp.processEvents()
    resize = Mock()
    widget.process.resize = resize
    try:
        for value in (15, 16, 17, 18):
            widget.on_zoom_changed(value)
        resize.assert_not_called()
        QTest.qWait(200)
        resize.assert_called_once()
        widget.sync_size()
        resize.assert_called_once()
        window._text_zoom_commit.flush()
        window.core.config.save.assert_called_once()
        window.controller.theme.nodes.apply_all.assert_not_called()
        assert values['terminal.font_size'] == 18
    finally:
        widget.cursor_timer.stop()
        widget.resize_timer.stop()
        widget.hide()
        widget.deleteLater()


def test_container_collapse_does_not_resize_live_shell(tmp_path, monkeypatch):
    pytest.importorskip('pyte')
    from unittest.mock import Mock
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QVBoxLayout
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(filesystem=SimpleNamespace(get_data_dir=lambda: str(tmp_path)))
    window.ui = SimpleNamespace(dialog={})
    tool = Terminal()
    tool.attach(window)
    widget = tool.as_tab(SimpleNamespace())
    QVBoxLayout(window).addWidget(widget)
    window.resize(800, 400)
    window.show()
    try:
        wait_for(app, lambda: widget.process.process is not None)
        QTest.qWait(200)
        previous = (widget.screen.lines, widget.screen.columns)
        resize = Mock(wraps=widget.process.resize)
        monkeypatch.setattr(widget.process, 'resize', resize)
        # Intermediate geometries from a splitter animation must not reach PTY.
        for width in (600, 400, 200, 80, 20):
            window.resize(width, 400)
            app.processEvents()
        QTest.qWait(200)
        assert all(call.args[1] >= 20 for call in resize.call_args_list)
        resize.reset_mock()
        widget.hide()
        window.resize(400, 250)
        QTest.qWait(200)
        resize.assert_not_called()
        window.resize(800, 400)
        widget.show()
        QTest.qWait(200)
        assert (widget.screen.lines, widget.screen.columns) == previous
        resize.reset_mock()
        window.resize(650, 400)
        QTest.qWait(200)
        resize.assert_called_once()
        assert widget.screen.columns >= 20
    finally:
        tool.on_exit()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.mark.skipif(sys.platform == 'win32', reason='Bash readline integration')
def test_real_bash_prompt_survives_repeated_container_collapse(tmp_path, monkeypatch):
    pytest.importorskip('pyte')
    import shutil
    if not shutil.which('bash'):
        pytest.skip('bash unavailable')
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QVBoxLayout
    from pygpt_net.tools.terminal.ui.widget import TerminalWidget
    monkeypatch.setenv('PS1', 'marcin@marcin-Legion:~/pygpt_workdir/data$ ')
    original = TerminalProcess.start
    def start_bash(self, cwd, rows=24, columns=80, command=None):
        return original(self, cwd, rows, columns, ['bash', '--noprofile', '--norc', '-i'])
    monkeypatch.setattr(TerminalProcess, 'start', start_bash)
    app = QApplication.instance() or QApplication([])
    window = QWidget()
    window.core = SimpleNamespace(filesystem=SimpleNamespace(get_data_dir=lambda: str(tmp_path)))
    window.ui = SimpleNamespace(dialog={})
    tool = Terminal()
    tool.attach(window)
    widget = tool.as_tab(SimpleNamespace())
    QVBoxLayout(window).addWidget(widget)
    window.resize(800, 400)
    window.show()
    try:
        wait_for(app, lambda: widget.screen is not None and any('marcin@marcin-Legion:' in row for row in widget.screen.display))
        for width in (350, 800, 350, 800):
            window.resize(width, 400)
            QTest.qWait(100)
        for _ in range(3):
            for width in (600, 400, 200, 80, 20):
                window.resize(width, 400)
                QTest.qWait(10)
            QTest.qWait(200)
            widget.hide()
            window.resize(800, 400)
            widget.show()
            QTest.qWait(200)
        text = '\n'.join(''.join(row[x].data for x in range(widget.screen.columns)).rstrip() for row in widget.all_lines())
        assert text.count('marcin@marcin-Legion:') == 1
        assert 'marcin@marcin-Legion:~/pygpt_workdir/data$' in text
        assert len(widget.screen.history.top) == 0
    finally:
        tool.on_exit()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_reflow_rewraps_history_and_preserves_hard_line_breaks_and_colors():
    pytest.importorskip('pyte')
    import pyte
    from pygpt_net.tools.terminal.core.screen import TerminalScreen
    screen = TerminalScreen(12, 4, history=2000)
    stream = pyte.Stream(screen)
    stream.feed('\x1b[31mabcdefghijklmnopqrstuvwx\x1b[0m\r\nSHORT\r\nthird line\r\nlast')
    screen.resize(lines=8, columns=24)
    assert screen.display[0] == 'abcdefghijklmnopqrstuvwx'
    assert screen.display[1].rstrip() == 'SHORT'
    assert screen.display[2].rstrip() == 'third line'
    assert screen.buffer[0][18].fg == 'red'
    original = screen.display[:4]
    for width in (6, 30, 8, 24):
        screen.resize(lines=8, columns=width)
    assert screen.display[:4] == original
    assert screen.cursor.y == 3 and screen.cursor.x == 4
