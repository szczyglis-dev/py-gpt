# Example web-search provider

This `web` Add-on performs a real network request against Wikipedia's public MediaWiki OpenSearch endpoint and returns result URLs in the format expected by PyGPT's Web search plugin.

## Try it

Install and restart PyGPT, select **Example Wikipedia search** as the search engine in the Web search plugin, then ask the model to search the web. Set the example language option to `pl` or `en` to test provider settings.

Production providers should add authentication/options in `init_options()`, implement `search(query, limit, offset)`, and use `is_configured(cmds)`/`get_config_message()` for configuration validation.
