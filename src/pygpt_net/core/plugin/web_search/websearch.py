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
            data = urlopen(url).read()
            res = json.loads(data)
            if 'items' not in res:
                return []
            for item in res['items']:
                urls.append(item['link'])
            return urls
        except Exception as e:
            print("Error in google_search: " + str(e))
        return []

    def query_wiki(self, string):
        """
        Query wikipedia for a string and return the text content

        :param string: string to query
        :return: text content
        """
        try:
            wiki = wikipedia.page(string)
            text = wiki.content
            text = re.sub(r'==.*?==+', '', text)
            return text.replace('\n', '')
        except Exception as e:
            print("Error in query_wiki: " + str(e))

    def query_web(self, string):
        """
        Query the web for a string and return the text content of the pages

        :param string: string to query
        :return: list of text content
        """
        pages = []
        if self.plugin.options["use_google"]['value']:
            urls = self.google_search(string, self.plugin.options["num_pages"]['value'])
            for url in urls:
                if self.plugin.options["use_wikipedia"]['value'] and "wikipedia.org/" in url:
                    pages.append(self.query_wiki(string))
                else:
                    pages.append(self.query_url(url))
        if len(pages) == 0:
            if self.plugin.options["use_wikipedia"]['value']:
                pages.append(self.query_wiki(string))
        return pages

    def query_url(self, url):
        """
        Query a URL and return the text content

        :param url: URL to query
        :return: text content
        """
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
            return text.replace("\n", " ").replace("\t", " ")
        except Exception as e:
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
            summary += self.plugin.window.gpt.quick_call(prompt, sys_prompt, False, max_tokens)
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
            question = self.plugin.window.gpt.quick_call(tmp_prompt, sys_prompt, use_context, 500)
            if question is not None:
                question = question.replace("<query>", "").replace("</query>", "").strip()

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
            chunks += self.to_chunks(page, chunk_size)

        # build summary
        summary = self.get_summarized_text(chunks, question)
        if summary.strip() != "":
            prompt += str(self.plugin.options['prompt_system']['value']) + summary.replace("\n", " ").replace("\t", " ")
            if len(prompt) > max_prompt_size:
                prompt = prompt[:max_prompt_size]
        return prompt

