#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # HTTP / Endpoints
        plugin.add_option("api_base", type="text", value="https://api.bitbucket.org/2.0",
                          label="API base", description="Bitbucket Cloud API 2.0 base URL.")
        plugin.add_option("http_timeout", type="int", value=30,
                          label="HTTP timeout (s)", description="Requests timeout in seconds.")

        # Auth options
        plugin.add_option("auth_mode", type="combo", value="auto",
                          label="Auth mode", description="auto|basic|bearer", keys=["auto", "basic", "bearer"],)
        plugin.add_option("bb_username", type="text", value="",
                          label="Username", description="Bitbucket username (handle, not email).")
        plugin.add_option("bb_app_password", type="textarea", value="",
                          label="App Password", description="Bitbucket App Password (Basic).", secret=True)
        plugin.add_option("bb_access_token", type="textarea", value="",
                          label="Bearer token", description="OAuth access token (Bearer).", secret=True)

        # Cached convenience
        plugin.add_option("user_uuid", type="text", value="", label="(auto) User UUID", description="Cached after bb_me.")
        plugin.add_option("username", type="text", value="", label="(auto) Username", description="Cached after bb_me.")

        # ---------------- Commands ----------------

        # Auth
        plugin.add_cmd("bb_auth_set_mode",
                       instruction="Set auth mode: auto|basic|bearer.",
                       params=[{"name": "mode", "type": "str", "required": True, "description": "auto|basic|bearer"}],
                       enabled=True, description="Auth: set mode", tab="auth")

        plugin.add_cmd("bb_set_app_password",
                       instruction="Set App Password credentials.",
                       params=[
                           {"name": "username", "type": "str", "required": True, "description": "Bitbucket username"},
                           {"name": "app_password", "type": "str", "required": True, "description": "App password"},
                           {"name": "set_mode", "type": "bool", "required": False, "description": "Switch to basic"},
                       ],
                       enabled=True, description="Auth: set App Password", tab="auth")

        plugin.add_cmd("bb_set_bearer",
                       instruction="Set Bearer token.",
                       params=[
                           {"name": "access_token", "type": "str", "required": True, "description": "OAuth access token"},
                           {"name": "set_mode", "type": "bool", "required": False, "description": "Switch to bearer"},
                       ],
                       enabled=True, description="Auth: set Bearer", tab="auth")

        plugin.add_cmd("bb_auth_check",
                       instruction="Diagnostics: show auth result for /user.",
                       params=[],
                       enabled=True, description="Auth: check", tab="auth")

        # Users / Workspaces
        plugin.add_cmd("bb_me",
                       instruction="Get authenticated user.",
                       params=[], enabled=True, description="Users: me", tab="users")

        plugin.add_cmd("bb_user_get",
                       instruction="Get user by username.",
                       params=[{"name": "username", "type": "str", "required": True, "description": "Bitbucket username"}],
                       enabled=True, description="Users: get", tab="users")

        plugin.add_cmd("bb_workspaces_list",
                       instruction="List accessible workspaces.",
                       params=[
                           {"name": "page", "type": "int", "required": False, "description": "Page"},
                           {"name": "pagelen", "type": "int", "required": False, "description": "Items per page"},
                       ],
                       enabled=True, description="Workspaces: list", tab="users")

        # Repos
        plugin.add_cmd("bb_repos_list",
                       instruction="List repositories.",
                       params=[
                           {"name": "workspace", "type": "str", "required": False, "description": "Workspace id"},
                           {"name": "role", "type": "str", "required": False, "description": "owner|contributor|member"},
                           {"name": "q", "type": "str", "required": False, "description": "BBQL filter"},
                           {"name": "sort", "type": "str", "required": False, "description": "Sort expression"},
                           {"name": "page", "type": "int", "required": False, "description": "Page"},
                           {"name": "pagelen", "type": "int", "required": False, "description": "Items per page"},
                           {"name": "after", "type": "str", "required": False, "description": "Cursor"},
                       ],
                       enabled=True, description="Repos: list", tab="repos")

        plugin.add_cmd("bb_repo_get",
                       instruction="Get repository details.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace id"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo slug"},
                       ],
                       enabled=True, description="Repos: get", tab="repos")

        plugin.add_cmd("bb_repo_create",
                       instruction="Create repository.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace id"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo slug"},
                           {"name": "description", "type": "str", "required": False, "description": "Description"},
                           {"name": "is_private", "type": "bool", "required": False, "description": "Default True"},
                           {"name": "scm", "type": "str", "required": False, "description": "git"},
                           {"name": "project_key", "type": "str", "required": False, "description": "Project key"},
                       ],
                       enabled=True, description="Repos: create", tab="repos")

        plugin.add_cmd("bb_repo_delete",
                       instruction="Delete repository.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace id"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo slug"},
                           {"name": "confirm", "type": "bool", "required": False, "description": "Must be true"},
                       ],
                       enabled=False, description="Repos: delete", tab="repos")

        # Contents
        plugin.add_cmd("bb_contents_get",
                       instruction="Get file or list directory contents.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace id"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo slug"},
                           {"name": "path", "type": "str", "required": False, "description": "Path inside repo"},
                           {"name": "ref", "type": "str", "required": False, "description": "Branch/tag/commit"},
                           {"name": "format", "type": "str", "required": False, "description": "meta|rendered"},
                           {"name": "q", "type": "str", "required": False, "description": "Filter (BBQL)"},
                           {"name": "sort", "type": "str", "required": False, "description": "Sort"},
                           {"name": "max_depth", "type": "int", "required": False, "description": "Depth"},
                       ],
                       enabled=True, description="Contents: get", tab="contents")

        plugin.add_cmd("bb_file_put",
                       instruction="Create or update a file (POST /src).",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "path", "type": "str", "required": True, "description": "Remote path"},
                           {"name": "message", "type": "str", "required": False, "description": "Commit message"},
                           {"name": "content", "type": "str", "required": False, "description": "Raw text content"},
                           {"name": "local_path", "type": "str", "required": False, "description": "Local file to upload"},
                           {"name": "branch", "type": "str", "required": False, "description": "Branch"},
                           {"name": "parents", "type": "str", "required": False, "description": "Parent commit SHA1"},
                       ],
                       enabled=True, description="Contents: put file", tab="contents")

        plugin.add_cmd("bb_file_delete",
                       instruction="Delete file(s) (POST /src with files=...).",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "paths", "type": "list", "required": True, "description": "List of paths to delete"},
                           {"name": "message", "type": "str", "required": False, "description": "Commit message"},
                           {"name": "branch", "type": "str", "required": False, "description": "Branch"},
                           {"name": "parents", "type": "str", "required": False, "description": "Parent SHA1"},
                       ],
                       enabled=True, description="Contents: delete files", tab="contents")

        # Issues
        plugin.add_cmd("bb_issues_list",
                       instruction="List repository issues.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "q", "type": "str", "required": False, "description": "BBQL filter"},
                           {"name": "state", "type": "str", "required": False, "description": "open|resolved|closed|..."},
                           {"name": "sort", "type": "str", "required": False, "description": "Sort"},
                           {"name": "page", "type": "int", "required": False, "description": "Page"},
                           {"name": "pagelen", "type": "int", "required": False, "description": "Items per page"},
                       ],
                       enabled=True, description="Issues: list", tab="issues")

        plugin.add_cmd("bb_issue_create",
                       instruction="Create an issue.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "title", "type": "str", "required": True, "description": "Title"},
                           {"name": "content", "type": "str", "required": False, "description": "Body"},
                           {"name": "assignee", "type": "str", "required": False, "description": "Assignee username"},
                       ],
                       enabled=True, description="Issues: create", tab="issues")

        plugin.add_cmd("bb_issue_comment",
                       instruction="Comment on an issue.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "id", "type": "int", "required": True, "description": "Issue id"},
                           {"name": "content", "type": "str", "required": True, "description": "Comment body"},
                       ],
                       enabled=True, description="Issues: comment", tab="issues")

        plugin.add_cmd("bb_issue_update",
                       instruction="Update an issue.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "id", "type": "int", "required": True, "description": "Issue id"},
                           {"name": "state", "type": "str", "required": False, "description": "open|resolved|closed|..."},
                           {"name": "title", "type": "str", "required": False, "description": "New title"},
                           {"name": "content", "type": "str", "required": False, "description": "New body"},
                       ],
                       enabled=True, description="Issues: update", tab="issues")

        # Pull requests
        plugin.add_cmd("bb_prs_list",
                       instruction="List pull requests.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "state", "type": "str", "required": False, "description": "open|merged|declined|superseded"},
                           {"name": "q", "type": "str", "required": False, "description": "BBQL filter"},
                           {"name": "sort", "type": "str", "required": False, "description": "Sort"},
                           {"name": "page", "type": "int", "required": False, "description": "Page"},
                           {"name": "pagelen", "type": "int", "required": False, "description": "Items per page"},
                       ],
                       enabled=True, description="PR: list", tab="pulls")

        plugin.add_cmd("bb_pr_create",
                       instruction="Create a pull request.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "title", "type": "str", "required": True, "description": "PR title"},
                           {"name": "source_branch", "type": "str", "required": True, "description": "Source branch"},
                           {"name": "destination_branch", "type": "str", "required": True, "description": "Target branch"},
                           {"name": "description", "type": "str", "required": False, "description": "PR description"},
                           {"name": "draft", "type": "bool", "required": False, "description": "Draft PR"},
                       ],
                       enabled=True, description="PR: create", tab="pulls")

        plugin.add_cmd("bb_pr_merge",
                       instruction="Merge a pull request.",
                       params=[
                           {"name": "workspace", "type": "str", "required": True, "description": "Workspace"},
                           {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                           {"name": "id", "type": "int", "required": True, "description": "PR id"},
                           {"name": "message", "type": "str", "required": False, "description": "Commit message"},
                           {"name": "close_source_branch", "type": "bool", "required": False, "description": "Close source"},
                       ],
                       enabled=True, description="PR: merge", tab="pulls")

        # Search
        plugin.add_cmd("bb_search_repos",
                       instruction="Search repositories (BBQL via ?q=).",
                       params=[
                           {"name": "q", "type": "str", "required": False, "description": "Query string (BBQL)"},
                           {"name": "sort", "type": "str", "required": False, "description": "Sort expression"},
                           {"name": "page", "type": "int", "required": False, "description": "Page"},
                           {"name": "pagelen", "type": "int", "required": False, "description": "Items per page"},
                       ],
                       enabled=True, description="Search: repositories", tab="search")