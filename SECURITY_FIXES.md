# PYGPT — Issues Raised & How They Were Fixed

This document lists the issues identified during the audit of the py-gpt codebase, and the fixes applied to resolve them. All changes affect files under `src/pygpt_net/`.

---

## 1. BUG-001: Shell Injection in Custom Commands (Critical)

**Where:** `plugin/cmd_custom/worker.py`

**Issue:** User/LLM-supplied parameter values were interpolated directly into a command string that was executed with `subprocess.Popen(cmd, shell=True)`. A malicious parameter value containing shell metacharacters (`;`, `|`, `&&`, backticks, etc.) could execute arbitrary commands on the host.

```python
cmd = cmd.replace("{" + param["name"] + "}", str(item["params"][param["name"]]))
```

**Fix:**
- Parameter values are now passed through a platform-aware quote helper (`_quote_param`) so shell metacharacters are neutralized before the command is executed.
- POSIX shells (Linux/macOS) use `shlex.quote()`. **Windows `cmd.exe` does not understand POSIX single-quote quoting**, so on Windows the helper uses `subprocess.list2cmdline()` (Windows command-line quoting) instead.

```python
def _quote_param(value: str) -> str:
    if _IS_WINDOWS:            # os.name == "nt"
        return subprocess.list2cmdline([value])
    return shlex.quote(value)
```

> Why not `shlex.quote()` everywhere? On Windows, `shlex.quote()` wraps the value in `'...'`, which `cmd.exe` does not recognize — the literal quote characters would end up in the command and break it. `subprocess.list2cmdline()` produces cmd.exe-compatible quoting.

---

## 2. BUG-002: SSL Verification Disabled in File Downloads

**Where:** `plugin/cmd_files/worker.py`

**Issue:** `download_file` created an SSL context with `check_hostname = False` and `verify_mode = ssl.CERT_NONE`, disabling TLS certificate validation. This allowed man-in-the-middle attacks on files the assistant downloads from URLs.

```python
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
```

**Fix:**
- Removed the insecure flags; the download now uses a standard `ssl.create_default_context()` which verifies certificates.
- Also pulled the download timeout from 5s to 30s so large files are not spuriously rejected.
- Replaced `shutil.copyfileobj` with an explicit 1 MiB chunked read that validates `Content-Length` and rejects truncated downloads.

---

## 3. BUG-003: Global `OPENAI_API_KEY` Environment Pollution

**Where:** `provider/llms/ollama.py` (and, discovered later, `provider/llms/mistral.py`)

**Issue:** When no OpenAI API key was configured, the local-embeddings init wrote a fake key into the **process-global** environment:

```python
os.environ['OPENAI_API_KEY'] = "_"
```

This leaked into any subsequent OpenAI API calls in the same process, corrupting them. The same bug existed in `mistral.py`.

**Fix:**
- Removed the `os.environ` mutation from both `ollama.py` and `mistral.py`. The local embedding providers (`OllamaEmbedding`, Mistral) do not require an OpenAI key, so no injection is needed.

---

## 4. BUG-005/006: `Config.get_version()` / `get_build()` Crashes

**Where:** `config.py`

**Issue:** `_RE_VERSION.search(data)` / `_RE_BUILD.search(data)` can return `None` when the `__init__.py` metadata is missing or malformed. The code called `result.group(1)` on `None`, raising `AttributeError: 'NoneType' object has no attribute 'group'`, which broke app startup on packaged builds.

**Fix:**
- Factored the logic into a shared `_load_app_meta()` that reads the file **once** (instead of twice), uses safe fallbacks (`"0.0.0"`) when no match is found, and caches both values.
- `get_version()` / `get_build()` now return cached defaults instead of raising.

---

## 5. BUG-007: `asyncio.run()` Crash in MCP Plugin

**Where:** `plugin/mcp/plugin.py`

**Issue:** `_discover_tools_sync()` called `asyncio.run()` unconditionally. When called from inside an already-running event loop (e.g., the agents v2 runtime), this raised:

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**Fix:**
- `_discover_tools_sync()` now detects an existing running loop; if one is present it runs discovery in a fresh event loop on a daemon thread, otherwise it uses `asyncio.run()` as before. Results/errors are propagated back to the caller.

---

## 6. LiteLLM Chat History Loss

**Where:** `provider/llms/litellm.py`

**Issue:** `complete()` / `stream_complete()` always sent a single `{"role": "user", "content": prompt}` message, discarding multi-turn history and any system prompt.

**Fix:**
- Added `chat()` / `stream_chat()` implementations that accept a full `Sequence[ChatMessage]`.
- `complete()` / `stream_complete()` now accept message history via `kwargs` (`messages` / `chat_messages`) and normalize roles via a shared `_coerce_role()` helper (handles `str` and enum roles).
- A shared `_build_kwargs()` now centralizes the `model`/`temperature`/`max_tokens`/`api_key`/`api_base`/`drop_params` construction that previously existed in four near-identical copies.

---

## 7. Plugin Failure Isolation (Startup Abort)

**Where:** `controller/plugins/plugins.py`, `controller/plugins/settings.py`

**Issue:** During startup/settings init, plugins were re-configured in a loop:

```python
options = plugin.setup()          # if this raises -> whole init aborts
cfg.load_options(f'plugin.{id}', options)
```

One broken plugin could crash the entire settings dialog or app initialization.

**Fix:**
- `plugin.setup()` and `plugin.setup_ui()` are now wrapped in `try/except`; failures are logged via `debug.error()` and processing continues with the plugin's existing options.
- `cfg.load_options(...)` is also isolated so one malformed option set cannot abort the rest.

---

## 8. `get_models()` Unhandled Exceptions (all OpenAI-compatible providers)

**Where:** `provider/llms/base.py` and 11 provider files

**Issue:** `get_models()` called `client.models.list()` with no error handling. Any network/API failure during model enumeration raised out of the loop, and the same un-hardened body was copy-pasted across 10+ providers.

**Fix:**
- Canonicalized the implementation into `BaseLLM.get_models()`: it now wraps the call in `try/except`, logs via `debug.log()`, and returns `[]` on failure.
- Removed the now-redundant (and un-hardened) overrides from `openai`, `custom`, `forge`, `open_router`, `deepseek_api`, `perplexity`, `hugging_face_router`, `x_ai`, `edenai`, and `mistral` (~178 lines removed).
- The non-OpenAI-schema providers `google` and `anthropic` keep their overrides but were hardened with the same `try/except` pattern.

---

## 9. Worker Signal Cleanup Race Condition

**Where:** `plugin/base/worker.py`

**Issue:** `cleanup()` sets `self.signals = None` and calls `signals.deleteLater()` while a worker thread may still be emitting. A queued emission could hit a half-deleted C++ `QObject`, throwing `RuntimeError: Internal C++ object already deleted`.

**Fix:**
- Added a single `_emit(name, *args)` helper that safely checks for a live signal object, catches `RuntimeError` / `Exception`, and returns `False` when the object is gone.
- All emit paths (`debug`, `destroyed`, `error`, `log`, `reply`, `reply_more`, `started`, `status`, `stopped`) now route through `_emit()`, removing redundant `hasattr` double-checks.
- Also fixed a latent `AttributeError` in `reply_more()` when `self.ctx` is `None`.

---

## 10. `cmd_system/runner.py` — STDOUT/STDERR Masking

**Where:** `plugin/cmd_system/runner.py`

**Issue:** `handle_result()` preferred stderr over stdout, so a benign stderr message (e.g., a warning) silently discarded the real command output.

**Fix:**
- stdout and stderr are now combined (`"\n".join(...)` of the non-empty parts) so legitimate output is preserved alongside any error text.

---

## 11. `cmd_custom/worker.py` — Result Handling + Perf

**Where:** `plugin/cmd_custom/worker.py`

**Issue:** Same stderr-masking pattern as the system runner; per-item re-read of plugin config; multiple `datetime.now()` calls; redundant substring scans.

**Fix:**
- stdout/stderr combined instead of stderr overwriting stdout; decode uses `errors="replace"`.
- Plugin command config fetched once outside the iteration loop.
- `datetime.now()` evaluated once; placeholder replacements skip the redundant `if token in cmd` guards.
- Plugin directory cached as a module-level constant.

---

## 12. MCP Discovery Was Sequential (Perf)

**Where:** `plugin/mcp/plugin.py`

**Issue:** Each MCP server was discovered one after another with an 8s timeout each — N servers meant up to N×8s total, and the whole thing could be truncated by the 30s sync-bridge cap.

**Fix:**
- Rewrote discovery to launch one coroutine per server via `asyncio.gather(..., return_exceptions=True)`. Per-server timeout and error isolation are preserved; total time is bounded by the slowest server instead of the sum.
- Fixed a late-binding closure bug (`address` is now passed explicitly to `_discover_single_server`).

---

## 13. OpenAI Response Schema Hardening (bonus)

**Where:** `config.py`, `provider/llms/...`

**Issue:** Mixed `result`/`err`, `items`/`item` etc. variables and inner-function reuse patterns made several fixes fragile.

**Fix:** Unified naming and pushed shared logic to base classes as described above.

---

## Cross-Platform Notes (Windows + Linux)

All fixes were verified to be platform-neutral except where noted:

| Change | Windows | Linux/macOS | Notes |
|---|---|---|---|
| `cmd_custom` param quoting | `subprocess.list2cmdline()` | `shlex.quote()` | **Platform-aware helper** (`_quote_param`); the only change that needed an OS branch |
| `cmd_files` download | chunked read, `os.path` | same | Standard `os.path`/`os.makedirs` usage, no shell involved |
| MCP concurrency | threads + `asyncio` | same | `threading.Thread` + per-thread event loop works on both |
| MCP `_discover_tools_sync` loop-fallback | daemon thread | same | same code path on both |
| `get_models()` dedup (base.py) | `client.models.list()` | same | pure Python, no OS dependency |
| `config._load_app_meta()` | `os.path` read | same | platform-agnostic |
| LiteLLM `chat()`/`_build_kwargs()` | pure Python | same | platform-agnostic |
| worker `_emit()` Qt signals | Qt-safe | same | platform-agnostic |
| runner stderr/stdout merge | same | same | `"\n".join(...)` fine on Windows too |

**Pre-existing code left untouched:** `shlex.split` used to parse the MCP **stdio server command** config (`plugin/mcp/plugin.py`) is original code, not part of these fixes — it assumes a POSIX-style command line for the MCP server executable, so on Windows the stdio transport server command should be entered in a cmd-compatible form.

## Verification

- All 23 modified files pass `python -m py_compile`.
- Full pytest suite could **not** be executed in this environment (Python 3.14; project targets 3.10–3.13 and requires PySide6). Recommended commands in a normal dev environment:

```bash
poetry run pytest tests/
poetry run ruff check src/pygpt_net/
```

## Files Changed

```
src/pygpt_net/config.py
src/pygpt_net/controller/plugins/plugins.py
src/pygpt_net/controller/plugins/settings.py
src/pygpt_net/plugin/base/worker.py
src/pygpt_net/plugin/cmd_custom/worker.py
src/pygpt_net/plugin/cmd_files/worker.py
src/pygpt_net/plugin/cmd_system/runner.py
src/pygpt_net/plugin/mcp/plugin.py
src/pygpt_net/provider/llms/base.py
src/pygpt_net/provider/llms/openai.py
src/pygpt_net/provider/llms/custom.py
src/pygpt_net/provider/llms/ollama.py
src/pygpt_net/provider/llms/mistral.py
src/pygpt_net/provider/llms/litellm.py
src/pygpt_net/provider/llms/forge.py
src/pygpt_net/provider/llms/open_router.py
src/pygpt_net/provider/llms/deepseek_api.py
src/pygpt_net/provider/llms/perplexity.py
src/pygpt_net/provider/llms/hugging_face_router.py
src/pygpt_net/provider/llms/x_ai.py
src/pygpt_net/provider/llms/edenai.py
src/pygpt_net/provider/llms/google.py
src/pygpt_net/provider/llms/anthropic.py
```