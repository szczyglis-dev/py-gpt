"""Profile persistence and capture paths for Painter."""
import os


class Storage:
    def __init__(self, tool):
        self.tool = tool
        self._path = None

    def directory(self):
        return self.tool.window.core.filesystem.get_runtime_dir('capture')

    def save(self):
        canvas = self.tool.canvas
        if canvas is None:
            return False
        # Tab cleanup runs after the application may have changed profiles.
        # Save to the profile that owns these pixels, captured during restore.
        path = self._path or os.path.join(self.directory(), '_current.png')
        return canvas.files.save(path, include_drawing=True)

    def restore(self):
        canvas = self.tool.canvas
        if canvas is None:
            return
        canvas.cancel_active_drawing()
        canvas.text.cancel(canvas)
        canvas.selection.cancel()
        canvas.history.undo_stack.clear()
        canvas.history.redo_stack.clear()
        path = self._path = os.path.join(self.directory(), '_current.png')
        if os.path.isfile(path):
            canvas.document.restore(path)
        else:
            canvas.document.clear()
        canvas.update()
