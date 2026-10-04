# Built-in sandbox runtimes

`builtin.py` uses uv to prepare independent Python and System/OS virtual
environments. `native_tools.py` adds a shared optional environment using Pixi
and conda-forge. All supported platforms get ripgrep (`rg`), Git, curl, fd,
Node.js/npm, Poppler (`pdftotext`, `pdfinfo`), 7-Zip (`7z`/`7zz`), bzip2, xz,
zstd and file. Linux/macOS additionally get jq, wget, tree, zip, unzip, gzip,
tar, coreutils and findutils; these conda-forge packages lack Windows builds.

While building or rebuilding a built-in sandbox, its preparation worker downloads the pinned Pixi release
from https://github.com/prefix-dev/pixi/releases and checks the archive's
published SHA-256 before copying its executable. No installer script is run.
The same flow is used for source, PyInstaller, Snap and AppImage installations.
Supported targets are Windows x64, Linux x64/ARM64 and macOS Intel/Apple Silicon.

Files live under the application's base workdir:

- `sandbox/tools/pixi/`: downloaded Pixi executable.
- `sandbox/tools/pixi.toml` and `pixi.lock`: native package specification and lock.
- `sandbox/tools/.pixi/envs/default/`: native packages and their dependencies.
- `sandbox/tools/.pygpt-tools.json`: successful installation marker.

Application startup and execution in an already prepared Python environment do
not download or install tools. Existing tools are reused. Their executable
directories are included only in child-process PATH, after the Python venv and
before inherited system paths. The application and global system PATH are
unchanged. This also covers the built-in IPython kernel environment.

After successful preparation and executable checks, the private
`sandbox/tools/cache` download cache is removed. Installed packages in `.pixi`,
Pixi itself, the manifest, lockfile and readiness marker are preserved. Cached
tool environments also have leftover download caches cleaned when a sandbox is
built. Cleanup errors are warnings only. Future package changes may download
packages again; ordinary command execution does not recreate the cache.

Before exposing the directories, each CLI is actually executed with its version
or help option once per application session. Cached installations are checked
too. If any executable is blocked or broken, the entire private tool environment
is omitted from PATH for this session and a console warning is printed.

Download, checksum, unsupported-platform, package-installation and execution
errors produce console warnings only. They do not change Python readiness or
invalidate its preparation marker. Failed optional installations are retried
when a sandbox is prepared in a later session or on a manual built-in sandbox rebuild. Snap's
strict confinement may deny downloaded executables; Python still uses its
existing packaged-interpreter setup, and commands are resolved through inherited
PATH. This fallback only works for tools already present and accessible inside
the Snap confinement. An unavailable/blocked system tool fails that command;
it does not make the Python environment unavailable or bypass Snap restrictions.

Python/System preparation also clears the shared `sandbox/cache` through
`uv cache clean` after packages are installed and the Python readiness marker
is saved. Packages are installed in copy mode so they do not depend on cache
symlinks. The interpreter in `sandbox/runtime` and both virtual environments
remain intact. Cleanup failures only produce console warnings.

Two independent code flags in `cache_policy.py` control this behavior:
`CLEAN_UV_CACHE_AFTER_INSTALL` and `CLEAN_PIXI_CACHE_AFTER_INSTALL` (both `True`
by default). Set either to `False` to retain that manager's download cache.
