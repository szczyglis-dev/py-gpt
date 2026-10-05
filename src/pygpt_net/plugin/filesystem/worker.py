"""Route commands by provider while emitting a single combined reply."""
from .python.worker import Worker as PythonWorker
from .filesystem.worker import Worker as FilesWorker
from .os.worker import Worker as SystemWorker


class SystemView:
    """Use the OS runner for desktop APIs and the Python runtime for shell commands."""
    def __init__(self, plugin):
        self.plugin = plugin
        self.runner = plugin.system_runner

    def __getattr__(self, name):
        return getattr(self.plugin, name)


class RoutedSystemWorker(SystemWorker):
    def cmd_shell_exec(self, item):
        backend = self.plugin.get_execution_backend()
        request = self.from_request(item)
        runner = self.plugin.plugin.runner
        runner.attach_signals(self.signals)
        try:
            try:
                result = backend.shell_exec(self.ctx, item, request)
            except Exception as exc:
                result = self.throw_error(exc)
        finally:
            runner.detach_signals(self.signals)
        return self.make_response(item, result, extra=self.prepare_extra(item, result))


class Worker(PythonWorker):
    def run(self):
        responses = []
        try:
            for item in self.cmds:
                if self.is_stopped():
                    break
                cmd = item['cmd']
                if cmd in self.plugin.command_groups['filesystem']:
                    child = FilesWorker()
                elif cmd in self.plugin.command_groups['system']:
                    child = RoutedSystemWorker()
                else:
                    child = PythonWorker()
                child.plugin = SystemView(self.plugin) if isinstance(child, SystemWorker) else self.plugin
                child.window = self.window
                child.ctx = self.ctx
                child.signals.deleteLater()
                child.signals = self.signals
                child.cmds = [item]
                child.reply_more = responses.extend
                child.cleanup = lambda: None
                # Select the internal implementation without changing public request/response names.
                if cmd == 'python_exec' and self.plugin.is_ipython_enabled():
                    child.cmd_python_exec = child.cmd_ipython_exec
                child.run()
            if responses:
                self.reply_more(responses)
        except Exception as exc:
            self.error(exc)
        finally:
            self.cleanup()
