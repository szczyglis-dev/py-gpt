"""Optional, application-local CLI tools for the built-in sandboxes."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from . import cache_policy


class NativeTools:
    """Download Pixi and provision CLI tools without touching system packages.

    Provision only while building a sandbox. Failures never affect Python
    readiness; an explicit sandbox rebuild can retry failed installations.
    """

    PIXI_VERSION = "0.74.0"
    PACKAGES = ("ripgrep", "git", "curl", "fd-find", "nodejs", "poppler",
                "7zip", "bzip2", "xz", "zstd", "file")
    UNIX_PACKAGES = ("jq", "wget", "tree", "zip", "unzip", "gzip", "tar",
                     "coreutils", "findutils")
    COMMANDS = ("rg", "git", "curl", "fd", "node", "pdftotext", "pdfinfo",
                "7z", "bzip2", "xz", "zstd", "file")
    UNIX_COMMANDS = ("jq", "wget", "tree", "zip", "unzip", "gzip", "tar", "ls", "find")
    _lock = threading.RLock()
    _attempted: set[str] = set()
    _validated: dict[str, bool] = {}

    def __init__(self, sandbox_root):
        self.root = Path(sandbox_root).resolve() / "tools"
        self.pixi_bin = self.root / "pixi" / ("pixi.exe" if os.name == "nt" else "pixi")
        self.manifest = self.root / "pixi.toml"
        self.prefix = self.root / ".pixi" / "envs" / "default"
        self.marker = self.root / ".pygpt-tools.json"

    @staticmethod
    def target(system=None, machine=None):
        system = system or platform.system()
        machine = (machine or platform.machine()).lower()
        arch = {"amd64": "x86_64", "x86_64": "x86_64",
                "arm64": "aarch64", "aarch64": "aarch64"}.get(machine)
        targets = {
            ("Windows", "x86_64"): ("x86_64-pc-windows-msvc", "win-64"),
            ("Darwin", "x86_64"): ("x86_64-apple-darwin", "osx-64"),
            ("Darwin", "aarch64"): ("aarch64-apple-darwin", "osx-arm64"),
            ("Linux", "x86_64"): ("x86_64-unknown-linux-musl", "linux-64"),
            ("Linux", "aarch64"): ("aarch64-unknown-linux-musl", "linux-aarch64"),
        }
        if (system, arch) not in targets:
            raise RuntimeError(f"Unsupported native tools platform: {system}/{machine}")
        return targets[system, arch]

    def _spec(self):
        return {"version": 2, "pixi": self.PIXI_VERSION,
                "platform": self.target()[1], "packages": list(self.get_packages())}

    def get_packages(self):
        return self.PACKAGES + (self.UNIX_PACKAGES if os.name != "nt" else ())

    def get_commands(self):
        return self.COMMANDS + (self.UNIX_COMMANDS if os.name != "nt" else ())

    @staticmethod
    def log(message):
        # Pixi diagnostics contain Unicode box drawing characters that legacy
        # Windows consoles cannot encode. Even logging must remain best effort.
        try:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            print(message.encode(encoding, errors="backslashreplace").decode(encoding))
        except (OSError, UnicodeError):
            pass

    def _bin_dirs(self):
        if os.name == "nt":
            return [self.prefix, self.prefix / "Library" / "bin",
                    self.prefix / "Library" / "mingw-w64" / "bin",
                    self.prefix / "Library" / "usr" / "bin",
                    self.prefix / "Scripts",
                    self.prefix / "bin"]
        return [self.prefix / "bin"]

    def _executable(self, name):
        suffix = ".exe" if os.name == "nt" else ""
        aliases = ("7z", "7zz") if name == "7z" else (name,)
        return next((directory / (alias + suffix) for directory in self._bin_dirs()
                     for alias in aliases if (directory / (alias + suffix)).is_file()), None)

    def _commands_exist(self):
        return all(self._executable(name) is not None for name in self.get_commands())

    def is_ready(self):
        try:
            return (json.loads(self.marker.read_text(encoding="utf-8")) == self._spec()
                    and self._commands_exist())
        except (OSError, ValueError, RuntimeError):
            return False

    def bin_dirs(self):
        """Expose only a successfully installed tool environment, never Pixi."""
        if not self.is_ready() or not self._can_execute():
            return []
        return [str(p) for p in self._bin_dirs() if p.is_dir()]

    def _validation_key(self):
        return os.path.normcase(str(self.root)) + json.dumps(self._spec(), sort_keys=True)

    def _can_execute(self):
        """Reject blocked/broken binaries before putting them ahead of host tools.

        File existence alone does not prove a Snap can execute a downloaded
        binary. Probe once per process, including cached installations.
        """
        with self._lock:
            key = self._validation_key()
            if key in self._validated:
                return self._validated[key]
            env = dict(os.environ)
            env["PATH"] = os.pathsep.join([*(str(p) for p in self._bin_dirs()),
                                          env.get("PATH", "")])
            flags = {"pdftotext": ["-v"], "pdfinfo": ["-v"], "7z": [],
                     "bzip2": ["--help"], "zip": ["-v"], "unzip": ["-v"]}
            try:
                for name in self.get_commands():
                    executable = self._executable(name)
                    if executable is None:
                        raise RuntimeError(f"Missing native executable: {name}")
                    result = subprocess.run(
                        [str(executable), *flags.get(name, ["--version"])],
                        cwd=self.root, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        check=False,
                    )
                    if result.returncode:
                        details = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")
                        raise RuntimeError(f"{name} cannot run ({result.returncode}): {details[-1000:].strip()}")
                self._validated[key] = True
            except Exception as exc:
                self._validated[key] = False
                self.log(f"[BUILT-IN SANDBOX] WARN: Private CLI tools disabled: {exc}. "
                         "Using inherited PATH; only tools accessible to this process can run.")
            return self._validated[key]

    @staticmethod
    def _download(url, destination):
        request = urllib.request.Request(url, headers={"User-Agent": "PyGPT-native-tools"})
        deadline = time.monotonic() + 120
        with urllib.request.urlopen(request, timeout=30) as response, open(destination, "wb") as out:
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError("Pixi download timed out")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

    def _ensure_pixi(self):
        if self.pixi_bin.is_file():
            return
        target, _ = self.target()
        extension = ".zip" if os.name == "nt" else ".tar.gz"
        asset = f"pixi-{target}{extension}"
        url = f"https://github.com/prefix-dev/pixi/releases/download/v{self.PIXI_VERSION}/{asset}"
        self.pixi_bin.parent.mkdir(parents=True, exist_ok=True)
        self.log(f"[BUILT-IN SANDBOX] Downloading Pixi {self.PIXI_VERSION} ({target})...")
        with tempfile.TemporaryDirectory(dir=self.pixi_bin.parent) as staging:
            archive = Path(staging) / asset
            checksum = Path(staging) / "sha256"
            self._download(url, archive)
            self._download(url + ".sha256", checksum)
            expected = checksum.read_text(encoding="utf-8").split()[0].lower()
            digest = hashlib.sha256()
            with archive.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if len(expected) != 64 or digest.hexdigest() != expected:
                raise RuntimeError("Pixi archive SHA-256 mismatch")
            binary = Path(staging) / self.pixi_bin.name
            # Copy just the executable; never extract arbitrary archive paths.
            if extension == ".zip":
                with zipfile.ZipFile(archive) as bundle:
                    member = next(item for item in bundle.infolist()
                                  if item.filename.rsplit("/", 1)[-1] == self.pixi_bin.name)
                    with bundle.open(member) as source, binary.open("wb") as out:
                        shutil.copyfileobj(source, out)
            else:
                with tarfile.open(archive, "r:gz") as bundle:
                    member = next(item for item in bundle.getmembers()
                                  if item.isfile() and item.name.rsplit("/", 1)[-1] == "pixi")
                    with bundle.extractfile(member) as source, binary.open("wb") as out:
                        shutil.copyfileobj(source, out)
            binary.chmod(0o755)
            os.replace(binary, self.pixi_bin)

    def _install(self):
        _, conda_platform = self.target()
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_pixi()
        manifest = ("[workspace]\nname = \"pygpt-native-tools\"\n"
                    "channels = [\"conda-forge\"]\n"
                    f"platforms = [{json.dumps(conda_platform)}]\n\n[dependencies]\n"
                    + "".join(f'{package} = "*"\n' for package in self.get_packages()))
        self.manifest.write_text(manifest, encoding="utf-8")
        env = dict(os.environ, PIXI_HOME=str(self.root / "home"),
                   PIXI_CACHE_DIR=str(self.root / "cache"), PIXI_NO_CONFIG="true")
        env.pop("PIXI_PROJECT_MANIFEST", None)
        self.log(f"[BUILT-IN SANDBOX] Installing optional CLI tools: {', '.join(self.get_packages())}...")
        result = subprocess.run(
            [str(self.pixi_bin), "install", "--manifest-path", str(self.manifest)],
            cwd=self.root, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
        if result.returncode:
            details = (result.stderr or result.stdout or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"Pixi installation failed ({result.returncode}): {details[-4000:].strip()}")
        if not self._commands_exist():
            raise RuntimeError("Pixi did not install all expected CLI executables")
        temporary = self.marker.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._spec(), sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.marker)

    def _clean_cache(self):
        """Remove only our private download cache; preserve installed packages."""
        if not cache_policy.CLEAN_PIXI_CACHE_AFTER_INSTALL:
            return
        cache = self.root / "cache"
        try:
            if not cache.exists():
                return
            # Never follow a replaced cache directory outside the managed root.
            if cache.resolve() != self.root / "cache" or cache.is_symlink():
                raise RuntimeError(f"Refusing to clean redirected Pixi cache: {cache}")
            shutil.rmtree(cache)
            self.log("[BUILT-IN SANDBOX] Pixi download cache removed.")
        except Exception as exc:
            self.log(f"[BUILT-IN SANDBOX] WARN: Unable to clean Pixi download cache: {exc}")

    def ensure_optional(self, force=False):
        """Attempt once per session; all download/install errors are warnings."""
        with self._lock:
            if self.is_ready() and not force:
                usable = self._can_execute()
                if usable:
                    self._clean_cache()
                return usable
            key = os.path.normcase(str(self.root))
            if key in self._attempted and not force:
                return self.is_ready() and self._can_execute()
            self._attempted.add(key)
            try:
                self._install()
                self._validated.pop(self._validation_key(), None)
                usable = self._can_execute()
                if usable:
                    self.log("[BUILT-IN SANDBOX] Optional CLI tools ready.")
                    self._clean_cache()
                return usable
            except Exception as exc:
                self.log(f"[BUILT-IN SANDBOX] WARN: Optional CLI tools unavailable: {exc}. "
                      "Python preparation remains available; using existing system tools.")
                return False
