# Example data loader

This `loader` Add-on handles files ending in `.example`. The bundled `sample.example` file contains simple `key = value` lines; the reader turns them into a real LlamaIndex `Document` with metadata.

## Try it

Install and restart PyGPT, copy `sample.example` into the active data workdir, then index it from Files/Indexer. Query the resulting index for the project or purpose fields.

The example separates the PyGPT provider (`ExampleLoader`) from the LlamaIndex reader (`ExampleReader`). `init_args` exposes reader constructor options to PyGPT's loader configuration.
