#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.04 14:00:00                  #
# ================================================== #

import json
import ssl
import time

import wikipedia
import re
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from urllib.parse import quote


class WebSearch:
    def __init__(self, plugin=None):
        """
        Web search

        :param plugin: plugin
        """
        self.plugin = plugin

    def google_search(self, q, num):
        """
        Google search

        :param q: query string
        :param num: number of results
        :return: list of URLs
        """
        key = self.plugin.options["google_api_key"]['value']
        cx = self.plugin.options["google_api_cx"]['value']

        if key is None or cx is None or key == "" or cx == "":
            err = "Google API key or CX is not set. Please set them in plugin settings."
            print(err)
            self.plugin.window.ui.dialogs.alert(err)
            return []

        urls = []
        try:
            url = 'https://www.googleapis.com/customsearch/v1'
            url += '?key=' + str(key)
            url += '&cx=' + str(cx)
            url += '&num=' + str(num)
            url += '&sort=date-sdate:d:s'
            url += '&fields=items(link)'
            url += '&q=' + quote(q)

            self.plugin.window.log("Plugin: cmd_web_google:google_search: calling API: {}".format(url))  # log
            data = urlopen(url).read()
            res = json.loads(data)
            self.plugin.window.log("Plugin: cmd_web_google:google_search: received response: {}".format(res))  # log
            if 'items' not in res:
                return []
            for item in res['items']:
                urls.append(item['link'])
            self.plugin.window.log("Plugin: cmd_web_google:google_search [urls]: {}".format(urls))  # log
            return urls
        except Exception as e:
            self.plugin.window.log("Plugin: cmd_web_google:google_search: error: {}".format(e))  # log
            self.plugin.window.ui.dialogs.alert("Google Search Error: " + str(e))
            print("Error in google_search: " + str(e))
        return []

    def query_wiki(self, string):
        """
        Query wikipedia for a string and return the text content

        :param string: string to query
        :return: text content
        """
        try:
            # try search page
            wiki = wikipedia.page(string)
            text = wiki.content
            text = re.sub(r'==.*?==+', '', text)
            text = text.replace('\n', '')
            self.plugin.window.log("Plugin: cmd_web_google:query_wiki [content]: {}".format(text))  # log
            return text
        except Exception as ex:
            # try summary if page not found
            try:
                text = wikipedia.summary(string)
                text = re.sub(r'==.*?==+', '', text)
                text = text.replace('\n', '')
                self.plugin.window.log("Plugin: cmd_web_google:query_wiki [content]: {}".format(text))  # log
                return text
            except Exception as e:
                self.plugin.window.log("Plugin: cmd_web_google:query_wiki [error]: {}".format(e))  # log
                print("Error in query_wiki 1: " + str(e))

            self.plugin.window.log("Plugin: cmd_web_google:query_wiki [error]: {}".format(ex))  # log
            print("Error in query_wiki 2: " + str(ex))

    def get_urls(self, query):
        num_pages = int(self.plugin.options["num_pages"]['value'])
        return self.google_search(query, num_pages)

    def query_url(self, url):
        """
        Query a URL and return the text content

        :param url: URL to query
        :return: text content
        """
        self.plugin.window.log("Plugin: cmd_web_google:query_url: crawling URL: {}".format(url))  # log
        text = ''
        try:
            req = Request(
                url=url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if self.plugin.options['disable_ssl']['value']:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                html = urlopen(req, context=context).read().decode("utf-8")
            else:
                html = urlopen(req).read().decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            for paragraph in soup.find_all('p'):
                text += paragraph.text
            text = text.replace("\n", " ").replace("\t", " ")
            self.plugin.window.log("Plugin: cmd_web_google:query_url: received text: {}".format(text))  # log
            return text
        except Exception as e:
            self.plugin.window.log("Plugin: cmd_web_google:query_url: error querying: {}".format(url))  # log
            print("Error in query_web: " + str(e))

    def to_chunks(self, text, chunk_size):
        """
        Split text into chunks

        :param text: text to split
        :param chunk_size: chunk size
        :return: list of chunks
        """
        if text is None or text == "":
            return []
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def get_summarized_text(self, chunks, query):
        """
        Get summarized text from chunks

        :param chunks: chunks of text
        :param query: query string
        :return: summarized text
        """
        summary = ""
        max_tokens = int(self.plugin.options["summary_max_tokens"]['value'])
        sys_prompt = str(self.plugin.options['prompt_summarize']['value']) + query + "\n"
        for chunk in chunks:
            self.plugin.window.log("Plugin: cmd_web_google:get_summarized_text "
                                   "(chunk, max_tokens): {}, {}".
                                   format(chunk, max_tokens))  # log
            response = self.plugin.window.gpt.quick_call(chunk, sys_prompt, False, max_tokens)
            if response is not None and response != "" and "**FAILED**" not in response:
                summary += response

        return summary

    def make_query(self, query):
        """
        Get system prompt from web search results

        :param query: query to search
        :return: result
        """
        urls = self.get_urls(query)

        # get options
        max_per_page = int(self.plugin.options["max_page_content_length"]['value'])
        chunk_size = int(self.plugin.options["chunk_size"]['value'])
        max_result_size = int(self.plugin.options["max_result_length"]['value'])

        result = ""
        i = 1
        for url in urls:
            if url is None or url == "":
                continue
            content = self.query_url(url)
            if content is None or content == "":
                continue
            if 0 < max_per_page < len(content):
                content = content[:max_per_page]

            chunks = self.to_chunks(content, chunk_size)  # it returns list of chunks
            print("Web attempt: " + str(i) + " of " + str(len(urls)))
            print("Url: " + url)
            self.plugin.window.log(
                "Plugin: cmd_web_google: URL: {}".format(url))  # log
            result = self.get_summarized_text(chunks, str(query))
            if result is not None and result != "":
                break
            i += 1

        self.plugin.window.log(
            "Plugin: cmd_web_google: summary: {}".format(result))  # log
        if result is not None:
            self.plugin.window.log(
                "Plugin: cmd_web_google: summary length: {}".format(len(result)))  # log

        if len(result) > max_result_size:
            result = result[:max_result_size]

        self.plugin.window.log(
            "Plugin: cmd_web_google: result length: {}".format(len(result)))  # log

        return result
