# JSON tree file preview

Install this directory through **Config → Install Add-on…**, then restart PyGPT.
Opening a `.json` file in Files displays an expandable tree instead of the text
editor. No extra packages are needed. `.md` and `.markdown` are rendered by a
built-in Markdown preview even without this add-on.

The entry point derives from `pygpt_net.provider.file_preview.BaseFilePreview`:

- `id`: unique provider ID; `name`: display name.
- `extensions`: supported suffixes, with or without leading dots; case-insensitive.
- `accepts(path)`: optional override for content-based detection.
- `create_widget(path, parent)`: returns a fresh `QWidget` for the absolute path.
  It runs on the GUI thread; parent the returned widget to `parent`.
- `release_widget(widget)`: optional hook to stop timers/media and release resources
  when another file replaces this preview or its panel is deleted. Files owns and deletes the widget.
- `self.window`: application window attached at registration.

Add-on previews take precedence over built-ins. Later registered providers win
when multiple providers accept the same file. Exceptions display an error and an
external-open action without stopping Files. File actions (open externally,
open folder, save as) remain available from the preview panel's breadcrumbs.

For development, use `run(file_previews=[ExampleFilePreview()])` or
`launcher.add_file_preview(ExampleFilePreview())`. Runtime registration uses
`window.core.file_previews.register(provider)`; `unregister(provider.id)` removes
it from future file selections. All Files tabs consult this shared registry.

After editing the example, regenerate its manifest checksum:

```sh
python -m pygpt_net.core.extensions.integrity examples/addons/file_previews/example_file_preview
```
