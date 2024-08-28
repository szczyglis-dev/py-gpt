#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 15:00:00                  #
# ================================================== #

import json
import os
import re
import html
from datetime import datetime

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.utils import trans

from .parser import Parser
from .syntax_highlight import SyntaxHighlight

import pygpt_net.js_rc


class Renderer(BaseRenderer):

    NODE_INPUT = 0
    NODE_OUTPUT = 1

    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        Web renderer

        :param window: Window instance
        """
        self.window = window
        self.parser = Parser(window)
        self.highlight = SyntaxHighlight(window)
        self.images_appended = []
        self.urls_appended = []
        self.buffer = ""  # stream buffer
        self.is_cmd = False
        self.img_width = 400
        self.html = ""  # html buffer
        self.document = ""
        self.initialized = False
        self.loaded = False  # page loaded
        self.item = None  # current item
        self.use_buffer = False  # use html buffer
        self.name_user = trans("chat.name.user")
        self.name_bot = trans("chat.name.bot")
        self.last_time_called = 0
        self.cooldown = 1 / 6  # max chunks to parse per second
        self.throttling_min_chars = 5000  # min chunk chars to activate cooldown

    def init(self):
        """
        Initialize renderer
        """
        if not self.initialized:
            self.flush()
            self.initialized = True
        else:
            self.clear_chunks()

    def reset_names(self):
        """Reset names"""
        self.name_user = trans("chat.name.user")
        self.name_bot = trans("chat.name.bot")

    def begin(self, stream: bool = False):
        """
        Render begin

        :param stream: True if it is a stream
        """
        self.init()
        self.reset_names()

    def end(self, stream: bool = False):
        """
        Render end

        :param stream: True if it is a stream
        """
        if self.item is not None and stream:
            self.append_context_item(self.item)
            self.item = None

    def end_extra(self, stream: bool = False):
        """
        Render end extra

        :param stream: True if it is a stream
        """
        self.to_end()

    def stream_begin(self):
        """Render stream begin"""
        pass  # do nothing

    def stream_end(self):
        """Render stream end"""
        if self.window.controller.agent.enabled():
            if self.item is not None:
                self.append_context_item(self.item)
                self.item = None

    def clear_output(self):
        """Clear output"""
        self.reset()

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def reset(self):
        """Reset"""
        self.parser.reset()
        self.item = None
        self.html = ""
        self.clear_nodes()
        self.clear_chunks()
        self.images_appended = []
        self.urls_appended = []
        self.get_output_node().reset_current_content()
        self.reset_names()

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

    def update_names(self, item: CtxItem):
        """
        Update names

        :param item: context item
        """
        if item.input_name is not None and item.input_name != "":
            self.name_user = item.input_name
        if item.output_name is not None and item.output_name != "":
            self.name_bot = item.output_name

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        self.init()

        if clear:
            self.clear_output()
        i = 0
        self.use_buffer = True
        self.html = ""
        for item in items:
            self.update_names(item)
            item.idx = i
            if i == 0:
                item.first = True
            self.append_context_item(item)  # to html buffer
            i += 1
        self.use_buffer = False

        # flush
        if self.html != "":
            self.append(self.html, flush=True)  # flush buffer if page loaded, otherwise it will be flushed on page load

    def append_input(self, item: CtxItem, flush: bool = True, node: bool = False):
        """
        Append text input to output

        :param item: context item
        :param flush: flush HTML
        :param node: True if force append node
        """
        if not flush:
            self.clear_chunks_input()

        self.update_names(item)

        if item.input is None or item.input == "":
            return

        text = item.input

        # check if it is a command response
        is_cmd = False
        if item.input.strip().startswith("[") and item.input.strip().endswith("]"):
            is_cmd = True

        # hidden internal call
        if item.internal \
                and not is_cmd \
                and not item.first \
                and not item.input.strip().startswith("user: ")\
                and not item.input.strip().startswith("@"):  # expert says:
            if flush:
                content = self.prepare_node('>>>', self.NODE_INPUT, item)
                self.append_chunk_input(item, content, True)
            else:
                self.append_node('>>>', self.NODE_INPUT, item)
            return
        else:
            # don't show user prefix if provided in internal call goal update
            if item.internal and item.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', item.input)

        if flush:  # to chunk buffer
            content = self.prepare_node(text.strip(), self.NODE_INPUT, item)
            if self.is_stream() and not node:
                self.append_chunk_input(item, content, False)
            else:
                self.append_node(text.strip(), self.NODE_INPUT, item)
        else:
            self.append_node(text.strip(), self.NODE_INPUT, item)

    def append_output(self, item: CtxItem, flush: bool = True):
        """
        Append text output to output

        :param item: context item
        :param flush: flush HTML
        """
        if item.output is None or item.output == "":
            return
        self.append_node(item.output.strip(), self.NODE_OUTPUT, item)

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        self.item = item
        if text_chunk is None or text_chunk == "":
            if begin:
                self.buffer = ""  # always reset buffer
            return

        self.update_names(item)
        raw_chunk = str(text_chunk)
        if begin:
            self.buffer = ""  # reset buffer
            self.is_cmd = False  # reset command flag
            self.clear_chunks_output()
        self.buffer += raw_chunk

        """
        # cooldown (throttling) to prevent high CPU usage on huge text chunks
        if len(self.buffer) > self.throttling_min_chars:
            current_time = time.time()
            if current_time - self.last_time_called <= self.cooldown:
                return  # wait a moment
            else:
                self.last_time_called = current_time
        """

        # parse chunks
        to_append = self.buffer
        if has_unclosed_code_tag(self.buffer):
            to_append += "\n```"  # fix for code block without closing ```
        html = self.parser.parse(to_append)
        escaped_chunk = json.dumps(html)
        try:
            self.get_output_node().page().runJavaScript(f"replaceOutput('{self.name_bot}', {escaped_chunk});")
        except Exception as e:
            pass

    def append_chunk_input(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return
        if item.hidden:
            return
        self.clear_chunks_input()
        chunk = self.format_chunk(text_chunk)
        escaped_chunk = json.dumps(chunk)
        try:
            self.get_output_node().page().runJavaScript(f"appendToInput({escaped_chunk});")
        except Exception as e:
            pass

    def append_block(self):
        """Append block to output"""
        pass

    def to_end(self):
        """Move cursor to end of output"""
        pass

    def prepare_node(self, html: str, type: int = 1, item: CtxItem = None) -> str:
        """
        Prepare node HTML

        :param html: html text
        :param type: type of message
        :param item: CtxItem instance
        :return: prepared HTML
        """
        if type == self.NODE_OUTPUT:
            return self.prepare_node_output(html, item)
        elif type == self.NODE_INPUT:
            return self.prepare_node_input(html, item)

    def prepare_node_input(self, html: str, item: CtxItem = None) -> str:
        """
        Prepare input node

        :param html: html text
        :param item: CtxItem instance
        :return: prepared HTML
        """
        id = "msg-user-" + str(item.id) if item is not None else ""
        content = self.append_timestamp(self.format_user_text(html), item, type=self.NODE_INPUT)
        html = "<p>" + content + "</p>"
        html = self.post_format_text(html)
        name = self.name_user
        if item.internal and item.input.startswith("[{"):
            name = "System"
        html = '<div class="msg-box msg-user" id="{}"><div class="name-header name-user">{}</div><div class="msg">'.format(id, name) + html + "</div></div>"
        return html

    def prepare_node_output(self, html: str, item: CtxItem = None) -> str:
        """
        Prepare output node

        :param html: html text
        :param item: CtxItem instance
        :return: prepared HTML
        """
        id = "msg-bot-" + str(item.id) if item is not None else ""
        html = self.pre_format_text(html)
        html = self.append_timestamp(html, item, type=self.NODE_OUTPUT)
        html = self.parser.parse(html)
        html = self.post_format_text(html)
        extra = self.append_extra(item, footer=True, render=False)
        footer_icons = self.prepare_action_icons(item)
        html = '<div class="msg-box msg-bot" id="{}"><div class="name-header name-bot">{}</div><div class="msg">'.format(id, self.name_bot) + html + '<div class="msg-extra">'+extra+'</div>' +footer_icons+ '</div></div>'
        return html

    def append_node(self, html: str, type: int = 1, item: CtxItem = None):
        """
        Append and format raw text to output

        :param html: text to append
        :param type: type of message
        :param item: CtxItem instance
        """
        if item.hidden:
            return
        self.append(self.prepare_node(html, type, item))

    def clear_chunks_output(self):
        """Clear chunks from output"""
        if not self.loaded:
            js = "var element = document.getElementById('_append_output_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearOutput();"
        try:
            self.get_output_node().page().runJavaScript(js)
        except Exception as e:
            pass

    def clear_chunks_input(self):
        """Clear chunks from input"""
        if not self.loaded:
            js = "var element = document.getElementById('_append_input_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearInput();"
        try:
            self.get_output_node().page().runJavaScript(js)
        except Exception as e:
            pass

    def clear_nodes(self):
        """Clear nodes from output"""
        if not self.loaded:
            js = "var element = document.getElementById('_nodes_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearNodes();"
        try:
            self.get_output_node().page().runJavaScript(js)
        except Exception as e:
            pass

    def clear_chunks(self):
        """Clear chunks from output"""
        self.clear_chunks_input()
        self.clear_chunks_output()

    def append(self, html: str, flush: bool = False):
        """
        Append text to output

        :param html: HTML code
        :param flush: True if flush only
        """
        if self.loaded and not self.use_buffer:
            self.clear_chunks()
            self.flush_output(html)  # render
            self.html = ""
        else:
            if not flush:
                self.html += html  # to buffer

    def append_context_item(self, item: CtxItem):
        """
        Append context item to output

        :param item: context item
        """
        self.append_input(item, flush=False)
        self.append_output(item, flush=False)  # + extra

    def get_image_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get image HTML

        :param url: URL to image
        :param num: number of image
        :param num_all: number of all images
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """<a href="{url}"><img src="{path}" class="image"></a>
        <p><b>{prefix}{num}:</b> <a href="{url}">{path}</a></p>""". \
            format(prefix=trans('chat.prefix.img'),
                   url=url,
                   path=path,
                   num=num_str)

    def get_url_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get URL HTML

        :param url: external URL
        :param num: number of URL
        :param num_all: number of all URLs
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        return """<b>{prefix}{num}:</b> <a href="{url}">{url}</a>""". \
            format(prefix=trans('chat.prefix.url'),
                   url=url,
                   num=num_str)

    def get_docs_html(self, docs: list) -> str:
        """
        Get Llama-index doc metadata HTML

        :param docs: list of document metadata
        :return: HTML code
        """
        html = ""
        html_sources = ""
        num = 1
        max = 3
        try:
            for item in docs:
                for uuid, doc_json in item.items():
                    """
                    Example doc (file metadata):
                    {'a2c7af6d-3c34-4c28-bf2d-6161e7fb525e': {
                        'file_path': '/home/user/.config/pygpt-net/data/my_cars.txt',
                        'file_name': '/home/user/.config/pygpt-net/data/my_cars.txt', 'file_type': 'text/plain',
                        'file_size': 28, 'creation_date': '2024-03-03', 'last_modified_date': '2024-03-03',
                        'last_accessed_date': '2024-03-03'}}
                    """
                    doc_parts = []
                    for key in doc_json:
                        doc_parts.append("<b>{}:</b> {}".format(key, doc_json[key]))
                    html_sources += "<p><small>[{}] {}: {}</small></p>".format(num, uuid, ", ".join(doc_parts))
                    num += 1
                if num >= max:
                    break
        except Exception as e:
            pass

        if html_sources != "":
            html += "<p><small><b>{prefix}:</b></small></p>".format(prefix=trans('chat.prefix.doc'))
            html += "<div class=\"cmd\">"
            html += "<p>" + html_sources + "</p>"
            html += "</div> "
        return html

    def get_file_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get file HTML

        :param url: URL to file
        :param num: number of file
        :param num_all: number of all files
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """<div><b>{prefix}{num}:</b> <a href="{url}">{path}</a></div>""". \
            format(prefix=trans('chat.prefix.file'),
                   url=url,
                   path=path,
                   num=num_str)

    def flush_output(self, html: str):
        """
        Flush output

        :param html: HTML code
        """
        escaped_html = json.dumps(html)
        try:
            self.get_output_node().page().runJavaScript(f"appendNode({escaped_html});")
            self.get_output_node().update_current_content()
        except Exception as e:
            pass

    def append_timestamp(self, text: str, item: CtxItem, type: int = None) -> str:
        """
        Append timestamp to text

        :param text: Input text
        :param item: Context item
        :param type: Type of message
        :return: Text with timestamp (if enabled)
        """
        if item is not None and item.input_timestamp is not None:
            timestamp = None
            if type == self.NODE_INPUT:
                timestamp = item.input_timestamp
            elif type == self.NODE_OUTPUT:
                timestamp = item.output_timestamp
            if timestamp is not None:
                ts = datetime.fromtimestamp(timestamp)
                hour = ts.strftime("%H:%M:%S")
                text = '<span class="ts">{}: </span>{}'.format(hour, text)
        return text

    def replace_code_tags(self, text: str) -> str:
        """
        Replace cmd code tags

        :param text:
        :return: replaced text
        """
        pattern = r"~###~(.*?)~###~"
        replacement = r'<p class="cmd">\1</p>'
        return re.sub(pattern, replacement, text)

    def pre_format_text(self, text: str) -> str:
        """
        Pre-format text

        :param text: text to format
        :return: formatted text
        """
        text = text.strip()
        text = text.replace("#~###~", "~###~")  # fix for #~###~ in text (previous versions)
        text = text.replace("# ~###~", "~###~")  # fix for # ~###~ in text (previous versions)

        # replace cmd tags
        text = self.replace_code_tags(text)

        # replace %workdir% with current workdir
        local_prefix = self.window.core.filesystem.get_workdir_prefix()
        safe_local_prefix = local_prefix.replace('\\', '\\\\').replace('\\.', '\\\\.')  # windows fix
        replacement = f'({safe_local_prefix}\\1)'
        try:
            text = re.sub(r'\(%workdir%([^)]+)\)', replacement, text)
        except Exception as e:
            pass
        return text

    def post_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        return text.strip()

    def format_user_text(self, text: str) -> str:
        """
        Post-format user text

        :param text: text to format
        :return: formatted text
        """
        text = html.escape(text).replace("\n", "<br>")
        # append cmd tags if response from command detected
        if (text.strip().startswith("[") or text.strip().startswith("&gt; [")) and text.strip().endswith("]"):
            text = '<div class="cmd">&gt; {}</div>'.format(text)
        return text

    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text.replace("\n", "<br/>")

    def is_timestamp_enabled(self) -> bool:
        """
        Check if timestamp is enabled

        :return: True if timestamp is enabled
        """
        return self.window.core.config.get('output_timestamp')

    def get_output_node(self):
        """
        Get output node

        :return: output node
        """
        return self.window.ui.nodes['output']

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def append_html(self, html: str):
        """
        Append HTML to output

        :param html: HTML code
        """
        self.html += html

    def append_extra(self, item: CtxItem, footer: bool = False, render: bool = True) -> str:
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        :param footer: True if it is a footer
        :param render: True if render, False if only return HTML
        :return: HTML code
        """
        appended = []
        html = ""
        # images
        c = len(item.images)
        if c > 0:
            n = 1
            for image in item.images:
                # don't append if it is an external url
                if image.startswith("http"):
                    continue
                if image in appended or image in self.images_appended:
                    continue
                try:
                    appended.append(image)
                    html += self.get_image_html(image, n, c)
                    self.images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        c = len(item.files)
        if c > 0:
            n = 1
            for file in item.files:
                if file in appended:
                    continue
                try:
                    appended.append(file)
                    html += self.get_file_html(file, n, c)
                    n += 1
                except Exception as e:
                    pass

        # urls
        c = len(item.urls)
        if c > 0:
            urls_html = []
            n = 1
            for url in item.urls:
                if url in appended or url in self.urls_appended:
                    continue
                try:
                    appended.append(url)
                    urls_html.append(self.get_url_html(url, n, c))
                    self.urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_html:
                html += "<br/>" + "<br/>".join(urls_html)

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if item.doc_ids is not None and len(item.doc_ids) > 0:
                try:
                    docs = self.get_docs_html(item.doc_ids)
                    html += docs
                except Exception as e:
                    pass
        # flush
        if render and html != "":
            if footer:
                # append to output
                self.append(html)
            else:
                # append to existing message box using JS
                escaped_html = json.dumps(html)
                self.get_output_node().page().runJavaScript("appendExtra('{}',{});".format(item.id, escaped_html))

        return html

    def prepare_action_icons(self, item: CtxItem) -> str:
        """
        Append action icons

        :param item: context item
        :return: HTML code
        """
        html = ""
        show_edit = self.window.core.config.get('ctx.edit_icons')
        icons_html = "".join(self.get_action_icons(item, all=show_edit))
        if icons_html != "":
            extra = "<div class=\"action-icons\" data-id=\"{}\">{}</div>".format(item.id, icons_html)
            html += extra
        return html

    def get_action_icons(self, item: CtxItem, all: bool = False) -> list:
        """
        Get action icons for context item

        :param item: context item
        :param all: True to show all icons
        :return: list of icons
        """
        icons = []

        # audio read
        if item.output is not None and item.output != "":
            icons.append(
                '<a href="extra-audio-read:{}" class="action-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    item.id,
                    self.get_icon("audio", trans("ctx.extra.audio"), item)
                )
            )
            # copy item
            icons.append(
                '<a href="extra-copy:{}" class="action-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    item.id,
                    self.get_icon("copy", trans("ctx.extra.copy"), item)
                )
            )
            # regen link
            icons.append(
                '<a href="extra-replay:{}" class="action-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    item.id,
                    self.get_icon("reload", trans("ctx.extra.reply"), item)
                )
            )
            # edit link
            icons.append(
                '<a href="extra-edit:{}" class="action-icon edit-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    item.id,
                    self.get_icon("edit", trans("ctx.extra.edit"), item)
                )
            )
            # delete link
            icons.append(
                '<a href="extra-delete:{}" class="action-icon edit-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    item.id,
                    self.get_icon("delete", trans("ctx.extra.delete"), item)
                )
            )

            # join link
            if not self.window.core.ctx.is_first_item(item.id):
                icons.append(
                    '<a href="extra-join:{}" class="action-icon edit-icon" data-id="{}"><span class="cmd">{}</span></a>'.format(
                        item.id,
                        item.id,
                        self.get_icon("join", trans("ctx.extra.join"), item)
                    )
                )
        return icons

    def get_icon(self, icon: str, title: str = None, item: CtxItem = None) -> str:
        """
        Get icon

        :param icon: icon name
        :param title: icon title
        :param item: context item
        :return: icon HTML
        """
        icon = os.path.join(self.window.core.config.get_app_path(), "data", "icons", "chat", icon + ".png")
        return '<img src="file://{}" class="action-img" title="{}" alt="{}" data-id="{}">'.format(
            icon, title, title, item.id)

    def on_page_loaded(self):
        """On page loaded"""
        self.loaded = True
        if self.html != "" and not self.use_buffer:
            self.clear_chunks()
            self.clear_nodes()
            self.append(self.html, flush=True)
            self.html = ""

    def scroll_to_bottom(self):
        """Scroll to bottom"""
        pass

    def reload_css(self):
        """Reload CSS"""
        if self.loaded:
            to_json = json.dumps(self.prepare_styles())
            self.get_output_node().page().runJavaScript("updateCSS({});".format(to_json))
            if self.window.core.config.get('render.blocks'):
                self.get_output_node().page().runJavaScript("enableBlocks();")
            else:
                self.get_output_node().page().runJavaScript("disableBlocks();")

    def prepare_styles(self) -> str:
        """
        Prepare CSS styles

        :return: CSS styles
        """
        dark_styles = ["dracula", "fruity", "github-dark", "gruvbox-dark", "inkpot", "material", "monokai",
                       "native", "nord", "nord-darker", "one-dark", "paraiso-dark", "rrt", "solarized-dark",
                       "stata-dark", "vim", "zenburn"]
        style = self.window.core.config.get("render.code_syntax")
        if style is None or style == "":
            style = "default"
        fonts_path = os.path.join(self.window.core.config.get_app_path(), "data", "fonts").replace("\\", "/")
        stylesheet = self.window.controller.theme.markdown.get_web_css().replace('%fonts%', fonts_path)
        if style in dark_styles:
            stylesheet += "pre { color: #fff; }"
        else:
            stylesheet += "pre { color: #000; }"
        content = stylesheet + """
        """ + self.highlight.get_style_defs()
        return content

    def flush(self):
        """Flush output"""
        if self.loaded:
            return  # wait for page load

        classes = []
        classes_str = ""
        if self.window.core.config.get('render.blocks'):
            classes.append("display-blocks")
        if self.window.core.config.get('ctx.edit_icons'):
            classes.append("display-edit-icons")
        if self.is_timestamp_enabled():
            classes.append("display-timestamp")
        if classes:
            classes_str = ' class="' + " ".join(classes) + '"'

        js_dir = os.path.join(self.window.core.config.get_app_path(), "data", "js").replace("\\", "/")

        content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                """ + self.prepare_styles() + """
            </style>
        </head>
        <body """+classes_str+""">
        <div id="container">
            <div id="_nodes_" class="nodes empty_list"></div>
            <div id="_append_input_" class="append_input"></div>
            <div id="_append_output_" class="append_output"></div>
        </div>
        
        <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script type='text/javascript' src='qrc:///js/highlight.min.js'></script>
        <script>
        
        let scrollTimeout = null;
        let prevScroll = 0;
        let bridge;
        new QWebChannel(qt.webChannelTransport, function (channel) {
            bridge = channel.objects.bridge;
        });
        history.scrollRestoration = "manual";
        document.addEventListener('keydown', function(event) {
            if (event.ctrlKey && event.key === 'f') {
                window.location.href = 'bridge://open_find'; // send to bridge
                event.preventDefault();
            }
            if (event.key === 'Escape') {
                window.location.href = 'bridge://escape'; // send to bridge
                event.preventDefault();
            }
        });
        function highlightCode() {
            document.querySelectorAll('pre code').forEach(el => {
                if (!el.classList.contains('hljs')) hljs.highlightElement(el);
            });
        }
        function scrollToBottom() {
            getScrollPosition();  // store using bridge
            if (scrollTimeout !== null) {
                return;
            }
            if (document.body.scrollHeight > prevScroll) {
                scrollTimeout = setTimeout(function() {
                    window.scrollTo(0, document.body.scrollHeight);
                    prevScroll = document.body.scrollHeight;
                    getScrollPosition();  // store using bridge
                    scrollTimeout = null;
                }, 30);
            }
        }
        function appendToInput(content) {
            var element = document.getElementById('_append_input_');
            if (element) {
                element.innerHTML += content;
            }
            highlightCode();
            scrollToBottom();
        }
        function appendToOutput(bot_name, content) {
            var element = document.getElementById('_append_output_');
            if (element) {
                var box = element.querySelector('.msg-box');
                var msg;
                if (!box) {
                    box = document.createElement('div');
                    box.classList.add('msg-box');
                    box.classList.add('msg-bot');
                    var name = document.createElement('div');
                    name.classList.add('name-header');
                    name.classList.add('name-bot');
                    name.textContent = bot_name;
                    msg = document.createElement('div');
                    msg.classList.add('msg');
                    box.appendChild(name);
                    box.appendChild(msg);
                    element.appendChild(box);
                } else {
                    msg = box.querySelector('.msg');
                }
                if (msg) {
                    msg.innerHTML+= content;
                }
            }
            highlightCode();
            scrollToBottom();
        }
        function appendNode(content) {
            prevScroll = 0;
            var element = document.getElementById('_nodes_');
            if (element) {
                element.classList.remove('empty_list');
                element.innerHTML += content;
            }
            highlightCode();
            scrollToBottom();
        }
        function appendExtra(id, content) {
            prevScroll = 0;
            var element = document.getElementById('msg-bot-' + id);
            if (element) {
                var extra = element.querySelector('.msg-extra');
                if (extra) {
                    extra.innerHTML+= content;
                }
            }
            highlightCode();
            scrollToBottom();
        }
        function removeNode(id) {
            prevScroll = 0;
            var element = document.getElementById('msg-user-' + id);
            if (element) {
                element.remove();
            }
            var element = document.getElementById('msg-bot-' + id);
            if (element) {
                element.remove();
            }
            highlightCode();
            scrollToBottom();
        }
        function removeNodesFromId(id) {
            prevScroll = 0;
            var container = document.getElementById('_nodes_');
            if (container) {
                var elements = container.querySelectorAll('.msg-box');
                remove = false;
                elements.forEach(function(element) {
                    if (element.id.endsWith('-' + id)) {
                        remove = true;
                    }
                    if (remove) {
                        element.remove();
                    }
                });
            }
            highlightCode();
            scrollToBottom();
        }
        function replaceOutput(bot_name, content) {
            var element = document.getElementById('_append_output_');
            if (element) {
                var box = element.querySelector('.msg-box');
                var msg;
                if (!box) {
                    box = document.createElement('div');
                    box.classList.add('msg-box');
                    box.classList.add('msg-bot');
                    var name = document.createElement('div');
                    name.classList.add('name-header');
                    name.classList.add('name-bot');
                    name.textContent = bot_name;
                    msg = document.createElement('div');
                    msg.classList.add('msg');
                    box.appendChild(name);
                    box.appendChild(msg);
                    element.appendChild(box);
                } else {
                    msg = box.querySelector('.msg');
                }
                if (msg) {
                    msg.innerHTML = content;
                }
            }
            highlightCode();
            scrollToBottom();
        }
        function clearNodes() {
            prevScroll = 0;
            var element = document.getElementById('_nodes_');
            if (element) {
                element.textContent = '';
                element.classList.add('empty_list');
            }
        }
        function clearInput() {
            var element = document.getElementById('_append_input_');
            if (element) {
                element.textContent = '';
            }
        }
        function clearOutput() {
            var element = document.getElementById('_append_output_');
            if (element) {
                element.textContent = '';
            }
        }
        function enableEditIcons() {
            var container = document.body;
            if (container) {
                container.classList.add('display-edit-icons');
            }
        }
        function disableEditIcons() {
            var container = document.body;
            if (container) {
                container.classList.remove('display-edit-icons');
            }
        }
        function enableTimestamp() {
            var container = document.body;
            if (container) {
                container.classList.add('display-timestamp');
            }
        }
        function disableTimestamp() {
            var container = document.body;
            if (container) {
                container.classList.remove('display-timestamp');
            }
        }
        function enableBlocks() {
            var container = document.body;
            if (container) {
                container.classList.add('display-blocks');
            }
        }
        function disableBlocks() {
            var container = document.body;
            if (container) {
                container.classList.remove('display-blocks');
            }
        }
        function updateCSS(styles) {
            var style = document.createElement('style');
            style.innerHTML = styles;
            var oldStyle = document.querySelector('style');
            if (oldStyle) {
                oldStyle.remove();
            }
            document.head.appendChild(style);
        }
        function bridgeCopyCode(text) {
            if (bridge) {
                bridge.copy_text(text);
            }
        }
        function bridgeUpdateScrollPosition(pos) {
            if (bridge) {
                bridge.update_scroll_position(pos);
            }
        }
        function getScrollPosition() {
            pos = window.scrollY;
            bridgeUpdateScrollPosition(pos);
        }
        function setScrollPosition(pos) {
            window.scrollTo(0, pos);
            prevScroll = parseInt(pos);
        }  
        document.addEventListener('DOMContentLoaded', function() {
            var container = document.getElementById('container');
            function addClassToMsg(id, className) {
                var msgElement = document.getElementById('msg-bot-' + id);
                if (msgElement) {
                    msgElement.classList.add(className);
                }
            }
            function removeClassFromMsg(id, className) {
                var msgElement = document.getElementById('msg-bot-' + id);
                if (msgElement) {
                    msgElement.classList.remove(className);
                }
            }
            container.addEventListener('mouseover', function(event) {
                if (event.target.classList.contains('action-img')) {
                    var id = event.target.getAttribute('data-id');
                    addClassToMsg(id, 'msg-highlight');
                }
            });        
            container.addEventListener('mouseout', function(event) {
                if (event.target.classList.contains('action-img')) {
                    var id = event.target.getAttribute('data-id');
                    removeClassFromMsg(id, 'msg-highlight');
                }
            });
            container.addEventListener('click', function(event) {
                if (event.target.classList.contains('code-header-copy')) {
                    event.preventDefault();
                    var parent = event.target.closest('.code-wrapper');
                    var source = parent.querySelector('code');
                    if (source) {
                        var text = source.textContent || source.innerText;
                        bridgeCopyCode(text);
                    }                        
                }
            });
        });
        </script>
        </body>
        </html>
        """
        self.document = content
        self.get_output_node().setHtml(content, baseUrl="file://")

    def get_document(self, plain: bool = False):
        """
        Get document content

        :param plain: True if plain text
        :return: document content
        """
        if plain:
            return self.parser.to_plain_text(self.document.replace("<br>", "\n"))
        return self.document

    def clear_all(self):
        """Clear all"""
        self.clear_nodes()
        self.clear_chunks()
        self.html = ""

    def remove_item(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        try:
            self.get_output_node().page().runJavaScript("removeNode({});".format(id))
        except Exception as e:
            pass

    def remove_items_from(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        try:
            self.get_output_node().page().runJavaScript("removeNodesFromId({});".format(id))
        except Exception as e:
            pass

    def on_reply_submit(self, id: int):
        """
        On regenerate submit

        :param id: context item ID
        """
        # remove all items from ID
        self.remove_items_from(id)

    def on_edit_submit(self, id: int):
        """
        On regenerate submit

        :param id: context item ID
        """
        # remove all items from ID
        self.remove_items_from(id)

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            self.get_output_node().page().runJavaScript("enableEditIcons();")
        except Exception as e:
            pass

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            self.get_output_node().page().runJavaScript("disableEditIcons();")
        except Exception as e:
            pass

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            self.get_output_node().page().runJavaScript("enableTimestamp();")
        except Exception as e:
            pass

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            self.get_output_node().page().runJavaScript("disableTimestamp();")
        except Exception as e:
            pass

    # TODO: on lang change

    def on_theme_change(self):
        """On theme change"""
        self.window.controller.theme.markdown.load()
        if self.loaded:
            self.reload_css()
