"""
Github repository reader.

Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-github/llama_index/readers/github/repository/base.py

Extended with config in load_data method.
"""

from llama_index.readers.github.repository.base import GithubRepositoryReader as BaseGithubRepositoryReader
from llama_index.readers.github.repository.github_client import GithubClient

from typing import List, Optional
from llama_index.core.schema import Document

class GithubRepositoryReader(BaseGithubRepositoryReader):
    def __init__(
        self,
        token: str,
        use_parser: bool = False,
        verbose: bool = False,
        concurrent_requests: int = 5,
        timeout: Optional[int] = 5,
        retries: int = 0,
        filter_dirs_include: Optional[List[str]] = None,
        filter_dirs_exclude: Optional[List[str]] = None,
        filter_file_ext_include: Optional[List[str]] = None,
        filter_file_ext_exclude: Optional[List[str]] = None,
    ):
        """
        Init reader.

        :param token: github API token
        :param use_parser: use parser
        :param verbose: verbose mode
        :param concurrent_requests: concurrent requests
        :param timeout: timeout
        :param retries: retries
        :param filter_dirs_include: list of directories to include
        :param filter_dirs_exclude: list of directories to exclude
        :param filter_file_ext_include: list of file extensions to include
        :param filter_file_ext_exclude: list of file extensions to exclude
        """
        self._initialized = False
        self._token = token
        self._verbose = verbose

        filter_directories = None
        filter_file_extensions = None
        if filter_dirs_include is not None:
            filter_directories = (filter_dirs_include, self.FilterType.INCLUDE)
        elif filter_dirs_exclude is not None:
            filter_directories = (filter_dirs_exclude, self.FilterType.EXCLUDE)
        if filter_file_ext_include is not None:
            filter_file_extensions = (filter_file_ext_include, self.FilterType.INCLUDE)
        elif filter_file_ext_exclude is not None:
            filter_file_extensions = (filter_file_ext_exclude, self.FilterType.EXCLUDE)

        super().__init__(
            github_client=None,
            owner="",
            repo="",
            use_parser=use_parser,
            verbose=verbose,
            concurrent_requests=concurrent_requests,
            timeout=timeout,
            retries=retries,
            filter_directories=filter_directories,
            filter_file_extensions=filter_file_extensions,
        )

    def _initialize(self):
        """
        Initialize reader.
        """
        self._github_client = GithubClient(github_token=self._token, verbose=self._verbose)

    def load_data(
            self,
            commit_sha: Optional[str] = None,
            branch: Optional[str] = None,
            owner: Optional[str] = None,
            repository: Optional[str] = None,

    ) -> List[Document]:
        """
        Load data from github repository.

        :param commit_sha: commit sha
        :param branch: branch
        :param owner: owner
        :param repository: repository name

        :return: list of documents
        """
        if not self._initialized:
            self._initialize()
            self._initialized = True

        self._owner = owner
        self._repo = repository
        return super().load_data(commit_sha, branch)
