"""Runnable file-loader example for files ending in .example."""

from llama_index.core import Document
from llama_index.core.readers.base import BaseReader

from pygpt_net.provider.loaders.base import BaseLoader


class ExampleReader(BaseReader):
    """Turn a simple key=value text file into one LlamaIndex Document."""

    def __init__(self, encoding="utf-8"):
        self.encoding = encoding

    def load_data(self, file, extra_info=None, **kwargs):
        path = str(file)
        with open(path, "r", encoding=self.encoding) as handle:
            raw = handle.read()

        pairs = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                pairs.append(f"{key.strip()}: {value.strip()}")
            else:
                pairs.append(line)

        metadata = dict(extra_info or {})
        metadata["source"] = path
        metadata["loader"] = "example_loader"
        return [Document(text="\n".join(pairs), metadata=metadata)]


class ExampleLoader(BaseLoader):
    def __init__(self):
        super().__init__()
        self.id = "example_loader"
        self.name = "Example .example files"
        self.extensions = ["example"]
        self.type = ["file"]
        self.init_args = {"encoding": "utf-8"}
        self.init_args_types = {"encoding": "str"}
        # Loader configuration carries this Add-on's locale domain, so labels
        # and descriptions can be translation keys from locale/locale.<lang>.ini.
        self.init_args_labels = {"encoding": "encoding.label"}
        self.init_args_desc = {"encoding": "encoding.description"}

    def is_supported_attachment(self, source: str) -> bool:
        return str(source).lower().endswith(".example")

    def get(self):
        return ExampleReader(**self.get_args())
