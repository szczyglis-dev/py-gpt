"""Window-scoped preview providers shared by all Files tabs."""
from pygpt_net.provider.file_preview import BaseFilePreview


class FilePreviews:
    def __init__(self, window=None):
        self.window = window
        self.providers = {}

    def register(self, provider):
        if not isinstance(provider, BaseFilePreview):
            raise TypeError('File preview must derive from BaseFilePreview')
        if not provider.id:
            raise ValueError('File preview provider requires an id')
        provider.attach_window(self.window)
        self.providers[provider.id] = provider

    def unregister(self, provider_id):
        self.providers.pop(provider_id, None)

    def resolve(self, path):
        # Later registrations can override an earlier provider for the same suffix.
        for provider in reversed(list(self.providers.values())):
            if provider.accepts(path):
                return provider
        return None
