"""Read Webpages"""


from typing import List

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document


class WebPage(BaseReader):
    """Webpage base reader."""

    def load_data(self, **kwargs) -> List[Document]:
        """
        Read URL and return documents.

        :param kwargs: keyword arguments
        :return: list of documents
        """
        from llama_index.readers.web import BeautifulSoupWebReader

        url = kwargs.get("url")
        return BeautifulSoupWebReader().load_data([url])
