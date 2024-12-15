#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 01:00:00                  #
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

    @Slot()
    def run(self):
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

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

        if self.msg is not None:
            self.log(self.msg)
            self.status(self.msg)

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
        self.msg = "Web search finished: '{}'".format(query )
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
        url = self.get_param(item, "url", "")

        self.msg = "Opening Web URL: '{}'".format(url)
        content, url, img = self.websearch.open_url(
            url,
            prompt,
        )
        result = {
            'url': url,
            'content': content,
        }
        context = "From: " + url + ":\n--------------------------------\n" + str(content)
        if url:
            self.ctx.urls_before.append(url)
        if img:
            result["thumb_img"] = img
            self.ctx.images_before.append(img)

        extra = {
            "context": context,
        }
        return self.make_response(item, result, extra=extra)

    def cmd_web_url_raw(self, item: dict) -> dict:
        """
        Open web URL (raw) command

        :param item: command item
        :return: response item
        """
        url = self.get_param(item, "url", "")
        self.msg = "Opening Web URL: '{}'".format(url)
        content, url, img  = self.websearch.open_url_raw(
            url,
        )
        result = {
            'url': url,
            'content': content,
        }
        context = "From: " + url + ":\n--------------------------------\n" + str(content)
        if url:
            self.ctx.urls_before.append(url)
        if img:
            result["thumb_img"] = img
            self.ctx.images_before.append(img)

        extra = {
            "context": context,
        }
        return self.make_response(item, result, extra=extra)

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
        self.msg = "Web search finished: '{}'".format(query)
        result = {
            'query': query,
            'urls': json.dumps(urls),
            'page': page,
            'num': num,
            'offset': offset,
        }
        if urls:
            for url in urls:
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

        url = ""
        if self.has_param(item, "url"):
            url = self.get_param(item, "url")  # from default param
        if "url" in args:
            url = args["url"]  # override from args

        if not url:
            return self.make_response(item, "No URL provided")

        self.msg = "Indexing URL: '{}'".format(url)
        idx_name = self.plugin.get_option_value("idx")
        self.status("Please wait... indexing: {}...".format(url))

        # index URL via Llama-index
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
            self.ctx.urls_before.append(url)

        extra = {
            "url": url,
        }
        return self.make_response(item, result, extra=extra)

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

        url = ""
        if self.has_param(item, "url"):
            url = self.get_param(item, "url")  # from default param
        if "url" in args:
            url = args["url"]  # override from args

        if not url:
            result = "No URL provided"
            return self.make_response(item, result)

        if self.has_param(item, "query"):
            query = self.get_param(item, "query")

        result = "No data"
        context = None
        if query is not None:
            # query file using temp index (created on the fly)
            self.log("Querying web: {}".format(url))

            # get tmp query model
            model = self.plugin.window.core.models.from_defaults()
            tmp_model = self.plugin.get_option_value("model_tmp_query")
            if self.plugin.window.core.models.has(tmp_model):
                model = self.plugin.window.core.models.get(tmp_model)

            answer = self.plugin.window.core.idx.chat.query_web(
                ctx=self.ctx,
                type=type,
                url=url,
                args=args,
                query=query,
                model=model,
            )
            self.log("Response from temporary in-memory index: {}".format(answer))
            if answer:
                from_str = type
                if url:
                    from_str += ", URL: " + url
                result = answer
                context = "From: " + from_str + ":\n--------------------------------\n" + answer

            # + auto-index to main index using Llama-index
            if self.plugin.get_option_value("auto_index"):
                self.msg = "Indexing URL: '{}'".format(url)
                idx_name = self.plugin.get_option_value("idx")
                # show status
                self.status("Please wait... indexing: {}...".format(url))
                # index URL via Llama-index
                num, errors = self.plugin.window.core.idx.index_urls(
                    idx=idx_name,
                    urls=[url],
                    type=type,
                    extra_args=args,
                )

        # add URL to context
        if url and (url.startswith("http://") or url.startswith("https://")):
            self.ctx.urls_before.append(url)

        extra = {
            "context": context,
        }
        return self.make_response(item, result, extra=extra)

    def cmd_web_extract_links(self, item: dict) -> dict:
        """
        Web extract links command

        :param item: command item
        :return: response item
        """
        url = ""
        if self.has_param(item, "url"):
            url = self.get_param(item, "url")
        if not url:
            return self.make_response(item, "No URL provided")
        links = self.plugin.window.core.web.helpers.get_links(url)
        result = {
            'links': links,
        }
        self.ctx.urls_before.append(url)
        return self.make_response(item, result)

    def cmd_web_extract_images(self, item: dict) -> dict:
        """
        Web extract images command

        :param item: command item
        :return: response item
        """
        download = False
        url = ""
        if self.has_param(item, "url"):
            url = self.get_param(item, "url")
        if self.has_param(item, "download"):
            download = bool(self.get_param(item, "download"))
        if not url:
            return self.make_response(item, "No URL provided")
        images = self.plugin.window.core.web.helpers.get_images(url)
        result = {
            'images': images,
        }
        if images and download:
            for img in images:
                try:
                    path = self.plugin.window.core.web.helpers.download_image(img)
                    if path:
                        self.ctx.images_before.append(path)
                except Exception as e:
                    print(e)
        self.ctx.urls_before.append(url)
        return self.make_response(item, result)

    def cmd_web_request(self, item: dict) -> dict:
        """
        Web request command

        :param item: command item
        :return: response item
        """
        url = ""
        method = "GET"
        data = None
        raw = None
        json = None
        headers = None
        params = None
        cookies = None
        files = None

        if self.has_param(item, "url"):
            url = self.get_param(item, "url")
        if not url:
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
        self.ctx.urls_before.append(url)
        return self.make_response(item, result)
