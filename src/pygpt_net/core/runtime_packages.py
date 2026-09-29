"""Optional application dependencies, separate from AI execution sandboxes."""
import importlib
import importlib.metadata as metadata
import os
from pathlib import Path
import queue
import signal
import shutil
import site
import subprocess
import sys
import tempfile
import threading

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


class RuntimePackages:
    _lock = threading.Lock()

    def __init__(self, window):
        self.window = window
        self._path = None
        self._dll_handles = {}
        self.requests = threading.local()

    @property
    def path(self):
        # Runtime imports are process-scoped: switching profiles needs a restart.
        if self._path is None:
            self._path = str(Path(self.window.core.config.get_user_path()) /
                             'extra_packages' / f'{sys.version_info.major}.{sys.version_info.minor}')
        return self._path

    def check_profile(self):
        current = Path(self.window.core.config.get_user_path()).resolve()
        if current != Path(self.path).parent.parent.resolve():
            raise RuntimeError('Restart PyGPT after switching workdir/profile before changing runtime packages.')

    def activate(self):
        Path(self.path).mkdir(parents=True, exist_ok=True)
        before = list(sys.path)
        site.addsitedir(self.path)
        # Even .pth files must not put optional libraries before the app runtime.
        sys.path[:] = before + [p for p in sys.path if p not in before]
        if hasattr(os, 'add_dll_directory'):
            root = Path(self.path)
            for directory in [root, *root.glob('*/lib'), *root.glob('*.libs')]:
                key = str(directory)
                if directory.is_dir() and key not in self._dll_handles:
                    self._dll_handles[key] = os.add_dll_directory(key)
        importlib.invalidate_caches()

    @staticmethod
    def requirements(dependencies):
        result = []
        for dep in dependencies:
            if isinstance(dep, dict):
                if dep.get('optional', False):
                    continue
                value = str(dep['name']) + str(dep.get('version') or '')
            else:
                value = str(dep).strip()
            req = Requirement(value)
            if req.url:
                raise ValueError('Use package names and version constraints, not URLs.')
            if req.marker is None or req.marker.evaluate():
                result.append(str(req))
        return result

    def missing(self, dependencies, _seen=None):
        seen = set() if _seen is None else _seen
        missing = []
        for value in self.requirements(dependencies):
            if value in seen:
                continue
            seen.add(value)
            req = Requirement(value)
            try:
                dist = metadata.distribution(req.name)
                if req.specifier and not req.specifier.contains(dist.version, prereleases=True):
                    raise metadata.PackageNotFoundError(req.name)
                # Extras require their own dependency checks.
                for child in dist.requires or []:
                    child_req = Requirement(child)
                    if req.extras and (child_req.marker is None or any(
                            child_req.marker.evaluate({'extra': extra}) for extra in req.extras)):
                        child_req.marker = None
                        if self.missing([str(child_req)], seen):
                            raise metadata.PackageNotFoundError(req.name)
            except metadata.PackageNotFoundError:
                missing.append(value)
        return missing

    def installed(self):
        return sorted([(d.metadata['Name'], d.version) for d in
                       metadata.distributions(path=[self.path]) if d.metadata['Name']],
                      key=lambda item: item[0].lower())

    def ensure_dependencies(self, dependencies):
        missing = self.missing(dependencies)
        if not missing:
            return
        handler = getattr(self.requests, 'handler', None)
        if handler is None or not handler(missing):
            raise RuntimeError('Add-on dependencies were not installed: ' + ', '.join(missing))
        if self.missing(dependencies):
            raise RuntimeError('Dependencies are still unavailable. Restart PyGPT and retry.')

    def _environment(self):
        env = dict(os.environ)
        for key in list(env):
            if key.startswith(('UV_', 'PIP_')) or key in ('VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH'):
                env.pop(key, None)
        env.update(UV_NO_PROGRESS='1', UV_PYTHON_INSTALL_DIR=str(Path(self.path).parent / '.python'),
                   UV_CACHE_DIR=str(Path(self.path).parent / '.cache'))
        # Frozen loader paths must not leak into an external Python/build process.
        for key in ('LD_LIBRARY_PATH', 'LIBPATH'):
            if getattr(sys, 'frozen', False):
                original = env.get(key + '_ORIG')
                if original is None:
                    env.pop(key, None)
                else:
                    env[key] = original
        return env

    def _run(self, args, cancel, output):
        from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime
        if cancel.is_set():
            raise RuntimeError('Package operation cancelled.')
        lines = queue.Queue()
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace', env=self._environment(),
                              start_new_session=os.name != 'nt',
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as proc:
            job = BuiltinSandboxRuntime._attach_windows_job(proc)
            def read():
                for line in proc.stdout:
                    lines.put(line.rstrip())
            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            try:
                while proc.poll() is None or reader.is_alive() or not lines.empty():
                    if cancel.is_set():
                        raise RuntimeError('Package operation cancelled.')
                    try:
                        output(lines.get(timeout=0.1))
                    except queue.Empty:
                        pass
                if proc.returncode:
                    raise RuntimeError(f'Package installer failed (exit {proc.returncode}). See installation output.')
            finally:
                if os.name != 'nt':
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif proc.poll() is None:
                    proc.kill()
                BuiltinSandboxRuntime.close_process_job(job)
                proc.wait()
                reader.join(timeout=2)

    def operate(self, action, packages, cancel, output):
        self.check_profile()
        if not self._lock.acquire(blocking=False):
            raise RuntimeError('Another package operation is running.')
        try:
            from PySide6.QtCore import QLockFile
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            lock = QLockFile(str(Path(self.path).parent / '.packages.lock'))
            lock.setStaleLockTime(0)
            if not lock.tryLock(0):
                raise RuntimeError('Another PyGPT instance is changing packages.')
            try:
                self._operate(action, packages, cancel, output)
            finally:
                lock.unlock()
        finally:
            self._lock.release()

    def _operate(self, action, packages, cancel, output):
        from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime
        if action not in ('install', 'uninstall'):
            raise ValueError('Unknown package operation')
        packages = self.requirements(packages)
        if not packages:
            return
        uv = BuiltinSandboxRuntime(self.window, 'python').find_uv()
        target = Path(self.path)
        target.mkdir(parents=True, exist_ok=True)
        log_enabled = self.window.core.config.get('log.packages', False)
        def report(line):
            output(line)
            if log_enabled:
                with (target.parent / 'packages.log').open('a', encoding='utf-8') as log:
                    log.write(line + '\n')
        # Work on a copy. Failure/cancellation leaves the live installation intact.
        with tempfile.TemporaryDirectory(prefix='.packages-', dir=target.parent) as temp:
            stage = Path(temp) / 'site-packages'
            report('Preparing working copy…')
            def copy_file(source, destination):
                if cancel.is_set():
                    raise RuntimeError('Package operation cancelled.')
                return shutil.copy2(source, destination)
            shutil.copytree(target, stage, copy_function=copy_file)
            args = [uv, '--no-config', 'pip', action, '--target', str(stage)]
            if action == 'install':
                if getattr(sys, 'frozen', False):
                    version = f'{sys.version_info.major}.{sys.version_info.minor}'
                    self._run([uv, '--no-config', 'python', 'install', '--no-bin', '--no-registry', version], cancel, report)
                    args += ['--python', version, '--managed-python',
                             '--python-version', version]
                else:
                    args += ['--python', sys.executable]
                constraints = Path(temp) / 'constraints.txt'
                pins = {}
                for dist in metadata.distributions():
                    if not dist.metadata['Name']:
                        continue
                    location = Path(dist.locate_file('')).resolve()
                    if location == target.resolve() or target.resolve() in location.parents:
                        continue
                    pins.setdefault(canonicalize_name(dist.metadata['Name']), dist.version)
                constraints.write_text(''.join(f'{name}=={version}\n' for name, version in pins.items()), encoding='utf-8')
                args += ['--constraint', str(constraints)]
            else:
                allowed = {canonicalize_name(name) for name, _ in self.installed()}
                if any(canonicalize_name(Requirement(p).name) not in allowed for p in packages):
                    raise ValueError('Only packages in extra_packages can be removed.')
                packages = [Requirement(p).name for p in packages]
            report(f'{action}: {", ".join(packages)} → {target}')
            self._run(args + packages, cancel, report)
            if cancel.is_set():
                raise RuntimeError('Package operation cancelled.')
            backup = Path(temp) / 'previous'
            target.rename(backup)
            try:
                stage.rename(target)
            except Exception:
                backup.rename(target)
                raise
        importlib.invalidate_caches()
