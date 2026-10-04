# Web renderer frontend

## Responsibilities

- `runtime.js` constructs collaborators and initializes/cleans up the application.
- `bootstrap.js` exposes the stable `window` API called by Python and HTML controls.
- `parts/runtime/` handles stream transport, workflow status, partial responses,
  turn lifecycle, history mutations, timeline reconciliation, and view settings.
- `stream.js` coordinates the stream lifecycle and incoming chunks.
- `parts/stream/` owns buffering, fence parsing, plain text, reasoning visibility,
  code rendering, language promotion, snapshot scheduling, and stable DOM reuse.
- `markdown.js` manages Markdown rendering and pending DOM placeholders.
  `parts/markdown/` installs math, link policy, and a shared code renderer with
  independent counters for full and streaming Markdown engines.
- `custom.js` compiles markup rules. `parts/markup/` applies those rules to source,
  ordinary HTML, and incomplete streaming HTML.
- `template.js` renders messages. `parts/templates/` renders tools, artifacts,
  and workflow timelines.
- `tool.js` manages tool payloads and accordion interaction. `parts/tools/`
  groups consecutive tool messages using their explicit continuation markers.
- `scroll.js` owns page scrolling. `parts/scroll/` separately owns code scrolling
  and history virtualization, including its observers and height measurements.
- `common.js` manages loading; `parts/ui/tips.js` manages rotating tips.
- Other top-level files retain their focused responsibilities: bridge, events,
  DOM references, highlighting, math, node insertion, queues, scheduling, and UI.

Call a component directly rather than adding a forwarding method to `Runtime`.

## Loading and building

`manifest.json` is the source of truth for script order. It is read by both the
Python development loader and `bin/minify.py`. These remain classic scripts to
work with Qt resource URLs and WebChannel; `bootstrap.js` must load last. A class
can refer to a later class in a constructor, because construction starts only in
bootstrap.

When adding a script, add its relative path to the manifest. From the repository
root, regenerate the production bundle and Qt resources:

```sh
bin/.venv-jsbuild/bin/python bin/minify.py
pyside6-rcc src/pygpt_net/js.qrc --format-version 1 -no-compress -o src/pygpt_net/js_rc.py
```

The minifier also synchronizes the source aliases in `js.qrc`. Any Python with
`rjsmin` installed can run it; without `rjsmin` it concatenates the sources.

##  Tests

From the repository root:

```sh
node tests/js/app.test.cjs
QTWEBENGINE_DISABLE_SANDBOX=1 QT_QUICK_BACKEND=software .venv/bin/python tests/core/render/web/live_tools_webview_check.py
QTWEBENGINE_DISABLE_SANDBOX=1 QT_QUICK_BACKEND=software .venv/bin/python tests/core/render/web/frontend_runtime_webview_check.py
```