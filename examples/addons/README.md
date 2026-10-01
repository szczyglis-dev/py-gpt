# External Add-ons examples

This directory contains runnable/tutorial Add-ons and mirrors the runtime `%base_workdir%/addons` layout. Each directory containing a `manifest.json` is one independently installable package. Import **one add-on directory at a time** with **Config -> Install Add-on...**, import a ZIP containing exactly one package, or copy it to the matching `%base_workdir%/addons/<type-dir>/<id>` directory and restart PyGPT.

The examples are deliberately small, but they now execute real code instead of only registering names:

- `plugins/example_plugin` - settings, two model-callable tools, command results and event hooks.
- `tools/example_tool` - adds a real item to the Tools menu and opens a Qt dialog.
- `llms/example_llm` - offline LlamaIndex `MockLLM` plus `MockEmbedding`.
- `vector_stores/example_vector_store` - persistent local LlamaIndex vector store.
- `loaders/example_loader` - reads `.example` key/value files into `Document` objects.
- `audio_input/example_audio_input` - inspects a WAV file and returns a text transcription-like result.
- `audio_output/example_audio_output` - creates a playable WAV tone with `prepare_output_path()`.
- `web/example_web` - performs a real MediaWiki OpenSearch request and returns result URLs.
- `agents/example_agent` - runnable Custom-agents provider reusing the built-in LlamaIndex base workflow.
- `themes/example-extension-dark` - static theme package.
- `locale/example-locale` - static locale package.

`manifest.example.json` documents manifest/dependency syntax, including the `sha256` integrity field. `addons.registry.example.json` shows both a package committed to the official `py-gpt-addons` repository and a package hosted in another GitHub repository. The digest values in those two generic template files are placeholders; runnable example packages have their real generated hashes in their own manifests.

## Suggested developer loop

1. Copy one example directory and give it a globally unique, stable `id`.
2. Edit `manifest.json` and the Python entry point.
3. Install the directory through **Config -> Install Add-on...**. If `external_dependencies` contains missing required packages, PyGPT asks to install them through the shared Package Manager.
4. Restart PyGPT for Python/runtime Add-ons.
5. Enable/configure the component and test it. Use `Config -> Settings -> Debug` and event/plugin logging while developing.
6. Increase the manifest `version`, reinstall/update, and repeat.
7. Before publishing, generate the final content pin with the PyGPT `bin/addon-sha256.sh` or `bin\addon-sha256.bat` helper using `--write`, commit the updated manifest, and copy the same SHA-256 to the public registry PR.

See the **Add-ons API** page in the PyGPT documentation for lifecycle, manifest, packaging, publishing, API and method/event references.
