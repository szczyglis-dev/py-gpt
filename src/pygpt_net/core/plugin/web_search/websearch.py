#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.16 22:00:00                  #
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
            url += '?key='+str(key)
            url += '&cx='+str(cx)
            url += '&num='+str(num)
            url += '&sort=date-sdate:d:s'
            url += '&fields=items(link)'
            url += '&q=' + quote(q)

            self.plugin.window.log("Plugin: web_search:google_search: calling API: {}".format(url))  # log
            data = urlopen(url).read()
            res = json.loads(data)
            self.plugin.window.log("Plugin: web_search:google_search: received response: {}".format(res))  # log
            if 'items' not in res:
                return []
            for item in res['items']:
                urls.append(item['link'])
            self.plugin.window.log("Plugin: web_search:google_search [urls]: {}".format(urls))  # log
            return urls
        except Exception as e:
            self.plugin.window.log("Plugin: web_search:google_search: error: {}".format(e))  # log
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
            self.plugin.window.log("Plugin: web_search:query_wiki [content]: {}".format(text))  # log
            return text
        except Exception as ex:
            # try summary if page not found
            try:
                text = wikipedia.summary(string)
                text = re.sub(r'==.*?==+', '', text)
                text = text.replace('\n', '')
                self.plugin.window.log("Plugin: web_search:query_wiki [content]: {}".format(text))  # log
                return text
            except Exception as e:
                self.plugin.window.log("Plugin: web_search:query_wiki [error]: {}".format(e))  # log
                print("Error in query_wiki: " + str(e))

            self.plugin.window.log("Plugin: web_search:query_wiki [error]: {}".format(ex))  # log
            print("Error in query_wiki: " + str(ex))

    def query_web(self, string):
        """
        Query the web for a string and return the text content of the pages

        :param string: string to query
        :return: list of text content
        """
        self.plugin.window.log("Plugin: web_search:query_web [string]: {}".format(string))  # log
        pages = []
        if self.plugin.options["use_google"]['value']:
            urls = self.google_search(string, self.plugin.options["num_pages"]['value'])
            for url in urls:
                # if Wikipedia is enabled and URL is from Wikipedia, use Wikipedia
                if self.plugin.options["use_wikipedia"]['value'] and "wikipedia.org/" in url:
                    self.plugin.window.log("Plugin: web_search:query_web: using Wikipedia...")  # log
                    content = self.query_wiki(string)

                    # if Wiki content is empty, use Google instead
                    if content is None or content == "":
                        self.plugin.window.log("Plugin: web_search:query_web: nothing in Wiki, using Google...")  # log
                        content = self.query_url(url)
                    pages.append(content)
                else:
                    # use Google
                    self.plugin.window.log("Plugin: web_search:query_web: using Google...")  # log
                    content = self.query_url(url)
                    pages.append(content)
                self.plugin.window.log("Plugin: web_search:query_web [crawled content]: {}".format(content))  # log

                if content is not None:
                    self.plugin.window.log("Plugin: web_search:query_web [content length]: {}".format(len(content)))  # log

        # if Google is disabled, use Wikipedia
        if len(pages) == 0:
            if self.plugin.options["use_wikipedia"]['value']:
                content = self.query_wiki(string)
                self.plugin.window.log("Plugin: web_search:query_web: nothing found, using Wikipedia...")  # log
                pages.append(content)
        return pages

    def query_url(self, url):
        """
        Query a URL and return the text content

        :param url: URL to query
        :return: text content
        """
        self.plugin.window.log("Plugin: web_search:query_url: crawling URL: {}".format(url))  # log
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
            self.plugin.window.log("Plugin: web_search:query_url: received text: {}".format(text))  # log
            return text
        except Exception as e:
            self.plugin.window.log("Plugin: web_search:query_url: error querying: {}".format(url))  # log
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

    def get_summarized_text(self, chunks, question):
        """
        Get summarized text from chunks

        :param chunks: chunks of text
        :param question: question to summarize
        :return: summarized text
        """
        summary = ""
        sys_prompt = str(self.plugin.options['prompt_summarize']['value']) + question
        max_tokens = int(self.plugin.options["summary_max_tokens"]['value'])
        for prompt in chunks:
            self.plugin.window.log("Plugin: web_search:get_summarized_tex [getting summary] "
                                   "(prompt, sys_prompt, max_tokens): {}, {}, {}".
                                   format(prompt, sys_prompt, max_tokens))  # log
            response = self.plugin.window.gpt.quick_call(prompt, sys_prompt, False, max_tokens)
            if response is not None:
                self.plugin.window.log("Plugin: web_search:get_summarized_text [response length]: {}".
                                       format(len(response)))  # log
                summary += response
        return summary

    def get_system_prompt(self, question, prompt):
        """
        Get system prompt from web search results

        :param question: question to search for
        :param prompt: current prompt
        :return: system prompt
        """
        if self.plugin.options["rebuild_question"]['value']:
            use_context = self.plugin.options['rebuild_question_context']['value']
            tmp_prompt = str(self.plugin.options['prompt_question_prefix']['value']) + question
            sys_prompt = str(self.plugin.options['prompt_question']['value']).replace("{time}", time.strftime("%c"))

            self.plugin.window.log("Plugin: web_search:get_system_prompt [getting system prompt] "
                                   "(question, prompt, sys_prompt, tmp_prompt): {}, {}, {}, {}".
                                   format(question, prompt, sys_prompt, tmp_prompt))  # log

            question = self.plugin.window.gpt.quick_call(tmp_prompt, sys_prompt, use_context, 500)
            self.plugin.window.log("Plugin: web_search:get_system_prompt [search question]: {}".format(question))  # log

            if question is not None:
                question = question.replace("<query>", "").replace("</query>", "").strip()
                self.plugin.window.log(
                    "Plugin: web_search:get_system_prompt [search question extracted]: {}".format(question))  # log
                self.plugin.window.log(
                    "Plugin: web_search:get_system_prompt [search question length]: {}".format(len(question)))  # log

        # query the web
        pages = self.query_web(question)

        # get options
        max_per_page = int(self.plugin.options["max_page_content_length"]['value'])
        chunk_size = int(self.plugin.options["chunk_size"]['value'])
        max_prompt_size = int(self.plugin.options["prompt_system_length"]['value'])

        # build chunks from webpages
        chunks = []
        for page in pages:
            if page is None or page == "":
                continue
            if 0 < max_per_page < len(page):
                page = page[:max_per_page]
            chunks += self.to_chunks(page, chunk_size)  # it returns list of chunks

        # log
        self.plugin.window.log(
            "Plugin: web_search:get_system_prompt [num chunks]: {}".format(len(chunks)))  # log

        # build summary
        summary = self.get_summarized_text(chunks, question)

        # log
        self.plugin.window.log(
            "Plugin: web_search:get_system_prompt [summary]: {}".format(summary))  # log
        if summary is not None:
            self.plugin.window.log(
                "Plugin: web_search:get_system_prompt [summary length]: {}".format(len(summary)))  # log

        # append summary to prompt
        if summary is not None and summary.strip() != "":
            prompt += str(self.plugin.options['prompt_system']['value']) + summary.replace("\n", " ").replace("\t", " ")
            if len(prompt) > max_prompt_size:
                prompt = prompt[:max_prompt_size]

        # log
        self.plugin.window.log(
            "Plugin: web_search:get_system_prompt [prompt length]: {}".format(len(prompt)))  # log

        return prompt

