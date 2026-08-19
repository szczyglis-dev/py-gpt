#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT LlamaIndex data-loader tutorial              #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.core.schema import Document
from llama_index.core.readers.base import BaseReader

from pygpt_net.provider.loaders.base import BaseLoader


class ExampleDataLoader(BaseLoader):
    """Register a reader for files ending in `.examplecsv`.

    A unique demo extension is used deliberately so enabling the example launcher
    does not replace PyGPT's built-in `csv` loader. In your own provider, set
    `extensions` to the real extensions you want to handle.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_csv"  # provider/config ID; must be unique
        self.name = "Example CSV-like files"
        self.extensions = ["examplecsv"]
        self.type = ["file"]  # supported values are currently: file, web

        # These become configurable loader kwargs in PyGPT settings. Values from
        # the user's loader configuration are merged into these defaults by the
        # BaseLoader `get_args()` helper.
        self.init_args = {
            "concat_rows": True,
            "encoding": "utf-8",
        }
        self.init_args_types = {
            "concat_rows": "bool",
            "encoding": "str",
        }
        self.init_args_labels = {
            "concat_rows": "Concatenate rows",
            "encoding": "Text encoding",
        }
        self.init_args_desc = {
            "concat_rows": "Return one document for the whole file instead of one document per row.",
            "encoding": "Encoding used to read the source file.",
        }

    def get(self) -> BaseReader:
        """Create the LlamaIndex reader used for each load operation."""
        return ExampleCSVReader(**self.get_args())


class ExampleCSVReader(BaseReader):
    """A tiny LlamaIndex BaseReader implementation used by the example loader."""

    def __init__(
        self,
        *args: Any,
        concat_rows: bool = True,
        encoding: str = "utf-8",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.concat_rows = concat_rows
        self.encoding = encoding

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
    ) -> List[Document]:
        """Read the source file and return LlamaIndex Document objects."""
        rows = []
        with open(file, "r", encoding=self.encoding, newline="") as handle:
            for row in csv.reader(handle):
                rows.append(", ".join(row))

        metadata = extra_info or {}
        if self.concat_rows:
            return [Document(text="\n".join(rows), metadata=metadata)]

        return [
            Document(text=row, metadata=metadata)
            for row in rows
        ]
