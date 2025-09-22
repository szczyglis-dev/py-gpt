#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.22 15:00:00                  #
# ================================================== #

import json

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.websearch = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    # --- helpers ---

    def _to_list(self, value):
        """Normalize any value to a flat list of strings."""
        # Accept list-like values
        if value is None:
            return []
        if isinstance(value, list):
            result = []
            for v in value:
                result.extend(self._to_list(v))
            return result
        if isinstance(value, (tuple, set)):
            result = []
            for v in value:
                result.extend(self._to_list(v))
            return result
        # Accept string (also split by whitespace/newlines to support multiple URLs pasted together)
        if isinstance(value, str):
            # Split by any whitespace; do not split by comma/semicolon to avoid breaking data: URLs etc.
            parts = value.split()
            return [p.strip() for p in parts if p and isinstance(p, str)]
        # Fallback: try to cast to str
        try:
            s = str(value).strip()
            return [s] if s else []
        except Exception:
            return []

    def _extract_urls(self, item: dict, allow_args: bool = True) -> list:
        """Extract and normalize URLs from item (supports url, urls; also from args if present)."""
        urls = []
        try:
            if self.has_param(item, "urls"):
                urls.extend(self._to_list(self.get_param(item, "urls")))
            if self.has_param(item, "url"):
                urls.extend(self._to_list(self.get_param(item, "url")))
            if allow_args and self.has_param(item, "args"):
                args = self.get_param(item, "args")
                if isinstance(args, dict):
                    if "urls" in args:
                        urls.extend(self._to_list(args.get("urls")))
                    if "url" in args:
                        urls.extend(self._to_list(args.get("url")))
        except Exception:
            pass

        # Deduplicate and cleanup
        cleaned = []
        seen = set()
        for u in urls:
            if not u:
                continue
            if not isinstance(u, str):
                try:
                    u = str(u)
                except Exception:
                    continue
            u = u.strip()
            if not u:
                continue
            if u in seen:
                continue
            seen.add(u)
            cleaned.append(u)
        return cleaned

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                response = None
                try:
                    if item["cmd"] == "web_search":
                        response = self.cmd_web_urls(item)  # return URLs

                    elif item["cmd"] == "web_url_open":
                        response = self.cmd_web_url_open(item)

                    elif item["cmd"] == "web_url_raw":
                        response = self.cmd_web_url_raw(item)

                    elif item["cmd"] == "web_urls":
                        response = self.cmd_web_urls(item)

                    elif item["cmd"] == "web_index":
                        response = self.cmd_web_index(item)

                    elif item["cmd"] == "web_index_query":
                        response = self.cmd_web_index_query(item)

                    elif item["cmd"] == "web_extract_links":
                        response = self.cmd_web_extract_links(item)

                    elif item["cmd"] == "web_extract_images":
                        response = self.cmd_web_extract_images(item)

                    elif item["cmd"] == "web_request":
                        response = self.cmd_web_request(item)

                    if response:
                        responses.append(response)

                except Exception as e:
                    responses.append(
                        self.make_response(
                            item,
                            self.throw_error(e)
                        )
                    )

            if len(responses) > 0:
                self.reply_more(responses) # send response

            if self.msg is not None:
                self.log(self.msg)
                self.status(self.msg)

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def cmd_web_search(self, item: dict) -> dict:
        """
        Web search command

        :param item: command item
        :return: response item
        """
        page = 1
        if self.has_param(item, "page"):
            page = int(self.get_param(item, "page"))
        prompt = None
        if self.has_param(item, "summarize_prompt"):
            prompt = self.get_param(item, "summarize_prompt")

        query = self.get_param(item, "query", "")
        content, total_found, current, url, img = self.websearch.make_query(
            query,
            page,
            prompt,
        )
        self.msg = f"Web search finished: '{query}'"
        result = {
            'query': query,
            'content': content,
            'url': url,
            'page': current,
            'total_found': total_found,
        }
        if url:
            self.ctx.urls_before.append(url)
        if img:
            result["thumb_img"] = img
            if img not in self.ctx.images_before:
                self.ctx.images_before.append(img)

        self.ctx.save_reply = True  # leave links in context
        return self.make_response(item, result)

    def cmd_web_url_open(self, item: dict) -> dict:
        """
        Open web URL command

        :param item: command item
        :return: response item
        """
        prompt = None
        if self.has_param(item, "summarize_prompt"):
            prompt = self.get_param(item, "summarize_prompt")

        # Get URLs with robust fallback (urls/url; also supports lists)
        urls = self._extract_urls(item, allow_args=False)

        results = []
        context = ""
        for url in urls:
            try:
                self.msg = f"Opening Web URL: '{url}'"
                content, url_resolved, img = self.websearch.open_url(
                    url,
                    prompt,
                )
                # Always include the URL the result refers to
                result = {
                    'url': url_resolved or url,
                    'content': content,
                }
                context += f"From: {url_resolved or url} + :\n--------------------------------\n{content}"
                if url_resolved or url:
                    self.ctx.urls_before.append(url_resolved or url)
                if img:
                    result["thumb_img"] = img
                    if img not in self.ctx.images_before:
                        self.ctx.images_before.append(img)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'content': f"Error: {e}",
                })
                self.log(f"Error opening URL '{url}': {e}")

        extra = {
            "context": context,
        }
        return self.make_response(item, results, extra=extra)

    def cmd_web_url_raw(self, item: dict) -> dict:
        """
        Open web URL (raw) command

        :param item: command item
        :return: response item
        """
        # Get URLs with robust fallback (urls/url; also supports lists)
        urls = self._extract_urls(item, allow_args=False)

        results = []
        context = ""
        for url in urls:
            try:
                self.msg = f"Opening Web URL: '{url}'"
                content, url_resolved, img = self.websearch.open_url_raw(
                    url,
                )
                result = {
                    'url': url_resolved or url,
                    'content': content,
                }
                context += f"From: {url_resolved or url} + :\n--------------------------------\n{content}"
                if url_resolved or url:
                    self.ctx.urls_before.append(url_resolved or url)
                if img:
                    result["thumb_img"] = img
                    if img not in self.ctx.images_before:
                        self.ctx.images_before.append(img)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'content': f"Error: {e}",
                })
                self.log(f"Error opening URL '{url}': {e}")

        extra = {
            "context": context,
        }
        return self.make_response(item, results, extra=extra)

    def cmd_web_urls(self, item: dict) -> dict:
        """
        Web search for URLs command

        :param item: command item
        :return: response item
        """
        page = 1
        num = 10
        if self.has_param(item, "page"):
            page = int(self.get_param(item, "page"))
        if self.has_param(item, "num_links"):
            num = int(self.get_param(item, "num_links"))
        if num < 1:
            num = 1
        if num > 10:
            num = 10
        offset = 1
        if page > 1:
            offset = (page - 1) * num + 1

        query = self.get_param(item, "query", "")
        urls = self.websearch.search(
            query,
            num,
            offset,
        )
        self.msg = f"Web search finished: '{query}'"
        result = {
            'query': query,
            'urls': json.dumps(urls),
            'page': page,
            'num': num,
            'offset': offset,
        }
        if urls:
            for url in urls:
                if url not in self.ctx.urls_before:
                    self.ctx.urls_before.append(url)

        return self.make_response(item, result)

    def cmd_web_index(self, item: dict) -> dict:
        """
        Index web URL command

        :param item: command item
        :return: response item
        """
        type = "webpage"  # default
        args = {}

        if self.has_param(item, "type"):
            type = self.get_param(item, "type")
        if self.has_param(item, "args"):
            args = self.get_param(item, "args")

        # Extract URLs with fallback: url(s) from item and args
        urls = self._extract_urls(item, allow_args=True)
        if not urls:
            return self.make_response(item, "No URL provided")

        idx_name = self.plugin.get_option_value("idx")
        results = []

        for url in urls:
            self.msg = f"Indexing URL: '{url}'"
            self.status(f"Please wait... indexing: {url}...")

            # index URL via Llama-index per URL to keep per-URL result
            num, errors = self.plugin.window.core.idx.index_urls(
                idx=idx_name,
                urls=[url],
                type=type,
                extra_args=args,
            )
            result = {
                'url': url,
                'num_indexed': num,
                'index': idx_name,
                'errors': errors,
            }
            if url and (url.startswith("http://") or url.startswith("https://")):
                if url not in self.ctx.urls_before:
                    self.ctx.urls_before.append(url)
            results.append(result)

        # Return list of results with URLs included
        return self.make_response(item, results)

    def cmd_web_index_query(self, item: dict) -> dict:
        """
        Index web URL and query command

        :param item: command item
        :return: response item
        """
        type = "webpage"  # default
        args = {}
        query = None

        if self.has_param(item, "type"):
            type = self.get_param(item, "type")
        if self.has_param(item, "args"):
            args = self.get_param(item, "args")

        # Extract URLs with fallback: url(s) from item and args
        urls = self._extract_urls(item, allow_args=True)
        if not urls:
            result = "No URL provided"
            return self.make_response(item, result)

        if self.has_param(item, "query"):
            query = self.get_param(item, "query")

        results = []
        context = ""

        # get tmp query model (shared for all URLs)
        model = self.plugin.window.core.models.from_defaults()
        tmp_model = self.plugin.get_option_value("model_tmp_query")
        if self.plugin.window.core.models.has(tmp_model):
            model = self.plugin.window.core.models.get(tmp_model)

        if query is not None:
            for url in urls:
                try:
                    # query file using temp index (created on the fly)
                    self.log(f"Querying web: {url}")

                    answer = self.plugin.window.core.idx.chat.query_web(
                        ctx=self.ctx,
                        type=type,
                        url=url,
                        args=args,
                        query=query,
                        model=model,
                    )
                    self.log(f"Response from temporary in-memory index: {answer}")
                    content = answer if answer else "No data"
                    from_str = type
                    if url:
                        from_str += ", URL: " + url
                    context += "From: " + from_str + ":\n--------------------------------\n" + content

                    # + auto-index to main index using Llama-index
                    if self.plugin.get_option_value("auto_index"):
                        self.msg = f"Indexing URL: '{url}'"
                        idx_name = self.plugin.get_option_value("idx")
                        # show status
                        self.status(f"Please wait... indexing: {url}...")
                        # index URL via Llama-index
                        self.plugin.window.core.idx.index_urls(
                            idx=idx_name,
                            urls=[url],
                            type=type,
                            extra_args=args,
                        )

                    # add URL to context
                    if url and (url.startswith("http://") or url.startswith("https://")):
                        self.ctx.urls_before.append(url)

                    results.append({
                        'url': url,
                        'content': content,
                    })
                except Exception as e:
                    results.append({
                        'url': url,
                        'content': f"Error: {e}",
                    })
                    self.log(f"Error querying/indexing URL '{url}': {e}")
        else:
            # No query provided - return info per URL to keep URL in response
            for url in urls:
                results.append({
                    'url': url,
                    'content': "No data",
                })

        extra = {
            "context": context if context else None,
        }
        return self.make_response(item, results, extra=extra)

    def cmd_web_extract_links(self, item: dict) -> dict:
        """
        Web extract links command

        :param item: command item
        :return: response item
        """
        urls = self._extract_urls(item, allow_args=False)
        if not urls:
            return self.make_response(item, "No URL provided")

        results = []
        for url in urls:
            try:
                links = self.plugin.window.core.web.helpers.get_links(url)
                result = {
                    'url': url,
                    'links': links,
                }
                if url not in self.ctx.urls_before:
                    self.ctx.urls_before.append(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'links': [],
                    'content': f"Error: {e}",
                })
                self.log(f"Error extracting links from '{url}': {e}")

        return self.make_response(item, results)

    def cmd_web_extract_images(self, item: dict) -> dict:
        """
        Web extract images command

        :param item: command item
        :return: response item
        """
        download = False
        if self.has_param(item, "download"):
            download = bool(self.get_param(item, "download"))

        urls = self._extract_urls(item, allow_args=False)
        if not urls:
            return self.make_response(item, "No URL provided")

        results = []
        for url in urls:
            try:
                images = self.plugin.window.core.web.helpers.get_images(url)
                result = {
                    'url': url,
                    'images': images,
                }
                if images and download:
                    for img in images:
                        try:
                            path = self.plugin.window.core.web.helpers.download_image(img)
                            if path:
                                if path not in self.ctx.images_before:
                                    self.ctx.images_before.append(path)
                        except Exception as e:
                            # Keep downloading independent per image
                            print(e)
                if url not in self.ctx.urls_before:
                    self.ctx.urls_before.append(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'images': [],
                    'content': f"Error: {e}",
                })
                self.log(f"Error extracting images from '{url}': {e}")

        return self.make_response(item, results)

    def cmd_web_request(self, item: dict) -> dict:
        """
        Web request command

        :param item: command item
        :return: response item
        """
        method = "GET"
        data = None
        raw = None
        json = None
        headers = None
        params = None
        cookies = None
        files = None

        urls = self._extract_urls(item, allow_args=False)
        if not urls:
            return self.make_response(item, "No URL provided")

        if self.has_param(item, "method"):
            method = self.get_param(item, "method")
        if self.has_param(item, "data_form"):
            data = self.get_param(item, "data_form")
        if self.has_param(item, "data"):
            raw = self.get_param(item, "data")
        if self.has_param(item, "data_json"):
            json = self.get_param(item, "data_json")
        if self.has_param(item, "headers"):
            headers = self.get_param(item, "headers")
        if self.has_param(item, "params"):
            params = self.get_param(item, "params")
        if self.has_param(item, "cookies"):
            cookies = self.get_param(item, "cookies")
        if self.has_param(item, "files"):
            files = self.get_param(item, "files")

        results = []
        for url in urls:
            try:
                code, response = self.window.core.web.helpers.request(
                    url=url,
                    method=method,
                    headers=headers,
                    params=params,
                    data=data if data else raw,
                    json=json,
                    cookies=cookies,
                    files=files,
                    timeout=self.plugin.get_option_value("timeout"),
                    disable_ssl_verify=self.plugin.get_option_value("disable_ssl"),
                    allow_redirects=True,
                    stream=False,
                    user_agent=self.plugin.get_option_value("user_agent"))
                result = {
                    'url': url,
                    'code': code,
                    'response': response,
                }
                if url not in self.ctx.urls_before:
                    self.ctx.urls_before.append(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'code': None,
                    'response': f"Error: {e}",
                })
                self.log(f"Error during web request to '{url}': {e}")

        return self.make_response(item, results)