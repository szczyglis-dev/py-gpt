# External Add-ons examples

This directory contains runnable/tutorial Add-ons and mirrors the runtime `%workdir%/addons` layout. Each directory containing a `manifest.json` is one independently installable package. Import **one add-on directory at a time** with **Config -> Install Add-on...**, import a ZIP containing exactly one package, or copy it to the matching `%workdir%/addons/<type-dir>/<id>` directory and restart PyGPT.

The examples are deliberately small, but they now execute real code instead of only registering names:

- `plugins/example_plugin` — settings, two model-callable tools, command results and event hooks.
- `tools/example_tool` — adds a real item to the Tools menu and opens a Qt dialog.
- `llms/example_llm` — offline LlamaIndex `MockLLM` plus `MockEmbedding`.
- `vector_stores/example_vector_store` — persistent local LlamaIndex vector store.
- `loaders/example_loader` — reads `.example` key/value files into `Document` objects.
- `audio_input/example_audio_input` — inspects a WAV file and returns a text transcription-like result.
- `audio_output/example_audio_output` — creates a playable WAV tone with `prepare_output_path()`.
- `web/example_web` — performs a real MediaWiki OpenSearch request and returns result URLs.
- `agents/example_agent` — runnable Custom-agents provider reusing the built-in LlamaIndex base workflow.
- `themes/example-extension-dark` — static theme package.
- `locale/example-locale` — static locale package.

`manifest.example.json` documents manifest/dependency syntax. `addons.registry.example.json` shows both a package committed to the official `py-gpt-addons` repository and a package hosted in another GitHub repository.

## Private locale directories

Every runtime Add-on type can optionally contain `locale/locale.<lang>.ini`. For an installed Add-on PyGPT registers this directory automatically as `addon.<manifest-id>` and assigns the domain to the runtime object; no manifest field or manual registration is required. English is the fallback locale.

The examples intentionally show several integration paths:

- `plugins/example_plugin` — automatic plugin name/description and option/command labels.
- `tools/example_tool` — `self.trans()` plus `add_lang_mapping()` for private Qt objects and live language switching.
- `llms/example_llm` — localized `provider.name` and provider-owned Settings fields using `use_locale=True`.
- `audio_input`, `audio_output`, and `web` examples — provider options added through the owning plugin inherit the Add-on domain automatically.
- `loaders/example_loader` — localized `init_args_labels` / `init_args_desc`.

`vector_store` and `agent` Add-ons receive the same domain and can use `self.trans()` for their own UI/messages. A standalone `type: locale` Add-on is different: it installs global/profile locale resources rather than a private runtime domain.

## Suggested developer loop

1. Copy one example directory and give it a globally unique, stable `id`.
2. Edit `manifest.json` and the Python entry point.
3. Install the directory through **Config -> Install Add-on...**. If `external_dependencies` contains missing required packages, PyGPT asks to install them through the shared Package Manager.
4. Restart PyGPT for Python/runtime Add-ons.
5. Enable/configure the component and test it. Use `Config -> Settings -> Debug` and event/plugin logging while developing.
6. Increase the manifest `version`, reinstall/update, and repeat.

See the **Add-ons API** page in the PyGPT documentation for lifecycle, manifest, packaging, publishing, API and method/event references.
