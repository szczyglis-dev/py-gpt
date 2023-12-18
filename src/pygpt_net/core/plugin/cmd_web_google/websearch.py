#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 21:00:00                  #
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
        key = self.plugin.get_option_value("google_api_key")
        cx = self.plugin.get_option_value("google_api_cx")

        if key is None or cx is None or key == "" or cx == "":
            err = "Google API key or CX is not set. Please set them in plugin settings."
            self.plugin.log(err)
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
            data = urlopen(url, timeout=4).read()
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
            self.plugin.log("Error in Google Search: " + str(e))
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
            self.plugin.log("Error in query_wiki 2: " + str(ex))

    def get_urls(self, query):
        """
        Search the web and returns URLs

        :param query: query string
        :return: list of founded URLs
        """
        num_pages = int(self.plugin.get_option_value("num_pages"))
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
            if self.plugin.get_option_value('disable_ssl'):
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                html = urlopen(req, context=context, timeout=4).read().decode("utf-8")
            else:
                html = urlopen(req, timeout=4).read().decode("utf-8")
            soup = BeautifulSoup(html, "html.parser")
            for element in soup.find_all('html'):
                text += element.text
            text = text.replace("\n", " ").replace("\t", " ")
            text = re.sub(r'\s+', ' ', text)
            self.plugin.window.log("Plugin: cmd_web_google:query_url: received text: {}".format(text))  # log
            return text
        except Exception as e:
            self.plugin.window.log("Plugin: cmd_web_google:query_url: error querying: {}".format(url))  # log
            self.plugin.log("Error in query_web: " + str(e))

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

    def get_summarized_text(self, chunks, query, summarize_prompt=None):
        """
        Get summarized text from chunks

        :param chunks: chunks of text
        :param query: query string
        :param summarize_prompt: custom summarize prompt
        :return: summarized text
        """
        summary = ""
        sys_prompt = "Summarize text in English in a maximum of 3 paragraphs, trying to find the most important " \
                     "content that can help answer the following question: {query}".format(query=query)

        # get custom prompt if set
        custom_summarize = self.plugin.get_option_value('prompt_summarize')
        if custom_summarize is not None and custom_summarize != "":
            sys_prompt = str(custom_summarize.format(query=query))
        max_tokens = int(self.plugin.get_option_value("summary_max_tokens"))

        # custom summarize prompt
        if summarize_prompt is not None and summarize_prompt != "":
            sys_prompt = summarize_prompt
        else:
            if query is None or query == "":
                sys_prompt = str(self.plugin.get_option_value('prompt_summarize_url').format(query=query))

        model = self.plugin.get_option_value("summary_model")
        # summarize per chunk
        for chunk in chunks:
            # print("Chunk: " + chunk)
            self.plugin.window.log("Plugin: cmd_web_google:get_summarized_text "
                                   "(chunk, max_tokens): {}, {}".
                                   format(chunk, max_tokens))  # log
            response = self.plugin.window.app.gpt.quick_call(chunk, sys_prompt, False, max_tokens, model)
            if response is not None and response != "":
                summary += response

        return summary

    def make_query(self, query, page_no=1, summarize_prompt=""):
        """
        Get result from search query

        :param query: query to search
        :param page_no: page number
        :param summarize_prompt: custom prompt
        :return: result, total_found, current, url
        """
        self.plugin.log("Using web query: " + query)
        urls = self.get_urls(query)

        # get options
        max_per_page = int(self.plugin.get_option_value("max_page_content_length"))
        chunk_size = int(self.plugin.get_option_value("chunk_size"))
        max_result_size = int(self.plugin.get_option_value("max_result_length"))

        total_found = len(urls)
        result = ""
        i = 1
        current = 1
        url = ""
        for url in urls:
            if url is None or url == "":
                continue

            # check if requested page number
            if current != page_no:
                current += 1
                continue

            self.plugin.log("Web attempt: " + str(i) + " of " + str(len(urls)))
            self.plugin.log("URL: " + url)
            content = self.query_url(url)
            if content is None or content == "":
                i += 1
                continue
            self.plugin.log("Content found (chars: {})".format(len(content)))
            if 0 < max_per_page < len(content):
                content = content[:max_per_page]
            chunks = self.to_chunks(content, chunk_size)  # it returns list of chunks
            self.plugin.window.log("Plugin: cmd_web_google: URL: {}".format(url))  # log
            result = self.get_summarized_text(chunks, str(query), summarize_prompt)

            # if result then stop
            if result is not None and result != "":
                self.plugin.log("Summary generated (chars: {})".format(len(result)))
                break
            i += 1

        self.plugin.window.log(
            "Plugin: cmd_web_google: summary: {}".format(result))  # log
        if result is not None:
            self.plugin.window.log("Plugin: cmd_web_google: summary length: {}".format(len(result)))  # log

        if len(result) > max_result_size:
            result = result[:max_result_size]

        self.plugin.window.log("Plugin: cmd_web_google: result length: {}".format(len(result)))  # log

        return result, total_found, current, url

    def open_url(self, url, summarize_prompt=""):
        """
        Get result from specified URL

        :param url: URL to visit
        :param summarize_prompt: custom prompt
        :return: result, url
        """
        self.plugin.log("Using URL: " + url)

        # get options
        max_per_page = int(self.plugin.get_option_value("max_page_content_length"))
        chunk_size = int(self.plugin.get_option_value("chunk_size"))
        max_result_size = int(self.plugin.get_option_value("max_result_length"))

        self.plugin.log("URL: " + url)
        content = self.query_url(url)
        self.plugin.log("Content found (chars: {})".format(len(content)))
        if 0 < max_per_page < len(content):
            content = content[:max_per_page]
        chunks = self.to_chunks(content, chunk_size)  # it returns list of chunks
        self.plugin.window.log("Plugin: cmd_web_google: URL: {}".format(url))  # log
        result = self.get_summarized_text(chunks, "", summarize_prompt)

        # if result then stop
        if result is not None and result != "":
            self.plugin.log("Summary generated (chars: {})".format(len(result)))

        self.plugin.window.log("Plugin: cmd_web_google: summary: {}".format(result))  # log
        if result is not None:
            self.plugin.window.log("Plugin: cmd_web_google: summary length: {}".format(len(result)))  # log

        if len(result) > max_result_size:
            result = result[:max_result_size]

        self.plugin.window.log("Plugin: cmd_web_google: result length: {}".format(len(result)))  # log

        return result, url
