# Contributing to PyHuey

**Project:** PyHuey  
**Parent project:** Monkey-Head-Project / HueyOS  
**Fork basis:** PyGPT  
**Current alignment:** v101.1 — PyHuey cockpit alignment  
**Maintainer:** Dylan L.R. Pollock

Thank you for your interest in contributing.

PyHuey is the cockpit tailored for the **Monkey-Head-Project / HueyOS**. It is forked from **PyGPT** and adapted as a project-controlled operator, build, and integration surface for Huey.

This document explains how to contribute safely and coherently while preserving the boundaries of the project.

---

## Quick checklist

Before submitting a change:

- Use **Python 3.13.x** as the normal PyHuey target branch.
- Keep **Python 3.12.x** as fallback only when dependency reality forces it.
- Work from an isolated virtual environment.
- Keep PRs focused and reviewable.
- Preserve upstream PyGPT attribution and license/provenance files.
- Add or update tests when behavior changes.
- Update docs when users, operators, or contributors will notice the change.
- Do not commit secrets, local profiles, API keys, context databases, private logs, or local scratch output.
- Keep PyHuey framed as cockpit/tooling, not Huey Brain, HIMS, Huey Body, or Huey sovereignty.

---

## What PyHuey is

PyHuey is a PyGPT-derived cockpit for the Monkey-Head-Project / HueyOS.

It may support:

- desktop AI cockpit workflows;
- provider/API testing;
- local model and Ollama-style experiments;
- project profiles and presets;
- LlamaIndex/vector-store work;
- file review and archive navigation;
- controlled operator-side tools;
- Windows 11 Pro build/runtime work;
- documentation and release-support workflows.

PyHuey is not:

- Huey itself;
- Huey Brain;
- Huey Body;
- HIMS / ThunderMail;
- constitutional governance runtime;
- the canonical Legion Go V1 proof loop;
- a finished autonomous robot.

The current Huey Brain V1 proof remains:

```text
controlled MP3 fixture
→ local transcription
→ cognition bridge
→ structured log
```

PyHuey can help inspect, configure, test, and operate around that loop. It must not obscure or replace it.

---

## Repository layout

Preferred v101.1 layout:

```text
Monkey-Head-Project/
├── integrations/
│   └── pyhuey/              # PyGPT fork adapted as PyHuey
├── platform/
│   └── windows/
│       └── huey/            # Windows 11 Pro cockpit/build/runtime material
├── docs/                    # project documentation
├── master-plan-v101.1.json  # machine-facing current project plan
└── README-v101.1.md         # human-facing project front door
```

`integrations/pygpt/` may exist briefly as a compatibility alias during migration, but `integrations/pyhuey/` is the preferred project-facing path.

Do not put Windows cockpit code under `platform/windows/hueybody/`. `Huey Body` is the physical embodiment term. Windows cockpit code belongs under `platform/windows/huey/`.

---

## Supported development targets

| Area | Current target |
|---|---|
| Primary cockpit OS | Windows 11 Pro |
| Python target | Python 3.13.x |
| Python fallback | Python 3.12.x only if needed |
| Linux baseline | Debian 14 “Forky” target language for HueyOS-aligned docs/runtime notes |
| Fork path | `integrations/pyhuey/` |
| Windows path | `platform/windows/huey/` |

PyHuey may still run on Linux/macOS where inherited PyGPT compatibility supports it, but the active project cockpit branch is Windows 11 Pro + Python 3.13.

---

## Development setup

### 1. Clone the project

```bash
git clone https://github.com/DylanLRPollock/Monkey-Head-Project.git
cd Monkey-Head-Project
```

### 2. Enter the PyHuey fork

```bash
cd integrations/pyhuey
```

If the fork has not yet been renamed in your local checkout:

```bash
cd integrations/pygpt
```

Document which path you used in your PR if it matters.

### 3. Create a virtual environment

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

Linux/macOS shell:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

### 4. Install dependencies

For a normal PyHuey cockpit install:

```bash
pip install -r requirements.txt
```

If a project constraint file is used from the repository root:

```bash
pip install -c ../../constraints.txt -r requirements.txt
```

If editable install support is configured:

```bash
pip install -e .
```

For development extras, where available:

```bash
pip install -e ".[dev]"
```

### 5. Confirm the environment

```bash
python --version
pip check
```

Save dependency freeze and check output when contributing to dependency or build changes:

```bash
pip freeze > requirements-freeze.txt
pip check > pip-check.txt
```

---

## Running PyHuey

The launch command depends on the current fork state.

Try:

```bash
python run.py
```

If a PyHuey entrypoint exists:

```bash
pyhuey
```

If the upstream PyGPT entrypoint is still present during migration:

```bash
pygpt
```

Record the working command in `platform/windows/huey/` build notes when changing launch behavior.

---

## Contributing changes

Contributions may include:

- bug fixes;
- PyHuey rename/migration work;
- dependency and Python 3.13 compatibility fixes;
- Windows cockpit/build scripts;
- profiles, presets, and safe default configuration;
- docs and Read the Docs improvements;
- tests and CI fixes;
- security hardening;
- PyGPT upstream merge/rebase work;
- provider, vector-store, and plugin integration cleanup.

Keep each pull request focused. Avoid mixing a rename pass, dependency upgrade, GUI change, security change, and docs rewrite in one PR.

---

## Git workflow

Use short, descriptive branches:

```text
feat/pyhuey-profile
fix/windows-launch
fix/bandit-tool-manager
docs/readthedocs-forky
chore/python313-freeze
refactor/provider-boundary
test/plugin-permissions
```

Use Conventional Commits:

```text
feat(pyhuey): add HueyOS default profile
fix(windows): repair Python 3.13 launch script
docs(readme): clarify PyHuey cockpit boundary
chore(deps): update Redis vector-store overlay notes
security(tools): log subprocess failures
test(profiles): cover profile isolation
```

Prefer small commits that can be reviewed independently.

---

## Pull requests

A good PR should include:

- clear title using Conventional Commit style;
- summary of what changed;
- why the change is needed;
- risk notes;
- test commands run;
- screenshots for visible GUI changes;
- docs updates where relevant;
- note about upstream PyGPT provenance if upstream files were modified;
- note about any dependency freeze changes;
- note about any security implications.

### PR checklist

Before requesting review:

- [ ] The PR has one main purpose.
- [ ] The branch name is clear.
- [ ] Commit messages are readable.
- [ ] Tests pass or skipped tests are explained.
- [ ] `pip check` passes where dependencies changed.
- [ ] No secrets are included.
- [ ] No private profiles, context DBs, logs, or local scratch files are included.
- [ ] Docs are updated for user-facing changes.
- [ ] Security-sensitive behavior is called out.
- [ ] Upstream PyGPT license/provenance files remain intact.

---

## Bug reports

Use GitHub Issues for non-security bugs.

A good bug report includes:

- short summary;
- PyHuey version, branch, commit, or freeze;
- install method;
- OS and version;
- Python version;
- relevant package versions from `pip list` or `pip freeze`;
- whether this is source, compiled, or packaged;
- steps to reproduce;
- expected behavior;
- actual behavior;
- logs with secrets redacted;
- screenshots for GUI issues;
- whether the issue also exists in upstream PyGPT, if known.

Do not include API keys, OAuth tokens, SSH keys, cookies, `.env` files, private context databases, or full private logs.

---

## Security reports

Do not open public issues for vulnerabilities.

Use:

- GitHub Private Vulnerability Report, if available; or
- email: `admin@dlrp.ca`
- subject: `VULN: PyHuey — <short title>`

Security-relevant areas include:

- command execution;
- Python execution;
- file write/delete/move;
- plugin permissions;
- provider/API key handling;
- profile export/import;
- context and index leakage;
- vector-store integration;
- unsafe local wheel or dependency behavior;
- release artifact leaks;
- unsafe defaults.

Follow `SECURITY.md` for the full policy.

---

## Secrets and local files

Never commit:

- `.env` files;
- API keys;
- OAuth tokens;
- SSH keys;
- cookies;
- local provider configs;
- private profiles;
- context databases;
- private chat logs;
- generated local indexes;
- private Atlas transcripts;
- local scratch archives;
- Windows user paths containing private data;
- patched wheels unless intentionally added to a documented wheelhouse;
- build logs containing secrets.

When adding a new config key, add a sanitized example to `.env.example` if appropriate.

---

## Coding style

Use normal Python project hygiene:

- follow PEP 8 where practical;
- prefer readable code over clever code;
- use type hints for new public functions where reasonable;
- keep GUI, provider, plugin, and filesystem boundaries clear;
- avoid broad silent exceptions;
- log failures with useful context;
- do not add framework weight unnecessarily.

Recommended formatting/linting tools, where configured:

```bash
ruff check .
ruff format .
black .
isort .
```

Run only the tools that are actually configured for the repository or PR branch.

---

## Exception-handling standard

PyHuey inherits a large PyGPT codebase, including broad exception handlers. Do not make this worse.

Rules for new or touched code:

- Do not use silent `except Exception: pass`.
- Optional imports should catch `ImportError` or `ModuleNotFoundError`.
- File I/O should catch `OSError`, `FileNotFoundError`, `PermissionError`, or `UnicodeDecodeError` as appropriate.
- JSON/YAML parsing should catch parser-specific exceptions.
- Subprocess code should catch `OSError`, `ValueError`, `subprocess.CalledProcessError`, or `subprocess.TimeoutExpired` as appropriate.
- GUI cosmetic fallbacks may log at debug level.
- Tool execution, shell execution, file write/delete, provider/API, credential, and plugin-manager code must not silently suppress broad failures.

Preferred logging style:

```python
logger.debug("Failed to configure font %s: %s", name, exc)
```

Avoid f-string logging when lazy formatting is available:

```python
logger.debug(f"Failed to configure font {name}: {exc}")
```

---

## Bandit and security scanning

PyHuey may carry inherited PyGPT Bandit findings. Treat these as security debt, not as false success or immediate panic.

Recommended workflow:

```bash
mkdir -p .security reports/security

bandit -r src   -f json   -o .security/bandit-baseline.json
```

Then fail CI on new or serious findings:

```bash
bandit -r src   -b .security/bandit-baseline.json   -ll   -ii   -f json   -o reports/security/bandit-current.json
```

Do not claim all security findings are fixed until a fresh Bandit run confirms it.

Prioritize fixes in this order:

1. subprocess/shell/Python execution;
2. plugin and tool manager;
3. file write/delete/move;
4. provider/API key and credential handling;
5. profile/config export;
6. network/IPC surfaces;
7. GUI cosmetic fallbacks.

---

## Testing

Use pytest where tests exist:

```bash
pytest -q
```

For targeted tests:

```bash
pytest tests/test_specific_file.py -q
```

For coverage, if configured:

```bash
pytest --cov --cov-report=term-missing
```

If touching GUI code, include at least a smoke-test note:

- OS;
- Python version;
- launch command;
- screenshot or description;
- whether headless tests were possible.

If touching provider, network, or paid API paths, avoid tests that require real secrets unless explicitly designed as integration tests and documented.

---

## Documentation

Update documentation when changing:

- installation;
- launch commands;
- supported Python version;
- dependencies;
- profiles/presets;
- security behavior;
- plugin permissions;
- provider configuration;
- Read the Docs config;
- release packaging;
- Windows build steps;
- PyHuey/HueyOS terminology.

Documentation should preserve the v101.1 boundary:

> PyHuey is cockpit/tooling. Huey Brain V1 remains the Legion Go proof loop.

---

## Upstream PyGPT relationship

PyHuey is forked from PyGPT. Preserve provenance.

When modifying upstream-derived files:

- keep upstream license notices;
- document large local changes;
- prefer clean patches over untraceable rewrites;
- record upstream version/commit where possible;
- keep a changelog of PyHuey-specific divergence;
- do not remove attribution during rename work.

When pulling upstream changes, document:

- upstream commit/tag;
- merge/rebase method;
- conflicts;
- PyHuey-specific files touched;
- follow-up tasks.

---

## Dependencies and patched wheels

PyHuey uses a wheel-first, compiler-second policy.

For dependency changes:

- update `requirements.txt`;
- preserve or regenerate known-good freeze files;
- run `pip check`;
- document local wheel overlays separately;
- do not make absolute local wheel paths the only public install path;
- record why a dependency was added or pinned;
- include rollback notes for risky upgrades.

For patched wheels, document:

- package name;
- version;
- patch reason;
- build platform;
- wheel filename;
- hash;
- install command;
- upstream issue/replacement plan if any.

---

## Release notes

For user-facing changes, update the changelog or release notes.

Include:

- summary;
- affected platform;
- migration notes;
- security notes;
- dependency changes;
- known limitations;
- rollback notes when relevant.

Use clear version language:

- PyHuey v101.1 is the cockpit alignment era.
- Older v100.x/v101.0 labels are lineage or baseline unless explicitly current.
- Do not expose old labels as current.

---

## Code of conduct

Be direct, constructive, and specific.

This project values grounded implementation, continuity, honest proof, and clear boundaries. Do not overclaim capabilities. Do not present future Huey systems as active. Do not collapse PyHuey, Huey Brain, Huey Body, HIMS, LabTech, and Huey proper into one flat system.

If a disagreement is architectural, explain the layer boundary and propose a testable path.

---

## Licensing

PyHuey inherits upstream PyGPT provenance and must preserve upstream license files and notices.

Monkey-Head-Project code is GPLv3 where applicable unless a specific file says otherwise. Documentation and media may have separate licensing.

By submitting a contribution, you certify that you have the right to contribute it under the repository’s applicable license terms.

---

## Support and questions

Use GitHub Issues for bugs and feature requests.

Use GitHub Discussions, if enabled, for design proposals and general questions.

Use private vulnerability reporting for security issues.

For project-boundary questions, use the current README and master plan as the source of truth:

- PyHuey = cockpit/tooling;
- Huey Brain V1 = Legion Go deterministic proof loop;
- Huey Body = V2+ embodiment;
- HIMS = future routing/record doctrine until implemented;
- LabTech = external operator/archive/ingress layer.

Thank you for helping improve PyHuey and the Monkey-Head-Project.
