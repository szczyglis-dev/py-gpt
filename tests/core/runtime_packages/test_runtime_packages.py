import importlib
from importlib import metadata
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock
import zipfile
import shutil

import pytest

from pygpt_net.core.runtime_packages import RuntimePackages
from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime


@pytest.fixture
def manager(tmp_path, monkeypatch):
    config = SimpleNamespace(get_user_path=lambda: str(tmp_path), get_base_workdir=lambda: str(tmp_path), get=lambda *a: False)
    result = RuntimePackages(SimpleNamespace(core=SimpleNamespace(config=config)))
    monkeypatch.setattr(sys, 'path', list(sys.path))
    result.activate()
    return result


def test_version_path_and_low_import_priority(manager):
    assert Path(manager.path).name == f'{sys.version_info.major}.{sys.version_info.minor}'
    assert sys.path[-1] == manager.path
    before = list(sys.path)
    manager.activate()
    assert sys.path == before


def test_requirement_validation_and_markers(manager):
    assert manager.requirements(['demo>=1; python_version<"2"']) == []
    assert manager.requirements([{'name': 'demo', 'version': '>=1'},
                                 {'name': 'other', 'optional': True}]) == ['demo>=1']
    with pytest.raises(ValueError):
        manager.requirements(['--index-url evil'])
    with pytest.raises(ValueError):
        manager.requirements(['demo @ https://example.org/demo.whl'])


def test_missing_version_and_installed_listing(manager):
    dist = Path(manager.path) / 'pygpt_test_dep-1.0.dist-info'
    dist.mkdir()
    (dist / 'METADATA').write_text('Metadata-Version: 2.1\nName: pygpt-test-dep\nVersion: 1.0\n')
    assert manager.missing(['pygpt-test-dep>=1']) == []
    assert manager.missing(['pygpt-test-dep>=2']) == ['pygpt-test-dep>=2']
    assert manager.installed() == [('pygpt-test-dep', '1.0')]


def test_missing_dependencies_require_approval(manager):
    with pytest.raises(RuntimeError, match='not installed'):
        manager.ensure_dependencies(['pygpt-nonexistent-test-package'])
    handler = MagicMock(return_value=False)
    manager.requests.handler = handler
    with pytest.raises(RuntimeError):
        manager.ensure_dependencies(['pygpt-nonexistent-test-package'])
    handler.assert_called_once()


def test_failure_keeps_live_tree(manager, monkeypatch):
    (Path(manager.path) / 'keep.txt').write_text('original')
    monkeypatch.setattr(BuiltinSandboxRuntime, 'find_uv', lambda self: '/fake/uv')
    def fail(args, cancel, output):
        stage = Path(args[args.index('--target') + 1])
        (stage / 'keep.txt').write_text('changed')
        raise RuntimeError('failed')
    monkeypatch.setattr(manager, '_run', fail)
    with pytest.raises(RuntimeError, match='failed'):
        manager.operate('install', ['demo'], threading.Event(), lambda s: None)
    assert (Path(manager.path) / 'keep.txt').read_text() == 'original'
    assert not list(Path(manager.path).parent.glob('.packages-*'))


def test_frozen_uses_managed_matching_python(manager, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(BuiltinSandboxRuntime, 'find_uv', lambda self: '/fake/uv')
    calls = []
    monkeypatch.setattr(manager, '_run', lambda args, *rest: calls.append(args))
    manager.operate('install', ['demo'], threading.Event(), lambda s: None)
    assert '--no-bin' in calls[0] and '--no-registry' in calls[0]
    install = calls[1]
    assert install[install.index('--python') + 1] == Path(manager.path).name
    assert sys.executable not in install
    assert '--managed-python' in install


def test_source_pins_core_and_uses_current_python(manager, monkeypatch):
    monkeypatch.setattr(BuiltinSandboxRuntime, 'find_uv', lambda self: '/fake/uv')
    def check(args, *rest):
        assert args[args.index('--python') + 1] == sys.executable
        constraints = Path(args[args.index('--constraint') + 1]).read_text()
        assert 'packaging==' in constraints
    monkeypatch.setattr(manager, '_run', check)
    manager.operate('install', ['demo'], threading.Event(), lambda s: None)


def test_cancel_preserves_tree(manager, monkeypatch):
    monkeypatch.setattr(BuiltinSandboxRuntime, 'find_uv', lambda self: '/fake/uv')
    event = threading.Event()
    monkeypatch.setattr(manager, '_run', lambda *args: event.set())
    with pytest.raises(RuntimeError, match='cancelled'):
        manager.operate('install', ['demo'], event, lambda s: None)
    assert Path(manager.path).is_dir()


def test_uninstall_cannot_touch_core(manager, monkeypatch):
    monkeypatch.setattr(BuiltinSandboxRuntime, 'find_uv', lambda self: '/fake/uv')
    with pytest.raises(ValueError, match='Only packages'):
        manager.operate('uninstall', ['packaging'], threading.Event(), lambda s: None)


def test_operation_serialization(manager):
    with manager._lock:
        with pytest.raises(RuntimeError, match='Another package'):
            manager.operate('install', ['demo'], threading.Event(), lambda s: None)

def test_addon_decline_preserves_installed_version(manager, tmp_path):
    import json
    from pygpt_net.core.extensions import Extensions
    manager.window.core.packages = manager
    core = Extensions(manager.window)
    source = tmp_path / 'source'
    source.mkdir()
    manifest = {
        'manifest_version': 1, 'id': 'test_addon', 'name': 'Test',
        'description': 'Test addon', 'version': '1.0', 'min_app_version': '1.0',
        'author': 'Test', 'contact': 'test@example.org', 'type': 'plugin',
        'entrypoint': 'plugin.py:Plugin', 'external_dependencies': [],
    }
    (source / 'plugin.py').write_text('class Plugin: pass\n')
    (source / 'manifest.json').write_text(json.dumps(manifest))
    core.import_directory(str(source))
    manifest.update(version='2.0', external_dependencies=['pygpt-nonexistent-test-package'])
    (source / 'manifest.json').write_text(json.dumps(manifest))
    manager.requests.handler = lambda requirements: False
    with pytest.raises(RuntimeError, match='not installed'):
        core.import_directory(str(source))
    assert core.get_installed_versions()['test_addon'] == '1.0'


def test_profile_switch_keeps_global_runtime_packages(manager, tmp_path):
    path = manager.path
    manager.window.core.config.get_user_path = lambda: str(tmp_path / 'other-profile')

    assert manager.check_profile() is True
    assert manager.path == path


def test_cross_process_lock(manager):
    from PySide6.QtCore import QLockFile
    lock = QLockFile(str(Path(manager.path).parent / '.packages.lock'))
    assert lock.tryLock(0)
    try:
        with pytest.raises(RuntimeError, match='Another PyGPT instance'):
            manager.operate('install', ['demo'], threading.Event(), lambda s: None)
    finally:
        lock.unlock()


def test_build_metadata_only_includes_analyzed_distributions(tmp_path, monkeypatch):
    import runpy
    build = runpy.run_path(str(Path(__file__).resolve().parents[3] / 'bin/pyinstaller_runtime_metadata.py'))
    package = tmp_path / 'demo' / '__init__.py'
    package.parent.mkdir()
    package.write_text('')
    info = tmp_path / 'demo-1.0.dist-info' / 'METADATA'
    info.parent.mkdir()
    info.write_text('Name: demo\nVersion: 1.0\n')
    dist = SimpleNamespace(files=[Path('demo/__init__.py'), Path('demo-1.0.dist-info/METADATA')],
                           locate_file=lambda f: tmp_path / f)
    monkeypatch.setattr(metadata, 'distributions', lambda: [dist])
    analysis = SimpleNamespace(pure=[], binaries=[], datas=[])
    build['add_runtime_metadata'](analysis)
    assert analysis.datas == []
    analysis.pure = [('demo', str(package), 'PYMODULE')]
    build['add_runtime_metadata'](analysis)
    assert analysis.datas == [('demo-1.0.dist-info/METADATA', str(info), 'DATA')]
    build['add_runtime_metadata'](analysis)
    assert len(analysis.datas) == 1
