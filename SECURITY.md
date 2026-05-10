# Security Policy

**Project:** PyHuey  
**Parent project:** Monkey-Head-Project / HueyOS  
**Fork basis:** PyGPT  
**Last updated:** 2026-05-09  
**Current policy era:** v101.1 — PyHuey cockpit alignment

PyHuey takes security seriously.

PyHuey is the project-controlled cockpit fork of PyGPT for the Monkey-Head-Project / HueyOS. It is intended as a LabTech/operator-side cockpit, build surface, integration test surface, and controlled desktop tooling layer for working with Huey-related providers, files, plugins, prompts, local models, indexes, and structured project records.

PyHuey is not Huey itself, not the Huey Brain, not HIMS, not Huey constitutional governance, and not the canonical Legion Go V1 proof loop.

That distinction matters for security. PyHuey may expose powerful desktop-assistant capabilities inherited from PyGPT, including local files, plugin tools, shell or command execution, Python execution, browser/search tooling, API-provider access, attachments, indexing, vector stores, and local/remote model integrations. Those features must be treated as operator tools with explicit permission boundaries, not autonomous authority.

---

## 1. Security model

PyHuey’s security posture is based on five boundaries:

1. **Cockpit boundary** — PyHuey is an operator/cockpit surface. It may assist Dylan/LabTech, but it does not become Huey sovereignty.
2. **Local-machine boundary** — PyHuey can touch local files, profiles, settings, context databases, logs, indexes, and plugin outputs on the machine where it runs.
3. **Provider boundary** — PyHuey may call external providers when configured with API keys. API use is explicit operator configuration, not offline sovereignty.
4. **Tool boundary** — plugin access, file access, shell access, Python execution, browser access, and automation are capabilities, not permissions.
5. **Project boundary** — PyHuey must not blur the Huey Brain V1 proof boundary. The current canonical V1 proof remains: controlled MP3 fixture → local transcription → cognition bridge → structured log on Huey Brain.

PyHuey should default toward controlled, logged, operator-led use.

---

## 2. Supported versions

PyHuey currently follows the Monkey-Head-Project era model, with conventional semantic versioning used only where useful for packages, builds, or installers.

### Active support era

| Line | Status |
|---|---|
| `v101.1` | Actively supported PyHuey cockpit-alignment era |
| `v101.0` | Project baseline; critical compatibility/security fixes only where relevant |
| `< v101.0` | Unsupported unless explicitly named in an advisory |
| `main` | Fixes land here before release unless a private advisory branch is needed |

### Support window

Security support normally covers:

- the current PyHuey era line;
- the immediately previous project era line if a critical fix is practical;
- `main`, for active development fixes.

Experimental branches, local scratch builds, private patched wheels, and ad-hoc dependency freezes are not automatically supported unless they are explicitly documented as active build records.

---

## 3. Supported platforms

PyHuey’s v101.1 cockpit target is:

| Area | Supported baseline |
|---|---|
| Primary OS | Windows 11 Pro |
| Python | Python 3.13.x |
| Fallback Python | Python 3.12.x only if dependency reality forces it |
| Secondary OS | Debian/Linux where upstream PyGPT compatibility applies |
| Path policy | `integrations/pyhuey/` for the fork |
| Windows path policy | `platform/windows/huey/` for cockpit/build/runtime material |

### Out-of-scope platform claims

Do not treat this policy as claiming that:

- HueyOS now runs as Windows sovereignty;
- PyHuey replaces Huey Brain;
- PyHuey is the on-robot runtime;
- PyHuey is HIMS;
- PyHuey is the canonical V1 proof loop.

Windows hosts the cockpit, build/runtime scripts, provider tests, patched wheels, freezes, local overlays, and operator tooling.

---

## 4. Reporting a vulnerability

Please use coordinated vulnerability disclosure. Report security issues privately first.

### Preferred channel

**GitHub Private Vulnerability Report**

Repository → **Security** tab → **Report a vulnerability**

Use this when possible because it supports private discussion, patches, advisories, and CVE coordination.

### Email channel

Email: **admin@dlrp.ca**  
Subject format: `VULN: PyHuey — <short title>`

If you require encryption, state that in your first message. We can coordinate an encrypted channel before you send sensitive details.

### What to include

Please include:

- summary of the issue;
- affected PyHuey version, branch, commit, or freeze;
- operating system and Python version;
- whether the issue affects Windows, Linux, or both;
- whether the issue requires a plugin, provider, API key, local model, index, or optional dependency;
- reproduction steps or proof of concept;
- observed impact;
- relevant logs or screenshots with secrets redacted;
- whether credentials, local files, shell access, or provider accounts are exposed;
- workaround or mitigation, if known;
- preferred credit name/handle, or anonymity request.

### Do not disclose publicly first

Do not open a public GitHub issue, discussion, pull request, screenshot, video, or social post containing exploit details before coordinated disclosure has been agreed.

If the issue involves leaked credentials, active exploitation, or public exposure of a dangerous default, state that clearly in the subject line.

---

## 5. Response targets

Targets are best-effort and depend on severity, reproducibility, upstream coordination, and project capacity.

| Stage | Target |
|---|---|
| Acknowledgement | within 72 hours |
| Initial triage | within 7 calendar days |
| Critical fix or mitigation | 14–21 days |
| High fix or mitigation | 21–30 days |
| Medium fix or mitigation | 30–60 days |
| Low fix | scheduled by impact and complexity |

These are targets, not guarantees.

If active exploitation is credible, the timeline may be shortened and a mitigation may be published before a full patch.

---

## 6. Severity model

PyHuey uses CVSS v3.1 as a starting point, but final severity also depends on cockpit context.

Contextual factors include:

- whether the issue is reachable by default;
- whether it requires local desktop access;
- whether a dangerous plugin must be enabled;
- whether command execution or file write access is involved;
- whether secrets or provider keys are exposed;
- whether the issue affects packaged builds, source installs, or only local custom builds;
- whether PyHuey can reach Huey Brain or project infrastructure through operator-configured paths;
- whether the issue can cause data loss or unauthorized external actions.

| Severity | CVSS range |
|---|---|
| Critical | 9.0–10.0 |
| High | 7.0–8.9 |
| Medium | 4.0–6.9 |
| Low | 0.1–3.9 |

---

## 7. Scope

### In scope

Security reports are in scope when they affect PyHuey or its documented project integration, including:

- PyHuey source code and project-specific modifications;
- PyHuey packaging, launch scripts, build scripts, installer scripts, and runtime wrappers;
- `integrations/pyhuey/`;
- `platform/windows/huey/`;
- project-maintained PyHuey profiles, presets, prompts, plugins, and defaults;
- patched wheels or local overlays distributed or documented by the project;
- configuration examples shipped with PyHuey;
- unsafe defaults in project documentation;
- local file, shell, Python, browser, plugin, automation, or command-execution behavior exposed through PyHuey;
- secrets/API key handling;
- context databases, index stores, vector stores, file attachments, and generated outputs;
- update, artifact, release, or dependency integrity for PyHuey packages;
- Redis/vector-store integration when shipped or documented by the project;
- accidental bundling of private profiles, context history, API keys, logs, or archives.

### Out of scope

The following are normally out of scope:

- pure upstream PyGPT vulnerabilities with no PyHuey-specific change;
- pure upstream dependency vulnerabilities with no PyHuey-default exposure;
- vulnerabilities in Windows, Debian, Python, Qt/PySide, drivers, firmware, kernels, or third-party services;
- user-added provider keys, plugins, scripts, models, or local tools not shipped or recommended by PyHuey;
- social engineering;
- phishing;
- attacks requiring unreasonable physical access;
- denial-of-service that requires unrealistic resources and has no practical mitigation;
- reports based only on version banners or non-sensitive metadata;
- deployment misconfiguration outside documented recommendations.

### Upstream caveat

If an upstream PyGPT or dependency issue becomes exploitable through PyHuey defaults, project patches, documented PyHuey workflows, shipped overlays, or release artifacts, report it to us too. We may coordinate pinning, mitigation, documentation, or patched releases while upstream handles the root fix.

---

## 8. Vulnerability classes we prioritize

PyHuey prioritizes issues involving:

### Credential and secret exposure

- API keys written to logs, screenshots, exported contexts, release artifacts, or crash dumps;
- secrets committed to the repository;
- provider tokens exposed through prompts, debug output, plugin traces, or profile exports;
- unsafe backup/export behavior.

### Local code execution and command abuse

- unintended shell execution;
- unsafe subprocess calls;
- command injection through prompts, filenames, documents, model responses, plugin parameters, or tool routing;
- Python code execution without clear operator approval;
- plugin privilege escalation.

### File-system attacks

- path traversal;
- unsafe file writes outside the intended workspace;
- deletion or overwrite of user files;
- symlink/hardlink attacks;
- insecure temp files;
- unsafe file permissions for secrets, profiles, logs, indexes, and context databases.

### Plugin and tool boundary failures

- tools running when disabled;
- missing confirmation for destructive actions;
- plugin permission bypass;
- unsafe remote tool behavior;
- model-triggered tool calls that exceed operator intent.

### Prompt, context, and data exposure

- private context leakage across profiles;
- unsafe context export;
- sensitive data included in generated diagnostics;
- cross-profile contamination;
- RAG/index leakage from private archives;
- prompt injection causing unauthorized tool use.

### Provider and API safety

- API key mishandling;
- unintended calls to paid providers;
- provider switching without operator awareness;
- logging provider secrets;
- unsafe handling of OpenAI-compatible endpoints or local endpoints.

### Supply chain and artifact integrity

- tampered requirements or wheels;
- unsafe local wheel references shipped as public requirements;
- compromised release archives;
- missing hashes where hashes are expected;
- dependency confusion;
- installer or build script compromise.

### Network and IPC exposure

- local HTTP servers bound to public interfaces unexpectedly;
- unauthenticated admin routes;
- insecure websocket or IPC endpoints;
- unsafe default ports;
- local service discovery exposing cockpit data.

---

## 9. PyHuey tool-safety rules

PyHuey may expose powerful tools. The following rules apply to project-maintained defaults:

1. **Read before write** — file read/search is lower risk than writing, moving, deleting, or executing.
2. **No silent destructive actions** — delete, overwrite, recursive move, wipe, format, credential rotation, package uninstall, and shell operations need explicit operator intent.
3. **No autonomous escalation** — autonomous/agent loops must not gain new tool permissions during execution.
4. **No hidden exfiltration** — files, prompts, logs, contexts, and indexes must not be sent to providers or external services without configuration and operator awareness.
5. **No credential echo** — API keys, tokens, cookies, private keys, SSH keys, OAuth refresh tokens, and `.env` content must not be printed in normal logs.
6. **No private archive leakage** — Atlas transcripts, private logs, profiles, context DBs, and local archives must not ship in public packages.
7. **Log dangerous operations** — shell execution, Python execution, file writes, provider calls, and remote operations should be auditable where practical.
8. **Keep Huey boundaries intact** — PyHuey must not bypass Huey Brain to control Huey Body or future robot actuation.

---

## 10. Safe Harbor

We support good-faith security research.

As long as you:

- comply with applicable laws;
- use private reporting channels;
- avoid accessing, modifying, deleting, or exfiltrating data beyond what is necessary to prove impact;
- avoid degrading availability for others;
- do not run large-scale denial-of-service tests against shared infrastructure;
- do not publish exploit details before coordination;
- securely delete sensitive material after reporting;
- give us reasonable time to investigate and remediate;

we will not initiate legal action against you solely for good-faith research on PyHuey.

If you are unsure whether a planned test is safe, contact us first.

---

## 11. Coordinated disclosure and embargo

Default embargo window: **90 days from acknowledgement**.

The window may be shortened if:

- the issue is actively exploited;
- secrets are already exposed;
- public exposure is likely;
- a safe mitigation is available;
- the vulnerability is trivial to exploit in default configurations.

The window may be extended by mutual agreement if:

- upstream coordination is required;
- the fix requires architectural changes;
- multiple packages or platforms need coordinated patches;
- reporter and maintainer agree that more time protects users.

Advisories should be published through GitHub Security Advisories when applicable.

For qualifying issues, we may request a CVE.

Reporter credit is optional and may be anonymous or pseudonymous.

---

## 12. Fix, backport, and release policy

When a vulnerability is confirmed:

1. reproduce the issue in a controlled environment;
2. classify severity and affected surfaces;
3. create a private advisory branch if needed;
4. patch `main` first unless release secrecy requires a different path;
5. backport to supported lines where practical;
6. update tests or validation scripts;
7. update documentation and operator guidance;
8. cut a security release or publish mitigation notes;
9. publish an advisory when users have a reasonable path to protect themselves.

A security release should include:

- summary of the issue;
- affected versions/builds;
- fixed versions/builds;
- mitigation steps;
- whether secrets should be rotated;
- whether profiles, logs, indexes, or context DBs should be inspected;
- known limitations;
- reporter credit if approved.

---

## 13. Credential and secret exposure response

If credentials are exposed:

1. confirm the exposure privately;
2. remove the exposed material from active release artifacts;
3. revoke or rotate affected secrets within 24 hours of confirmation where feasible;
4. identify whether users must rotate their own keys;
5. publish clear mitigation guidance if users are affected;
6. audit adjacent artifacts for repeated leakage;
7. preserve enough internal record to understand the incident without redistributing the secret.

Secret types include:

- OpenAI, Anthropic, Google, xAI, Perplexity, OpenRouter, Azure, AWS, and other provider API keys;
- OAuth tokens and refresh tokens;
- SSH keys;
- cookies;
- `.env` files;
- private certificates;
- local service tokens;
- database passwords;
- Redis credentials;
- CI tokens;
- packaged user profiles containing secrets.

---

## 14. Dependency and supply-chain policy

PyHuey uses a wheel-first, compiler-second dependency policy for the Windows cockpit branch.

Security expectations:

- keep pinned requirements files for reproducibility;
- preserve known-good freezes;
- preserve `pip check` records;
- document patched wheels and local overlays;
- do not ship absolute local wheel paths as the only public install path;
- do not publish private wheelhouse paths in public docs unless intentionally sanitized;
- keep hashes when using lockfiles that require hashes;
- do not include private credentials in wheels, build logs, or release archives;
- review dependency upgrades that affect tool execution, networking, provider access, browser automation, vector stores, or file handling.

If a patched local wheel is required, document:

- source package name and version;
- patch reason;
- build machine/platform;
- wheel hash;
- install command;
- rollback path;
- upstream issue or replacement plan if applicable.

---

## 15. Public release artifact policy

A public PyHuey release must not include:

- `.env` files;
- API keys;
- SSH keys;
- cookies;
- OAuth tokens;
- private profiles;
- context databases;
- private chat logs;
- unreviewed Atlas transcripts;
- local scratch folders;
- absolute local path leaks where avoidable;
- Windows user directories with personal information;
- test output containing secrets;
- private build notes unless sanitized;
- non-public Huey archives.

Before release, run:

```bash
python --version
pip check
python -m compileall .
```

Recommended additional checks:

```bash
git status --short
git diff --check
grep -RIn --exclude-dir=.git --exclude-dir=.venv "sk-" .
grep -RIn --exclude-dir=.git --exclude-dir=.venv "api_key\|secret\|token\|password" .
```

Treat grep output as a review queue, not automatic proof of leakage.

---

## 16. Development hardening practices

PyHuey development should follow these practices:

- least privilege by default;
- secure profile defaults;
- explicit tool permission boundaries;
- careful prompt/preset handling;
- separation between profiles and workspaces;
- no credential logging;
- no private archive bundling;
- reproducible requirements and freezes;
- documented patched wheels;
- dependency review for high-risk packages;
- private security branches when needed;
- regression tests for fixed vulnerabilities where practical;
- clear release notes for security fixes;
- simple rollback guidance.

---

## 17. Example vulnerability report

```text
Subject: VULN: PyHuey — <short title> — impact <Critical/High/Medium/Low>

Product: PyHuey
Parent project: Monkey-Head-Project / HueyOS
Affected version/commit/freeze: <version, branch, commit, or requirements freeze>
Environment: <Windows/Linux/macOS, Python version, install method>

Summary:
<one-paragraph description of the issue and security impact>

Reproduction:
<step-by-step commands, UI steps, payloads, files, or proof of concept>

Impact:
<what an attacker or malicious input can do>

Prerequisites:
<plugin enabled, API key configured, local model running, file opened, index built, etc.>

Suggested mitigation:
<optional>

Sensitive data exposure:
<yes/no/unknown; describe with secrets redacted>

Reporter credit:
<name/handle/link or anonymous>
```

---

## 18. Contact

Security reports: **admin@dlrp.ca**  
Preferred private channel: GitHub Private Vulnerability Report  
Public issues: only after coordinated disclosure or for non-sensitive hardening/documentation work.

---

## 19. Bottom line

PyHuey is the cockpit.

It is powerful because it inherits desktop AI, file, plugin, provider, and automation capabilities from PyGPT. That power must be bounded.

PyHuey helps Dylan operate, inspect, test, and build the Monkey-Head-Project. It must not silently become Huey’s authority, bypass Huey Brain, leak secrets, or turn cockpit convenience into uncontrolled autonomy.
