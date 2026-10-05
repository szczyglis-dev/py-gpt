# Loader configuration and translations

Each built-in loader is a package, e.g. `provider/loaders/web_bitbucket/`, with
its `Loader` class in `__init__.py` and translations in `locale/locale.en.ini`.
Imports remain `from pygpt_net.provider.loaders.web_bitbucket import Loader`.

Define reader defaults in `init_args` and field metadata in `init_args_types`:

```python
self.init_args = {"api_key": "", "enabled": False, "credentials_path": "", "mapping": {}}
self.init_args_types = {
    "api_key": {"type": "str", "required": True, "extra": {"secret": True}},
    "enabled": {"type": "bool", "extra": {}},
    "credentials_path": {"type": "str", "extra": {"path": True, "filter": "JSON files (*.json)"}},
    "mapping": {"type": "dict", "extra": {}},
}
```

Legacy type names such as `"api_key": "str"` remain supported. `type` describes
the reader value: `str`, `bool`, `int`, `float`, `list`, or `dict`. A `dict` value
is entered as JSON; it is distinct from the dictionary that defines a field.
`extra.secret` enables password masking and the visibility action used in
settings. Boolean fields use toggles and serialize to real booleans, including
false. `extra.path: true` adds a file picker; `extra.path: "directory"` selects a
directory. Optional `extra.filter` restricts the file picker. The shorthand types
`"secret"` and `"path"` are also supported and serialize as strings.

Source parameter schemas in `instructions[command]["args"]` accept the same
`type`, `extra`, `required`, `label` and `description` metadata. Configuration
fields can also define explicit `label` and `description` translation keys.
After defining a built-in schema, call
`configure_locale(__file__, required_config=(...), required_options=(...))`.
Explicit field metadata takes precedence over default metadata. Only parameters
that must always be provided belong in the required lists; environment
credentials and alternative source selectors remain optional.

For `provider/loaders/web_example/__init__.py`, put translations in
`provider/loaders/web_example/locale/locale.en.ini`:

```ini
[LOCALE]
config.api_key.label = API key
config.api_key.desc = Key used to authenticate requests.
options.url.label = URL
options.url.desc = URL of the document to read.
```

Every configuration and source field needs both a label and a description.
Additional languages use `locale.pl.ini`, `locale.de.ini`, etc. Missing languages and missing
individual keys fall back to English. All loader locale files use `locale.<lang>.ini`.
Built-in domains are `loader.<loader.id>`; application and profile overrides
follow the existing domain override rules.

## Add-ons

The Add-ons manager automatically binds a package's `locale/` directory to the
`addon.<manifest.id>` domain and supplies the same standard field keys. All field
types, extras and validation apply to Add-on loaders too. Existing custom
translation keys remain supported. No explicit localization call is needed for
an installed Add-on with a `locale/` directory. Standalone loader code can use
`configure_locale(__file__)` with translations beside its source file.
See `examples/addons/loaders/example_loader` for a runnable example.

The shared form builder supplies both the attachment dialog and the web indexer.
Language changes update labels, descriptions and picker buttons without
replacing inputs. `UrlDialog.init(rebuild=True)` rebuilds its layout and schema
while preserving selection and values of fields that still exist, including
booleans and secrets. Calling `init()` again is safe.
