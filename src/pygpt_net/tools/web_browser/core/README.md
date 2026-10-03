# Canvas / Web View core

`../tool.py` contains `WebBrowser`, the application entry point and session
coordinator. It handles tool registration, tab/dialog creation and activation,
profile changes, and shared session state. There is no separate runtime class.
Each tab/dialog uses its own instance of this coordinator.

The coordinator composes ordinary service objects:

| Component | Responsibility |
| --- | --- |
| `commands.py` | Command dispatch, parameter handling and browser interactions |
| `playwright.py` | Browser/context lifecycle, page callbacks, screenshots and interactive actions |
| `qt.py` | Qt WebEngine JavaScript calls, waiting and load synchronization |
| `preview.py` | Loopback HTTP server, runtime HTML route and local asset boundaries |
| `viewport.py` | Surface attachment, input focus, viewport sizing and cursor coordinates |
| `history.py` | Persistent address history and session URL/HTML navigation |
| `document.py` | HTML files, source editing, address/base URL resolution and DOM input scripts |
| `annotations.py` | Browser selections and Playwright annotation bindings |
| `scripts.py` | Default documents and shared DOM scripts |

Services receive their session coordinator explicitly. Call the owning component
directly, for example `runtime.history.load()` or
`runtime.playwright.ensure()`.

The entry point keeps actual implementations of application lifecycle methods
and the two annotation hooks required by `AnnotationMixin` (`_render_annotations`
and `_show_annotation_editor`). These are polymorphic hooks, not component
wrappers. The shared annotation protocol also requires `_opt`.

Tabs and dialogs each own independent page, navigation, console and annotation
state. The root tool selects the active session through its surface registry.
Playwright's driver is shared by the root, but browser/context/page state belongs
to the individual session. Closing the last Playwright session stops the driver.
WebEngine and Playwright remain lazy.

The coordinator is a Qt object; services are ordinary Python objects. Callbacks
that need a Qt parent or registered surface identity refer to their coordinator.
Command execution stays on the UI thread. Only the preview server runs on its
own thread and reads the current committed runtime HTML.

The viewport observes clicks and focus events in all three views, including
WebEngine render children created later. Each interaction selects its session
and tab column without reopening the surface or consuming the input event.

Qt HTML submissions create a fresh page and wait for its successful load before
returning success. This isolates script declarations and annotation observers
from the previous document. Aborted loads and hidden-backend callbacks do not
alter the active session's history or overlays. Source for synthetic documents
comes from the committed HTML; revision checks discard stale serialization
callbacks for external pages. Qt evaluation snippets use a local scope, so their
temporary variables do not collide with declarations in the submitted page.
