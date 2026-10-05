"""Host filesystem provider helpers."""
import os
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.types import MODE_AGENT_LLAMA, MODE_AGENT_V2, MODE_EXPERT


class FilesystemHelpers:
    def get_code_interpreter_sandbox_modes(self) -> tuple[bool, bool]:
        """Return active Code Interpreter sandbox modes.

        :return: (ipython_sandbox, legacy_python_sandbox)
        """
        plugin_id = "filesystem"
        try:
            if not self.window.controller.plugins.is_enabled(plugin_id):
                return False, False

            plugin = self.window.core.plugins.get(plugin_id)
            if plugin is None:
                return False, False

            sandbox = bool(plugin.is_sandbox_enabled())
            if plugin.is_ipython_enabled():
                return sandbox, False
            return False, sandbox
        except Exception as e:
            self.window.core.debug.log(e)
            return False, False


    def is_ipython_sandbox_active(self) -> bool:
        """Backward-compatible helper for the IPython sandbox."""
        return self.get_code_interpreter_sandbox_modes()[0]


    def is_legacy_sandbox_active(self) -> bool:
        """Check whether the enabled Code Interpreter uses sandboxed legacy Python."""
        return self.get_code_interpreter_sandbox_modes()[1]


    def is_runtime_attach_mode(self, mode: str = None, ctx=None, is_expert=False) -> bool:
        """Return True only for modes that own the runtime attachment loop."""
        try:
            if is_expert or getattr(ctx, "mode", None) == MODE_EXPERT:
                return True
            current_mode = mode or getattr(ctx, "mode", None) or self.window.core.config.get("mode")
            return current_mode in (MODE_AGENT_V2, MODE_AGENT_LLAMA, MODE_EXPERT)
        except Exception:
            return False


    def get_index_names(self) -> list:
        """Return effective index targets for file indexing.

        The isolated current-project index takes precedence when project-aware
        indexing is enabled. Otherwise, return all global indexes selected in
        the plugin bool-list option.
        """
        if self.get_option_value("use_project_index"):
            idx = self.window.core.idx.get_current_project_idx(virtual=True)
            if idx is not None:
                return [idx]

        value = self.get_option_value("idx")
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            raw = value
        else:
            raw = str(value).split(",")

        indexes = []
        for idx in raw:
            idx = str(idx).strip()
            if (not idx
                    or idx == "_"
                    or idx == self.window.core.idx.project.VIRTUAL_ID
                    or idx in indexes):
                continue
            indexes.append(idx)
        return indexes


    def get_index_name(self) -> str:
        """Return first effective index target (backward-compatible helper)."""
        indexes = self.get_index_names()
        return indexes[0] if indexes else ""


    def read_as_text(self, path: str, use_loaders: bool = True, ctx: CtxItem = None) -> str:
        """
        Read file and return content as text

        :param path: file path
        :param use_loaders: use Llama-index loader to read file
        :return: text content
        """
        # use_loaders = False
        self.window.core.security.ensure_read(path, sandbox=False, ctx=ctx)
        if use_loaders:
            content, docs = self.window.core.idx.indexing.read_text_content(path)
            return content
        else:
            data = ""
            if os.path.isfile(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = file.read()
            return data


