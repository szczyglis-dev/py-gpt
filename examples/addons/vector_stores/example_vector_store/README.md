# Example vector store

This `vector_store` Add-on implements a persistent local LlamaIndex storage backend. Each PyGPT index receives a prefixed directory, and `create()`, `get()` and `store()` operate on real LlamaIndex indexes.

## Try it

Install and restart PyGPT, select `ExampleSimpleVectorStore` in the Vector Store settings, create/index a small text file, restart the app and query it again. The persistence round-trip is the important test: data should survive the restart.

For a remote backend, keep the same `BaseStore` contract but create the provider-specific LlamaIndex vector store in `index_from_store()`/`get()` as appropriate.
