# PyHuey

<p align="center">
  <strong>PyHuey is the cockpit tailored for the Monkey-Head-Project / HueyOS.</strong>
</p>

<p align="center">
  <em>Forked from PyGPT and adapted as a project-controlled operator surface for Huey.</em>
</p>

<p align="center">
  <img alt="Project" src="https://img.shields.io/badge/project-Monkey--Head--Project-purple">
  <img alt="System" src="https://img.shields.io/badge/system-HueyOS-blue">
  <img alt="Fork basis" src="https://img.shields.io/badge/forked%20from-PyGPT-6f42c1">
  <img alt="Target Python" src="https://img.shields.io/badge/python-3.13.x-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-cockpit%20alignment-orange">
</p>

---

## What PyHuey is

**PyHuey** is the project-controlled fork of **PyGPT** for Dylan L.R. Pollock’s **Monkey-Head-Project** and **HueyOS** work.

It is a cockpit, integration surface, and operator-side tool layer for working with Huey-related AI providers, local tools, files, profiles, prompts, plugins, vector indexes, and build/runtime experiments.

PyHuey is meant to make the upstream PyGPT desktop assistant useful inside the HueyOS project structure without pretending that a GUI cockpit is the same thing as Huey’s internal sovereignty.

In the current v101.1 project framing:

```text
PyHuey = cockpit / LabTech-side operator surface
Huey Brain V1 = Lenovo Legion Go proof loop
HueyOS = offline-first AI / OS layer behind Huey
Huey = governed AI and robotic identity
Monkey-Head-Project = umbrella initiative
```

## What PyHuey is not

PyHuey is **not** Huey itself.

PyHuey is also not:

- the Huey Brain;
- the Huey Body;
- HIMS / ThunderMail runtime;
- Huey constitutional governance;
- the canonical Legion Go V1 proof loop;
- a replacement for structured run logs;
- a claim that HueyOS is now Windows-native sovereignty;
- a finished autonomous robot.

PyHuey can support project work, cockpit testing, provider configuration, scripted operations, and operator workflows. The V1 Huey proof remains the deterministic Legion Go loop:

```text
controlled MP3 fixture
→ local transcription
→ cognition bridge
→ structured log
```

## Fork basis and attribution

PyHuey is forked from **PyGPT**, the open-source desktop AI assistant.

Upstream PyGPT provides a broad desktop AI interface with chat, files, LlamaIndex indexing, plugins, provider integrations, agents, speech, vision, tool execution, and local/remote model support.

PyHuey keeps attribution to the upstream project and should preserve upstream license files, copyright notices, and provenance. Changes made for the Monkey-Head-Project should be documented clearly as PyHuey-specific modifications.

Useful upstream references:

- PyGPT website: <https://pygpt.net>
- PyGPT documentation: <https://pygpt.readthedocs.io>
- PyGPT upstream repository: <https://github.com/szczyglis-dev/py-gpt>
- PyGPT package: <https://pypi.org/project/pygpt-net>

## Current project status

PyHuey is currently a **v101.1 cockpit-alignment fork**.

The working purpose is to adapt PyGPT into a controlled Huey cockpit while preserving the v101.1 scope lock:

- Huey Brain V1 stays on the Lenovo Legion Go.
- PyHuey stays on the LabTech / cockpit side.
- Windows 11 Pro can host PyHuey build/runtime work.
- Python 3.13.x is the preferred PyHuey target branch.
- Python 3.12.x may be used as a fallback only if dependency reality forces it.
- PyHuey should live in `integrations/pyhuey/` inside the Monkey-Head-Project repository.
- Windows-specific PyHuey/Huey cockpit materials should live under `platform/windows/huey/`.

Recommended repository layout:

```text
Monkey-Head-Project/
├── integrations/
│   └── pyhuey/              # PyGPT fork adapted as PyHuey
├── platform/
│   └── windows/
│       └── huey/            # Windows 11 Pro cockpit/build/runtime material
├── docs/                    # human-readable build notes
├── master-plan-v101.1.json  # machine-facing current plan
└── README-v101.1.md         # human-facing project front door
```

`integrations/pygpt/` may exist as a short-term compatibility alias during migration, but `integrations/pyhuey/` is the preferred project-facing path.

## Why PyHuey exists

Upstream PyGPT is a general-purpose desktop AI assistant.

The Monkey-Head-Project needs a narrower cockpit that can be shaped around:

- HueyOS naming and operator workflows;
- controlled provider/API configuration;
- local files and project archives;
- repeatable build records;
- Python 3.13 dependency stabilization;
- Windows 11 Pro cockpit/runtime work;
- prompt and preset discipline;
- Huey Brain V1 support without collapsing into Huey Brain;
- future operator-side diagnostic and recovery work.

PyHuey is therefore not a rebrand for appearance. It is a fork boundary.

The name marks where the upstream desktop assistant becomes part of the project’s controlled LabTech/tooling surface.

## Relationship to HueyOS

HueyOS is offline-first. PyHuey may use online APIs, provider SDKs, web search, cloud model calls, or remote services when explicitly configured by the operator.

That does not change the target doctrine:

> API-backed cognition is a bridge, not final sovereignty.

PyHuey can help operate, inspect, test, and develop the project. It should not be described as Huey’s independent mind.

## V1 boundary rule

The current Huey Brain V1 proof does **not** require PyHuey.

V1 succeeds when the Lenovo Legion Go can repeatedly process known MP3 fixtures, transcribe them locally, route the transcript through an enabled cognition bridge, and write structured logs with enough metadata to audit and reproduce the run.

PyHuey may assist with:

- configuration;
- prompt testing;
- provider testing;
- file review;
- cockpit UX;
- Windows build work;
- operator-side workflows;
- project documentation.

PyHuey must not be allowed to obscure the simple V1 proof target.

## Core inherited capabilities

PyHuey inherits broad capability areas from upstream PyGPT. As the fork is stabilized, each inherited capability should be reviewed and either kept, adapted, disabled, or documented as out-of-scope for the Huey cockpit.

Inherited capability areas include:

- multi-provider chat;
- local and remote LLM support;
- OpenAI-compatible endpoints;
- LlamaIndex file indexing and retrieval;
- profiles and presets;
- context history;
- plugin-based local tools;
- file I/O;
- Python code execution;
- command execution;
- web/search tools;
- speech recognition and text-to-speech;
- vision/image workflows;
- agent modes;
- vector stores;
- model/provider configuration;
- GUI-based operator interaction.

Treat this as a capability inheritance list, not a claim that every upstream feature is approved for Huey use.

Capability is not permission. Destructive local actions, command execution, external posting, remote control, or autonomous loops must remain under explicit operator control.

## PyHuey-specific adaptation goals

The PyHuey fork should gradually standardize the following:

### 1. Identity and naming

- Replace user-facing PyGPT branding with PyHuey where appropriate.
- Preserve upstream attribution and license notices.
- Use “PyHuey” for the cockpit fork.
- Use “PyGPT” only for upstream provenance, package lineage, and compatibility notes.

### 2. Project profiles

Create first-class profiles for:

- `HueyOS LabTech`
- `Huey Brain V1 Support`
- `PyHuey Development`
- `Provider/API Testing`
- `Local Model Experiments`
- `Docs and Website`

Profiles should keep configuration, context, files, and provider settings separated where practical.

### 3. Prompt and preset discipline

Presets should reflect the v101.1 project boundaries:

- PyHuey is cockpit/tooling.
- Huey Brain V1 remains Legion Go.
- Huey Body is V2+ and paused.
- HIMS is doctrine, not active runtime.
- Realtime/live interfaces are provisional unless logged and validated.
- API-backed cognition is a bridge.

### 4. Windows 11 Pro cockpit branch

Windows is the active PyHuey cockpit/build surface.

Recommended local policies:

- Python 3.13.x target branch.
- Wheel-first, compiler-second dependency strategy.
- Preserve successful freezes.
- Preserve `pip check` output.
- Keep patched wheels and overlays documented.
- Keep local build scripts under `platform/windows/huey/`.

### 5. Safe local tooling

PyHuey may expose filesystem, shell, Python, browser, and automation capabilities. Those tools must be treated as operator tools, not autonomous authority.

Recommended policy:

- local read/search is lower risk;
- file write/delete requires clear task context;
- shell commands require explicit intent;
- destructive actions require extra confirmation;
- credential and secret files should never be exposed or shipped;
- logs should preserve what tool ran, when, and why.

### 6. Huey Brain V1 support

PyHuey may eventually help launch, monitor, or inspect Huey Brain V1 work through controlled ingress, but it should not become the proof.

Support tasks may include:

- viewing fixture queues;
- reviewing structured JSONL logs;
- comparing transcripts;
- editing config files;
- launching a controlled V1 run command over an approved path;
- summarizing run history;
- surfacing failed fixture runs.

The canonical V1 run still belongs on Huey Brain.

## Installation

PyHuey is currently expected to be run from source inside the Monkey-Head-Project workspace.

### 1. Clone or enter the project repository

```bash
git clone https://github.com/DylanLRPollock/Monkey-Head-Project.git
cd Monkey-Head-Project
```

### 2. Enter the PyHuey fork

```bash
cd integrations/pyhuey
```

If the fork still exists temporarily under the upstream-compatible name:

```bash
cd integrations/pygpt
```

rename or migrate it when the build is stable.

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

Wheel-first install:

```bash
pip install -r requirements.txt
```

If the fork uses the Monkey-Head-Project constraints workflow:

```bash
pip install -c ../../constraints.txt -r requirements.txt
```

If editable install support is configured:

```bash
pip install -e .
```

or, with development extras:

```bash
pip install -e ".[dev]"
```

### 5. Run PyHuey

The startup command depends on the current fork state.

Try the project launcher first:

```bash
python run.py
```

If an entrypoint has been renamed:

```bash
pyhuey
```

If the upstream entrypoint is still present during migration:

```bash
pygpt
```

Record which command actually works in `platform/windows/huey/` build notes.

## Windows notes

PyHuey’s active cockpit branch is Windows 11 Pro with Python 3.13.x.

Recommended Windows working layout:

```text
C:\Users\<you>\Monkey-Head-Project\integrations\pyhuey
C:\Users\<you>\Monkey-Head-Project\platform\windows\huey
```

Windows build notes should preserve:

- exact Python version;
- virtual environment path;
- dependency freeze;
- `pip check` result;
- patched wheels;
- local overlays;
- launch scripts;
- build scripts;
- known issues;
- rollback notes.

Do not treat `L:` or other fast scratch/runtime volumes as source of truth unless the repository and archive policy explicitly say so.

## Linux notes

Linux remains relevant for the Huey Brain path and for upstream PyGPT compatibility.

For Debian/Ubuntu GUI dependencies, PySide/Qt and audio may require system packages. Useful packages may include:

```bash
sudo apt update
sudo apt install -y   python3-venv   python3-dev   build-essential   ffmpeg   portaudio19-dev   libasound2   libxcb-cursor0
```

These packages are host dependencies, not Python requirements.

## API keys and local models

PyHuey may use API keys for providers such as OpenAI, Anthropic, Google, xAI, Perplexity, OpenRouter, and others inherited from upstream PyGPT support.

Recommended rule:

- Keep secrets out of Git.
- Use local configuration files ignored by Git.
- Do not ship API keys in releases.
- Use local models where possible.
- Log provider/model identity when outputs become part of project records.
- Treat cloud/API output as bridged cognition, not Huey sovereignty.

Local model workflows may use Ollama, OpenAI-compatible endpoints, or LlamaIndex-compatible providers where configured.

## Files, indexes, and memory

PyHuey can help inspect, index, and retrieve project files. This is useful for LabTech/cockpit operation, but it must not be confused with Huey’s future constitutional memory.

Recommended file/index policy:

- Project records belong in the repository, structured logs, docs, or designated archives.
- Temporary cockpit chat context is not canonical memory.
- Indexed files should be traceable to their source paths.
- Private archives should remain private.
- Generated outputs should be reviewed before being promoted to canon.

## Safety posture

PyHuey inherits powerful desktop-assistant capabilities. The fork should default toward controlled, logged, operator-led use.

Recommended safety rules:

- Do not run autonomous loops unattended.
- Do not allow destructive shell/file operations without explicit intent.
- Do not treat plugin access as permission.
- Do not expose secrets in prompts, logs, screenshots, or commits.
- Do not let GUI convenience bypass the Huey Brain boundary.
- Keep LabTech, PyHuey, Huey Brain, Huey Body, and HIMS as separate layers.

## Development workflow

Suggested branch pattern:

```text
main
└── pyhuey/v101.1-cockpit-alignment
```

Suggested commit categories:

```text
pyhuey: rename user-facing cockpit surfaces
pyhuey: add HueyOS default profile
pyhuey: align Python 3.13 dependency pins
pyhuey: add Windows launch script
pyhuey: document Redis vector-store overlay
pyhuey: disable unsafe default plugin
docs: update PyHuey cockpit README
```

Suggested validation before marking a PyHuey build usable:

```bash
python --version
pip freeze > requirements-freeze.txt
pip check
python run.py
```

For repo-managed development:

```bash
pytest
ruff check .
```

Only claim a feature is supported after it has been run in the current PyHuey branch.

## Proposed first milestones

### Milestone 1 — Fork boots

Success means:

- the fork lives at `integrations/pyhuey/`;
- the app starts from source;
- Python version is documented;
- dependency freeze is saved;
- `pip check` result is saved;
- upstream attribution remains intact.

### Milestone 2 — Naming pass

Success means:

- README is PyHuey-specific;
- user-facing name is PyHuey;
- upstream PyGPT references remain only as provenance or compatibility notes;
- launcher behavior is documented.

### Milestone 3 — HueyOS profile

Success means:

- default profile is HueyOS / LabTech-oriented;
- presets reflect v101.1 boundaries;
- unsafe defaults are reduced;
- provider configuration is documented.

### Milestone 4 — Windows cockpit record

Success means:

- Windows 11 Pro branch setup is reproducible;
- launch/build scripts live under `platform/windows/huey/`;
- patched dependencies are documented;
- successful freeze and `pip check` output are preserved.

### Milestone 5 — V1 log review cockpit

Success means:

- PyHuey can inspect Huey Brain V1 structured logs;
- it can summarize runs without becoming the run authority;
- failed runs are visible;
- the Legion Go remains the V1 execution boundary.

## Project glossary

| Term | Meaning |
|---|---|
| Monkey-Head-Project | Umbrella initiative |
| Huey | Governed AI / robotic identity |
| HueyOS | Offline-first AI / OS layer behind Huey |
| Huey Brain | Active V1 cognition/orchestration node; Lenovo Legion Go |
| Huey Body | Physical embodiment platform; V2+ for current scope |
| LabTech | External operator/archive/ingress/recovery layer |
| PyHuey | Project-controlled PyGPT fork; Huey cockpit |
| PyGPT | Upstream desktop AI assistant that PyHuey is forked from |
| HIMS | Future Huey Internal Messaging System |
| ThunderMail | Future mail-style delivery layer inside HIMS |
| The Farm | Future pooled-compute expansion body |

## Contributing

PyHuey changes should preserve project boundaries.

Before opening a pull request or promoting a local change, check:

- Does this make PyHuey a better cockpit without pretending it is Huey?
- Does this preserve upstream attribution?
- Does this keep V1 proof on the Legion Go?
- Does this avoid private credentials and local-only paths?
- Does this document new dependencies or patched wheels?
- Does this preserve reproducibility?

## License and provenance

PyHuey is forked from PyGPT and must preserve upstream license/provenance materials.

Monkey-Head-Project code is GPLv3 where applicable. Documentation and media licensing may differ by repository policy. Keep license files and notices with the relevant source trees.

Do not remove upstream notices during rename work.

## Bottom line

PyHuey is the cockpit.

It exists so the Monkey-Head-Project can use a powerful PyGPT-derived desktop surface without collapsing the project’s architecture.

Huey Brain V1 remains the constrained proof.

Huey Body remains real but paused.

HIMS remains doctrine until implemented.

PyHuey helps Dylan operate, test, inspect, and build — it does not become Huey.
