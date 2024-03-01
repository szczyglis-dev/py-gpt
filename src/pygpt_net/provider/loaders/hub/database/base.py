"""
Database Reader.

Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-database/llama_index/readers/database/base.py

"""

from typing import Any, List, Optional

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from llama_index.core.utilities.sql_wrapper import SQLDatabase
from sqlalchemy import text
from sqlalchemy.engine import Engine


class DatabaseReader(BaseReader):
    """Simple Database reader.

    Concatenates each row into Document used by LlamaIndex.

    Args:
        sql_database (Optional[SQLDatabase]): SQL database to use,
            including table names to specify.
            See :ref:`Ref-Struct-Store` for more details.

        OR

        engine (Optional[Engine]): SQLAlchemy Engine object of the database connection.

        OR

        uri (Optional[str]): uri of the database connection.

        OR

        scheme (Optional[str]): scheme of the database connection.
        host (Optional[str]): host of the database connection.
        port (Optional[int]): port of the database connection.
        user (Optional[str]): user of the database connection.
        password (Optional[str]): password of the database connection.
        dbname (Optional[str]): dbname of the database connection.

    Returns:
        DatabaseReader: A DatabaseReader object.
    """

    def __init__(
        self,
        sql_database: Optional[SQLDatabase] = None,
        engine: Optional[Engine] = None,
        uri: Optional[str] = None,
        scheme: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        dbname: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize with parameters."""
        self._initialized = False
        self._sql_database = sql_database
        self._engine = engine
        self._uri = uri
        self._scheme = scheme
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._dbname = dbname
        self._args = args
        self._kwargs = kwargs

    def _initialize(self) -> None:
        """Initialize the SQLDatabase."""
        if self._sql_database:
            self.sql_database = self._sql_database
        elif self._engine:
            self.sql_database = SQLDatabase(self._engine, *self._args, **self._kwargs)
        elif self._uri:
            self.uri = self._uri
            self.sql_database = SQLDatabase.from_uri(self._uri, *self._args, **self._kwargs)
        elif self._scheme and self._host and self._port and self._user and self._password and self._dbname:
            uri = f"{self._scheme}://{self._user}:{self._password}@{self._host}:{self._port}/{self._dbname}"
            self.uri = uri
            self.sql_database = SQLDatabase.from_uri(uri, *self._args, **self._kwargs)
        else:
            raise ValueError(
                "You must provide either a SQLDatabase, "
                "a SQL Alchemy Engine, a valid connection URI, or a valid "
                "set of credentials."
            )

    def load_data(self, query: str) -> List[Document]:
        """Query and load data from the Database, returning a list of Documents.

        Args:
            query (str): Query parameter to filter tables and rows.

        Returns:
            List[Document]: A list of Document objects.
        """
        if not self._initialized:
            self._initialize()
            self._initialized = True

        documents = []
        with self.sql_database.engine.connect() as connection:
            if query is None:
                raise ValueError("A query parameter is necessary to filter the data")
            else:
                result = connection.execute(text(query))

            for item in result.fetchall():
                # fetch each item
                doc_str = ", ".join(
                    [f"{col}: {entry}" for col, entry in zip(result.keys(), item)]
                )
                documents.append(Document(text=doc_str))
        return documents