"""Exercise real OS signals while Qt is waiting in its event loop."""

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name == 'nt', reason='POSIX process signals')
@pytest.mark.parametrize('signum', [signal.SIGTERM, signal.SIGINT, signal.SIGHUP])
def test_system_signal_runs_quit_cleanup(signum):
    source = str(Path(__file__).resolve().parents[2] / 'src')
    script = '''
import signal
from PySide6.QtCore import QCoreApplication, QTimer
from pygpt_net.core.shutdown_signals import ShutdownSignals
app = QCoreApplication([])
old_handler = signal.getsignal(signal.SIGTERM)
bridge = ShutdownSignals(app)
app.aboutToQuit.connect(lambda: print("saved and cleaned", flush=True))
QTimer.singleShot(0, lambda: print("ready", flush=True))
app.exec()
assert signal.getsignal(signal.SIGTERM) == old_handler
bridge.close()
print("restored", flush=True)
'''
    env = dict(os.environ, PYTHONPATH=source)
    process = subprocess.Popen(
        [sys.executable, '-c', script], env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        assert process.stdout.readline().strip() == 'ready'
        process.send_signal(signum)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        assert 'saved and cleaned' in stdout
        assert 'restored' in stdout
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
