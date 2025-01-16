"""
Github issues reader.

Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-github/llama_index/readers/github/issues/base.py

Extended with config in load_data method.
"""

from llama_index.readers.github.issues.base import print_if_verbose, GitHubRepositoryIssuesReader as BaseGitHubRepositoryIssuesReader
from llama_index.readers.github.issues.github_client import GitHubIssuesClient

from typing import List, Optional, Dict
from llama_index.core.schema import Document

class GitHubRepositoryIssuesReader(BaseGitHubRepositoryIssuesReader):
    def __init__(
        self,
        token: str,
        verbose: bool = False,
    ):
        """
        Init reader.

        :param token: github API token
        :param verbose: verbose mode
        """
        client = GitHubIssuesClient(github_token=token, verbose=verbose)
        super().__init__(
            github_client=client,
            owner="",
            repo="",
            verbose=verbose,
        )

    def load_data(
            self,
            owner: Optional[str] = None,
            repository: Optional[str] = None,
            state: Optional[BaseGitHubRepositoryIssuesReader.IssueState] = BaseGitHubRepositoryIssuesReader.IssueState.OPEN,
            label_filters_include: Optional[List[str]] = None,
            label_filters_exclude: Optional[List[str]] = None,
    ) -> List[Document]:
        """
        Load data from GitHub issues.

        >>Fixed extra info list appending.<<

        :param owner: repository owner
        :param repository: repository name
        :param state: issue state
        :param label_filters_include: include label filters
        :param label_filters_exclude: exclude label filters
        """
        self._owner = owner
        self._repo = repository

        filters = None
        if label_filters_include is not None:
            filters = (label_filters_include, self.FilterType.INCLUDE)
        elif label_filters_exclude is not None:
            filters = (label_filters_exclude, self.FilterType.EXCLUDE)

        documents = []
        page = 1
        # Loop until there are no more issues
        while True:
            issues: Dict = self._loop.run_until_complete(
                self._github_client.get_issues(
                    self._owner, self._repo, state=state.value, page=page
                )
            )

            if len(issues) == 0:
                print_if_verbose(self._verbose, "No more issues found, stopping")

                break
            print_if_verbose(
                self._verbose, f"Found {len(issues)} issues in the repo page {page}"
            )
            page += 1
            filterCount = 0
            for issue in issues:
                if not self._must_include(filters, issue):
                    filterCount += 1
                    continue
                title = issue["title"]
                body = issue["body"]
                document = Document(
                    doc_id=str(issue["number"]),
                    text=f"{title}\n{body}",
                )
                metadata = {
                    "state": issue["state"],
                    "created_at": issue["created_at"],
                    # url is the API URL
                    "url": issue["url"],
                    # source is the HTML URL, more convenient for humans
                    "source": issue["html_url"],
                }
                if issue["closed_at"] is not None:
                    metadata["closed_at"] = issue["closed_at"]
                if issue["assignee"] is not None:
                    metadata["assignee"] = issue["assignee"]["login"]
                if issue["labels"] is not None:
                    metadata["labels"] = ",".join([label["name"] for label in issue["labels"]])  # fix for labels
                document.metadata = metadata
                documents.append(document)

            print_if_verbose(self._verbose, f"Resulted in {len(documents)} documents")
            if filters is not None:
                print_if_verbose(self._verbose, f"Filtered out {filterCount} issues")

        return documents
