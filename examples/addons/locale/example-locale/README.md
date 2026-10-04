# Example locale Add-on

This is a static `locale` Add-on. It installs `.ini` translation resources without importing Python code.

Install the directory and inspect/select the locale through PyGPT's language configuration. The bundled `locale/locale.en.ini` intentionally overrides only a tiny set of keys so it is easy to see the package format. Real locale packs can contain the complete translation key set.

This is intentionally different from a runtime Add-on's private `locale/` directory. Use `type: locale` when you want to install global/profile translation files; use `locale/locale.<lang>.ini` next to a plugin/tool/provider when translations belong only to that executable Add-on.
