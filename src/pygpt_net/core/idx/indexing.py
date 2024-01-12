#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 10:00:00                  #
# ================================================== #

import os.path
from llama_index import (
    SimpleDirectoryReader,
)
from pathlib import Path

from pygpt_net.core.idx.loaders.pdf.base import PDFReader
from pygpt_net.core.idx.loaders.docx.base import DocxReader
from pygpt_net.core.idx.loaders.markdown.base import MarkdownReader
from pygpt_net.core.idx.loaders.json.base import JSONReader
from pygpt_net.core.idx.loaders.simple_csv.base import SimpleCSVReader
from pygpt_net.core.idx.loaders.epub.base import EpubReader
from pygpt_net.core.idx.loaders.pandas_excel.base import PandasExcelReader


class Indexing:
    def __init__(self, window=None):
        """
        Indexing core

        :param window: Window instance
        """
        self.window = window
        self.loaders = {  # offline versions
            "pdf": PDFReader(),
            "docx": DocxReader(),
            "md": MarkdownReader(),
            "json": JSONReader(),
            "csv": SimpleCSVReader(),
            "epub": EpubReader(),
            "xlsx": PandasExcelReader(),
        }  # TODO: add adding custom loaders via dict config in settings

    def get_documents(self, path):
        """
        Get documents from path

        :param path: Path to data
        :return: List of documents
        """
        if os.path.isdir(path):
            reader = SimpleDirectoryReader(
                input_dir=path,
                recursive=True,
                exclude_hidden=False
            )
            documents = reader.load_data()
        else:
            ext = os.path.splitext(path)[1][1:]  # get loader by extension
            if ext in self.loaders:
                # download_loader cause problems in compiled version, so we use offline version :(
                # loader = download_loader(self.loaders[ext])
                reader = self.loaders[ext]
                documents = reader.load_data(file=Path(path))
            else:
                reader = SimpleDirectoryReader(input_files=[path])
                documents = reader.load_data()
        return documents

    def index_files(self, index, path: str = None) -> tuple:
        """
        Index all files in directory

        :param index: Index instance
        :param path: Path to file or directory
        :return: dict with indexed files, errors
        """
        indexed = {}
        errors = []
        files = []
        if os.path.isdir(path):
            files = [os.path.join(path, f)
                     for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        elif os.path.isfile(path):
            files = [path]

        for file in files:   # per file to allow use of multiple loaders
            try:
                documents = self.get_documents(file)
                for d in documents:
                    index.insert(document=d)
                    indexed[file] = d.id_  # add to index
            except Exception as e:
                errors.append(str(e))
                print(e)
                print("Error while indexing file: " + file)
                self.window.core.debug.log(e)
                continue

        return indexed, errors
