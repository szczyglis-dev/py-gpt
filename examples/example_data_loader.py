#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 05:00:00                  #
# ================================================== #

from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.readers.schema.base import Document
from llama_index.readers.base import BaseReader

from pygpt_net.provider.loaders.base import BaseLoader  # <--- data loader must inherit from BaseLoader


class ExampleDataLoader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_csv"  # identifier for the loader, must be unique
        self.name = "CSV files"  # name of the loader
        self.extensions = ["csv"]  # file extensions that the data loader can handle
        self.type = ["file"]  # allowed types: file, web

    def get(self) -> BaseReader:
        """
        Get data reader instance

        This is the only one required method to implement.
        It must return a BaseReader instance.
        Below is an example of how to return a reader instance for CSV files.
        SimpleCSVReader is a data reader downloaded from the Llama Hub.

        :return: Data reader instance
        """
        print("Using example CSV data loader...")
        return SimpleCSVReader()


class SimpleCSVReader(BaseReader):
    """CSV parser. (downloaded from Llama Hub)

    Args:
        encoding (str): Encoding used to open the file.
            utf-8 by default.
        concat_rows (bool): whether to concatenate all rows into one document.
            If set to False, a Document will be created for each row.
            True by default.

    """

    def __init__(
        self,
        *args: Any,
        concat_rows: bool = True,
        encoding: str = "utf-8",
        **kwargs: Any
    ) -> None:
        """Init params."""
        super().__init__(*args, **kwargs)
        self._concat_rows = concat_rows
        self._encoding = encoding

    def load_data(
        self, file: Path, extra_info: Optional[Dict] = None
    ) -> List[Document]:
        """Parse file."""
        import csv

        text_list = []
        with open(file, "r", encoding=self._encoding) as fp:
            csv_reader = csv.reader(fp)
            for row in csv_reader:
                text_list.append(", ".join(row))
        if self._concat_rows:
            return [Document(text="\n".join(text_list), extra_info=extra_info or {})]
        else:
            return [
                Document(text=text, extra_info=extra_info or {}) for text in text_list
            ]
