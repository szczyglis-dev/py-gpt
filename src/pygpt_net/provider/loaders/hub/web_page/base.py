"""Read Microsoft Word files."""

from pathlib import Path
from typing import Dict, List, Optional

from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document


class WebPage(BaseReader):
    """Webpage base reader."""

    def load_data(self, **kwargs) -> List[Document]:
        """
        Read URL and return documents.

        :param kwargs: keyword arguments
        :return: list of documents
        """
        from llama_index.readers import BeautifulSoupWebReader

        url = kwargs.get("url")

        return BeautifulSoupWebReader().load_data([url])
