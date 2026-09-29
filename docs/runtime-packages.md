# Optional runtime packages

Config → Package Manager (immediately above Open workdir directory) manages optional
Python dependencies in `<workdir>/extra_packages/<Python major.minor>/`. It lists
installed distributions, accepts one PEP 508 requirement per line, and removes the
selected distribution. Example: `openai-whisper` or `requests>=2.32`.

The manager, add-ons and local Whisper share one asynchronous installer and the
existing progress dialog. Installation/removal requires confirmation with the
package list and destination. The progress bar is indeterminate because uv does
not provide a reliable overall percentage; installer output appears in the dialog.
Enable **Settings → Debug → Log package installations** to also save output to
`<workdir>/extra_packages/packages.log`.

## Runtime and installer

* Startup registers the current Python version's directory using `site.addsitedir`.
  Existing application import paths retain priority. Windows keeps DLL directory
  handles for the target, package `lib` directories and wheel `.libs` directories.
* Source/PyPI use the running Python executable for resolution/builds. Frozen builds
  download a matching minor-version CPython using uv, into `extra_packages/.python`,
  without changing the system Python or Windows Python registration. This interpreter
  builds/resolves packages; imports run inside the application.
* uv always uses `--target`; it does not install into the app's venv or AI sandbox.
  Its cache is under `extra_packages/.cache`. Version constraints pin distributions
  already supplied by the app. Both PyInstaller specs preserve metadata for analyzed
  distributions so these constraints also work in new frozen builds.
* Changes are staged in a sibling directory, with the original retained until the
  installer succeeds. Allow space for a copy of existing packages plus downloads.
  Cancellation or an installer failure leaves the live target unchanged. A process
  lock and a file lock serialize operations, including separate PyGPT instances.
* Only distributions inside the active target can be uninstalled. Dependencies are
  not automatically pruned: another add-on may use them. Restart after changing
  imported packages. Windows can reject replacing loaded native libraries; switch
  away from consumers and restart before retrying.
* Imports are process-scoped. Switching profile/workdir does not switch Python
  libraries in a running process. Package mutations require a restart after a switch.

## Add-ons

The existing `external_dependencies` manifest field accepts requirement strings or
objects such as `{"name": "example", "version": ">=1,<2", "optional": false}`.
Optional entries are skipped; Python environment markers and version constraints
are evaluated. Requirements already available from the app or active target are
reused. Direct URLs and installer flags are not accepted as package requirements.

ZIP, directory, GitHub and catalog installs all check dependencies before changing
the installed add-on. The worker waits while the GUI obtains approval and runs the
shared installer. Rejection/failure leaves the add-on untouched. At startup, missing
requirements of existing add-ons trigger the same installer offer, including after
an upgrade selects a new Python-version directory. Restart to load repaired add-ons.

## Whisper and platform validation

Selecting local Whisper and starting recording offers `openai-whisper` installation
when imports are unavailable. On success the existing model preparation flow runs.
The old unconditional compiled/Snap prohibition is removed; import availability now
determines readiness. FFmpeg is still a separate system/bundled executable requirement.

Tests cover real offline uv installation/import/removal, version checks, cancellation,
rollback, locks, confirmation rejection, preserving an existing add-on on rejection,
UI creation and the existing audio flow. Full Torch/Whisper acceptance testing on
Linux and Windows frozen builds and Snap remains necessary: matching Python minor
versions does not alone guarantee native ABI/OS library compatibility, availability
of dynamically imported modules in a frozen runtime, CUDA compatibility, or network
access under Snap confinement. This change does not claim those platform tests passed.

uv command reference: https://docs.astral.sh/uv/reference/cli/
