from .python.render import Render as PythonRender
from .filesystem.render import Render as FilesRender
from .os.render import Render as SystemRender


class Render:
    def __init__(self, plugin):
        self.plugin = plugin

    def get_rules(self):
        rules = {}
        for provider in (FilesRender, PythonRender, SystemRender):
            rules.update(provider(self.plugin).get_rules())
        python = rules.get('ipython_exec') if self.plugin.is_ipython_enabled() else rules.get('python_exec')
        if python:
            rules['python_exec'] = python
        return {name: rule for name, rule in rules.items() if name in self.plugin.allowed_cmds}
