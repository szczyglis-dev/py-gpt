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
        # Endpoints / HTTP
        plugin.add_option(
            "api_base",
            type="text",
            value="https://api.github.com",
            label="API base",
            description="Base API URL (default https://api.github.com).",
        )
        plugin.add_option(
            "web_base",
            type="text",
            value="https://github.com",
            label="Web base",
            description="GitHub website base (default https://github.com).",
        )
        plugin.add_option(
            "api_version",
            type="text",
            value="2022-11-28",
            label="API version header",
            description="X-GitHub-Api-Version value.",
        )
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )

        # OAuth Device Flow
        plugin.add_option(
            "oauth_client_id",
            type="text",
            value="",
            label="OAuth Client ID",
            description="Client ID from your GitHub OAuth App (supports Device Flow).",
            secret=True,
        )
        plugin.add_option(
            "oauth_scopes",
            type="text",
            value="repo read:org read:user user:email",
            label="Scopes",
            description="Space-separated OAuth scopes for Device Flow.",
        )
        plugin.add_option(
            "oauth_open_browser",
            type="bool",
            value=True,
            label="Open browser automatically",
            description="Open verification URL in default browser.",
        )
        plugin.add_option(
            "oauth_auto_begin",
            type="bool",
            value=True,
            label="Auto-start auth when required",
            description="Begin Device Flow automatically when a command needs a token.",
        )
        plugin.add_option(
            "oauth_scope_granted",
            type="text",
            value="",
            label="(auto) Granted scopes",
            description="Set after authorization.",
        )

        # Tokens
        plugin.add_option(
            "gh_access_token",
            type="textarea",
            value="",
            label="(auto) OAuth access token",
            description="Stored OAuth access token (Device/Web).",
            secret=True,
        )
        plugin.add_option(
            "pat_token",
            type="textarea",
            value="",
            label="PAT token (optional)",
            description="Personal Access Token (classic or fine-grained).",
            secret=True,
        )
        plugin.add_option(
            "auth_scheme",
            type="text",
            value="Bearer",
            label="Auth scheme",
            description="Bearer or token (PAT usually 'token').",
        )

        # Convenience cache
        plugin.add_option(
            "user_id",
            type="text",
            value="",
            label="(auto) User ID",
            description="Cached after gh_me or auth.",
        )
        plugin.add_option(
            "username",
            type="text",
            value="",
            label="(auto) Username",
            description="Cached after gh_me or auth.",
        )

        # ---------------- Commands ----------------

        # Auth
        plugin.add_cmd(
            "gh_device_begin",
            instruction="Begin OAuth Device Flow (returns user_code and verification URL).",
            params=[
                {"name": "scopes", "type": "str", "required": False, "description": "Override scopes (space-separated)"},
            ],
            enabled=True,
            description="Auth: device begin",
            tab="auth",
        )
        plugin.add_cmd(
            "gh_device_poll",
            instruction="Poll device code for access token.",
            params=[
                {"name": "device_code", "type": "str", "required": True, "description": "Device code from gh_device_begin"},
            ],
            enabled=True,
            description="Auth: device poll",
            tab="auth",
        )
        plugin.add_cmd(
            "gh_set_pat",
            instruction="Set Personal Access Token (PAT).",
            params=[
                {"name": "token", "type": "str", "required": True, "description": "PAT token value"},
                {"name": "scheme", "type": "str", "required": False, "description": "Auth scheme: token|Bearer"},
            ],
            enabled=True,
            description="Auth: set PAT",
            tab="auth",
        )

        # Users
        plugin.add_cmd(
            "gh_me",
            instruction="Get authenticated user.",
            params=[],
            enabled=True,
            description="Users: me",
            tab="users",
        )
        plugin.add_cmd(
            "gh_user_get",
            instruction="Get user by username.",
            params=[{"name": "username", "type": "str", "required": True, "description": "GitHub login"}],
            enabled=True,
            description="Users: get",
            tab="users",
        )

        # Repos
        plugin.add_cmd(
            "gh_repos_list",
            instruction="List repositories.",
            params=[
                {"name": "username", "type": "str", "required": False, "description": "List for user (public)"},
                {"name": "org", "type": "str", "required": False, "description": "List for organization"},
                {"name": "type", "type": "str", "required": False, "description": "all|owner|member (for /user/repos)"},
                {"name": "visibility", "type": "str", "required": False, "description": "all|public|private"},
                {"name": "sort", "type": "str", "required": False, "description": "created|updated|pushed|full_name"},
                {"name": "direction", "type": "str", "required": False, "description": "asc|desc"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page index"},
            ],
            enabled=True,
            description="Repos: list",
            tab="repos",
        )
        plugin.add_cmd(
            "gh_repo_get",
            instruction="Get repository details.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner login"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo name"},
            ],
            enabled=True,
            description="Repos: get",
            tab="repos",
        )
        plugin.add_cmd(
            "gh_repo_create",
            instruction="Create repository for user or org.",
            params=[
                {"name": "name", "type": "str", "required": True, "description": "Repository name"},
                {"name": "description", "type": "str", "required": False, "description": "Description"},
                {"name": "private", "type": "bool", "required": False, "description": "Default False"},
                {"name": "auto_init", "type": "bool", "required": False, "description": "Default True"},
                {"name": "org", "type": "str", "required": False, "description": "Organization (if creating in org)"},
            ],
            enabled=True,
            description="Repos: create",
            tab="repos",
        )
        plugin.add_cmd(
            "gh_repo_delete",
            instruction="Delete repository (dangerous).",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner login"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo name"},
                {"name": "confirm", "type": "bool", "required": False, "description": "Must be true"},
            ],
            enabled=False,
            description="Repos: delete",
            tab="repos",
        )

        # Contents
        plugin.add_cmd(
            "gh_contents_get",
            instruction="Get file or list directory contents.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner login"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo name"},
                {"name": "path", "type": "str", "required": False, "description": "Path inside repo (optional)"},
                {"name": "ref", "type": "str", "required": False, "description": "Branch/tag/commit SHA"},
            ],
            enabled=True,
            description="Contents: get",
            tab="contents",
        )
        plugin.add_cmd(
            "gh_file_put",
            instruction="Create or update a file via Contents API.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner login"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo name"},
                {"name": "path", "type": "str", "required": True, "description": "Path inside repo"},
                {"name": "message", "type": "str", "required": False, "description": "Commit message"},
                {"name": "content", "type": "str", "required": False, "description": "Raw text content"},
                {"name": "local_path", "type": "str", "required": False, "description": "Local file to upload"},
                {"name": "branch", "type": "str", "required": False, "description": "Branch name"},
                {"name": "sha", "type": "str", "required": False, "description": "Existing blob sha for update"},
                {"name": "committer", "type": "dict", "required": False, "description": '{"name":"","email":""}'},
                {"name": "author", "type": "dict", "required": False, "description": '{"name":"","email":""}'},
                {"name": "resolve_sha", "type": "bool", "required": False, "description": "Auto-detect sha if missing"},
            ],
            enabled=True,
            description="Contents: put file",
            tab="contents",
        )
        plugin.add_cmd(
            "gh_file_delete",
            instruction="Delete a file via Contents API.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner login"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo name"},
                {"name": "path", "type": "str", "required": True, "description": "Path inside repo"},
                {"name": "message", "type": "str", "required": True, "description": "Commit message"},
                {"name": "sha", "type": "str", "required": True, "description": "Blob sha"},
                {"name": "branch", "type": "str", "required": False, "description": "Branch name"},
            ],
            enabled=True,
            description="Contents: delete file",
            tab="contents",
        )

        # Issues
        plugin.add_cmd(
            "gh_issues_list",
            instruction="List repository issues.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "state", "type": "str", "required": False, "description": "open|closed|all"},
                {"name": "labels", "type": "str", "required": False, "description": "Comma labels"},
                {"name": "creator", "type": "str", "required": False, "description": "Creator login"},
                {"name": "mentioned", "type": "str", "required": False, "description": "Mentioned login"},
                {"name": "assignee", "type": "str", "required": False, "description": "Assignee login"},
                {"name": "since", "type": "str", "required": False, "description": "ISO8601"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page"},
            ],
            enabled=True,
            description="Issues: list",
            tab="issues",
        )
        plugin.add_cmd(
            "gh_issue_create",
            instruction="Create an issue.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "title", "type": "str", "required": True, "description": "Issue title"},
                {"name": "body", "type": "str", "required": False, "description": "Issue body"},
                {"name": "assignees", "type": "list", "required": False, "description": "List of logins"},
                {"name": "labels", "type": "list", "required": False, "description": "List of labels"},
            ],
            enabled=True,
            description="Issues: create",
            tab="issues",
        )
        plugin.add_cmd(
            "gh_issue_comment",
            instruction="Comment on an issue.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "number", "type": "int", "required": True, "description": "Issue number"},
                {"name": "body", "type": "str", "required": True, "description": "Comment body"},
            ],
            enabled=True,
            description="Issues: comment",
            tab="issues",
        )
        plugin.add_cmd(
            "gh_issue_close",
            instruction="Close an issue.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "number", "type": "int", "required": True, "description": "Issue number"},
            ],
            enabled=True,
            description="Issues: close",
            tab="issues",
        )

        # Pull Requests
        plugin.add_cmd(
            "gh_pulls_list",
            instruction="List pull requests.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "state", "type": "str", "required": False, "description": "open|closed|all"},
                {"name": "head", "type": "str", "required": False, "description": "user:branch"},
                {"name": "base", "type": "str", "required": False, "description": "Base branch"},
                {"name": "sort", "type": "str", "required": False, "description": "created|updated|popularity|long-running"},
                {"name": "direction", "type": "str", "required": False, "description": "asc|desc"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page"},
            ],
            enabled=True,
            description="PR: list",
            tab="pulls",
        )
        plugin.add_cmd(
            "gh_pull_create",
            instruction="Create a pull request.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "title", "type": "str", "required": True, "description": "PR title"},
                {"name": "head", "type": "str", "required": True, "description": "Source branch (user:branch)"},
                {"name": "base", "type": "str", "required": True, "description": "Target branch"},
                {"name": "body", "type": "str", "required": False, "description": "PR body"},
                {"name": "draft", "type": "bool", "required": False, "description": "Draft PR"},
            ],
            enabled=True,
            description="PR: create",
            tab="pulls",
        )
        plugin.add_cmd(
            "gh_pull_merge",
            instruction="Merge a pull request.",
            params=[
                {"name": "owner", "type": "str", "required": True, "description": "Owner"},
                {"name": "repo", "type": "str", "required": True, "description": "Repo"},
                {"name": "number", "type": "int", "required": True, "description": "PR number"},
                {"name": "commit_title", "type": "str", "required": False, "description": "Commit title"},
                {"name": "commit_message", "type": "str", "required": False, "description": "Commit message"},
                {"name": "merge_method", "type": "str", "required": False, "description": "merge|squash|rebase"},
            ],
            enabled=True,
            description="PR: merge",
            tab="pulls",
        )

        # Search
        plugin.add_cmd(
            "gh_search_repos",
            instruction="Search repositories.",
            params=[
                {"name": "q", "type": "str", "required": True, "description": "Query string"},
                {"name": "sort", "type": "str", "required": False, "description": "stars|forks|help-wanted-issues|updated"},
                {"name": "order", "type": "str", "required": False, "description": "desc|asc"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page"},
            ],
            enabled=True,
            description="Search: repositories",
            tab="search",
        )
        plugin.add_cmd(
            "gh_search_issues",
            instruction="Search issues and pull requests.",
            params=[
                {"name": "q", "type": "str", "required": True, "description": "Query string"},
                {"name": "sort", "type": "str", "required": False, "description": "comments|reactions|created|updated"},
                {"name": "order", "type": "str", "required": False, "description": "desc|asc"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page"},
            ],
            enabled=True,
            description="Search: issues",
            tab="search",
        )
        plugin.add_cmd(
            "gh_search_code",
            instruction="Search code.",
            params=[
                {"name": "q", "type": "str", "required": True, "description": "Query string (use qualifiers)"},
                {"name": "per_page", "type": "int", "required": False, "description": "Items per page"},
                {"name": "page", "type": "int", "required": False, "description": "Page"},
            ],
            enabled=True,
            description="Search: code",
            tab="search",
        )