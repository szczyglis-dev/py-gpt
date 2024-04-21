#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.20 06:00:00                  #
# ================================================== #
import json
import os
import re
import html
from datetime import datetime

from pygments.formatters.html import HtmlFormatter

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.item.ctx import CtxItem
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatWebOutput, CustomWebEnginePage
from pygpt_net.utils import trans
from .parser import Parser


class Renderer(BaseRenderer):
    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        Markdown renderer

        :param window: Window instance
        """
        self.window = window
        self.parser = Parser(window)
        self.images_appended = []
        self.urls_appended = []
        self.buffer = ""
        self.is_cmd = False
        self.img_width = 400
        self.html = ""

    def begin(self, stream: bool = False):
        """
        Render begin

        :param stream: True if it is a stream
        """
        self.parser.reset()
        #self.html = ""

    def end(self, stream: bool = False):
        """
        Render end

        :param stream: True if it is a stream
        """
        if stream:
            self.reload()  # reload ctx items only if stream
        self.flush()

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
        pass  # do nothing

    def clear_output(self):
        """Clear output"""
        self.reset()
        self.html = ""
        self.flush()

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def reset(self):
        """Reset"""
        self.images_appended = []
        self.urls_appended = []

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        if clear:
            self.clear_output()
        i = 0
        for item in items:
            item.idx = i
            if i == 0:
                item.first = True
            self.append_context_item(item)
            i += 1
        self.flush()

    def append_input(self, item: CtxItem, flush: bool = True):
        """
        Append text input to output

        :param item: context item
        :param flush: flush HTML
        """
        if not flush:
            self.append_chunk_input_start()

        if item.input is None or item.input == "":
            return
        if self.is_timestamp_enabled() \
                and item.input_timestamp is not None:
            name = ""
            if item.input_name is not None \
                    and item.input_name != "":
                name = item.input_name + ": "
            text = '{}: {}'.format(name, item.input)
        else:
            text = "{}".format(item.input)

        # check if it is a command response
        is_cmd = False
        if item.input.strip().startswith("[") \
                and item.input.strip().endswith("]"):
            is_cmd = True

        # hidden internal call
        if item.internal \
                and not is_cmd \
                and not item.first \
                and not item.input.strip().startswith("user: "):
            if flush:
                content = self.prepare_raw('>>>', "msg-user", item)
                self.append_input_chunk(item, content, True)
            else:
                self.append_raw('>>>', "msg-user", item)
            return
        else:
            # don't show user prefix if provided in internal call goal update
            if item.internal and item.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', item.input)

        if flush:
            content = self.prepare_raw(text.strip(), "msg-user", item)
            if self.is_stream():
                self.append_input_chunk(item, content, False)
            else:
                self.append_raw(text.strip(), "msg-user", item)
        else:
            self.append_raw(text.strip(), "msg-user", item)

    def append_output(self, item: CtxItem, flush: bool = True):
        """
        Append text output to output

        :param item: context item
        :param flush: flush HTML
        """
        if item.output is None or item.output == "":
            return
        if self.is_timestamp_enabled() \
                and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None \
                    and item.output_name != "":
                name = item.output_name + " "
            text = '{} {}'.format(name, item.output)
        else:
            text = "{}".format(item.output)
        self.append_raw(text.strip(), "msg-bot", item)

    def append_extra(self, item: CtxItem, footer: bool = False):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        :param footer: True if it is a footer
        """
        appended = []

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
                    self.append(self.get_image_html(image, n, c))
                    self.images_appended.append(image)
                    n+=1
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
                    self.append(self.get_file_html(file, n, c))
                    n+=1
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
                    n+=1
                except Exception as e:
                    pass
            if urls_html:
                self.append("<br/>" + "<br/>".join(urls_html))

        # extra action icons
        if footer:
            show_edit = self.window.core.config.get('ctx.edit_icons')
            icons_html = " ".join(self.get_action_icons(item, all=show_edit))
            if icons_html != "":
                extra = "<div class=\"action-icons\">{}</div>".format(icons_html)
                self.append(extra)
                self.to_end()

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if item.doc_ids is not None and len(item.doc_ids) > 0:
                try:
                    docs = self.get_docs_html(item.doc_ids)
                    self.append(docs)
                    self.to_end()
                except Exception as e:
                    pass

        # jump to end
        if len(appended) > 0:
            self.to_end()

        if not footer:
            self.flush()

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
                '<a href="extra-audio-read:{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    self.get_icon("audio", trans("ctx.extra.audio"))
                )
            )
            # copy item
            icons.append(
                '<a href="extra-copy:{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    self.get_icon("copy", trans("ctx.extra.copy"))
                )
            )
            # regen link
            icons.append(
                '<a href="extra-replay:{}"><span class="cmd">{}</span></a>'.format(
                    item.id,
                    self.get_icon("reload", trans("ctx.extra.reply"))
                )
            )
            if all:
                # edit link
                icons.append(
                    '<a href="extra-edit:{}"><span class="cmd">{}</span></a>'.format(
                        item.id,
                        self.get_icon("edit", trans("ctx.extra.edit"))
                    )
                )
                # delete link
                icons.append(
                    '<a href="extra-delete:{}"><span class="cmd">{}</span></a>'.format(
                        item.id,
                        self.get_icon("delete", trans("ctx.extra.delete"))
                    )
                )

                # join link
                if not self.window.core.ctx.is_first_item(item.id):
                    icons.append(
                        '<a href="extra-join:{}"><span class="cmd">{}</span></a>'.format(
                            item.id,
                            self.get_icon("join", trans("ctx.extra.join"))
                        )
                    )
        return icons

    def get_icon(self, icon: str, title: str = None) -> str:
        """
        Get icon

        :param icon: icon name
        :param title: icon title
        :return: icon HTML
        """
        icon = os.path.join(self.window.core.config.get_app_path(), "data", "icons", "chat", icon + ".png")
        return '<img src="file://{}" width="20" height="20" title="{}" alt="{}">'.format(icon, title, title)
        # return '<img src=":/icons/{}.svg" width="25" title="{}">'.format(icon, title)

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return

        raw_chunk = str(text_chunk)
        if begin:
            self.buffer = ""  # reset buffer
            self.is_cmd = False  # reset command flag
            self.append_chunk_start()

        self.buffer += raw_chunk
        chunk = self.format_chunk(text_chunk)
        escaped_chunk = json.dumps(chunk)
        try:
            self.get_output_node().page().runJavaScript(f"appendToOutput({escaped_chunk});")
        except Exception as e:
            pass
        self.scroll_to_bottom()

    def append_input_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return

        self.append_chunk_input_start()
        chunk = self.format_chunk(text_chunk)
        escaped_chunk = json.dumps(chunk)
        try:
            self.get_output_node().page().runJavaScript(f"appendToInput({escaped_chunk});")
        except Exception as e:
            pass
        #self.scroll_to_bottom()

    def append_block(self):
        """Append block to output"""
        pass

    def to_end(self):
        """Move cursor to end of output"""
        pass

    def prepare_raw(self, html: str, type: str = "msg-bot", item: CtxItem = None):
        if type != "msg-user":  # markdown for bot messages
            html = self.pre_format_text(html)
            html = self.append_timestamp(html, item)
            html = self.parser.parse(html)
        else:
            content = self.append_timestamp(self.format_user_text(html), item, type=type)
            html = "<p>" + content + "</p>"

        html = self.post_format_text(html)
        html = '<div class="{}">'.format(type) + html + "</div>"
        return html

    def append_raw(self, html: str, type: str = "msg-bot", item: CtxItem = None):
        """
        Append and format raw text to output

        :param html: text to append
        :param type: type of message
        :param item: CtxItem instance
        """
        html = self.prepare_raw(html, type, item)
        self.append(html)

    def append_chunk_start(self):
        """Append start of chunk to output"""
        js = "var element = document.getElementById('_append_output_');"
        js += "if (element) { element.innerHTML = ''; }"
        try:
            self.get_output_node().page().runJavaScript(js)
        except Exception as e:
            pass

    def append_chunk_input_start(self):
        """Append start of chunk to output"""
        js = "var element = document.getElementById('_append_input_');"
        js += "if (element) { element.innerHTML = ''; }"
        try:
            self.get_output_node().page().runJavaScript(js)
        except Exception as e:
            pass

    def append_context_item(self, item: CtxItem):
        """
        Append context item to output

        :param item: context item
        """
        self.append_input(item, flush=False)
        self.append_output(item, flush=False)
        self.append_extra(item, footer=True)

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
        return """<a href="{url}"><img src="{path}" width="{img_width}" class="image"></a>
        <p><b>{prefix}{num}:</b> <a href="{url}">{path}</a></p>""".\
            format(prefix=trans('chat.prefix.img'),
                   url=url,
                   path=path,
                   img_width=self.img_width,
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
        return """<b>{prefix}{num}:</b> <a href="{url}">{url}</a>""".\
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
        for doc_json in docs:
            try:
                """
                Example doc (file metadata):
                {'a2c7af6d-3c34-4c28-bf2d-6161e7fb525e': {
                    'file_path': '/home/user/.config/pygpt-net/data/my_cars.txt',
                    'file_name': '/home/user/.config/pygpt-net/data/my_cars.txt', 'file_type': 'text/plain',
                    'file_size': 28, 'creation_date': '2024-03-03', 'last_modified_date': '2024-03-03',
                    'last_accessed_date': '2024-03-03'}}
                """
                doc_id = list(doc_json.keys())[0]
                doc_parts = []
                for key in doc_json[doc_id]:
                    doc_parts.append("<b>{}:</b> {}".format(key, doc_json[doc_id][key]))
                html_sources += "[{}] {}: {}".format(num, doc_id, ", ".join(doc_parts))
                num +=1
            except Exception as e:
                pass

        if html_sources != "":
            html += "<p><b>{prefix}:</b></p>".format(prefix=trans('chat.prefix.doc'))
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
        return """<div><b>{prefix}{num}:</b> <a href="{url}">{path}</a></div>""".\
            format(prefix=trans('chat.prefix.file'),
                   url=url,
                   path=path,
                   num=num_str)

    def append(self, html: str, end: str = "\n"):
        """
        Append text to output

        :param html: HTML code
        :param end: end of the line character
        """
        self.html += html

    def append_timestamp(self, text: str, item: CtxItem, type: str = None) -> str:
        """
        Append timestamp to text

        :param text: Input text
        :param item: Context item
        :param type: Type of message
        :return: Text with timestamp (if enabled)
        """
        if item is not None \
                and self.is_timestamp_enabled() \
                and item.input_timestamp is not None:
            if type == "msg-user":
                timestamp = item.input_timestamp
            else:
                timestamp = item.output_timestamp
            if timestamp is not None:
                ts = datetime.fromtimestamp(timestamp)
                hour = ts.strftime("%H:%M:%S")
                text = '<span class="ts">{}:</span> {}'.format(hour, text)
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
            text = '<div class="cmd">&gt; {}</div><br/>'.format(text)
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

    def get_output_node(self) -> ChatWebOutput:
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

    def on_page_loaded(self):
        """On page loaded"""
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Scroll to bottom"""
        self.get_output_node().page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

    def flush(self):
        """Flush output"""
        style = self.window.core.config.get("render.code_syntax")
        if style is None or style == "":
            style = "default"
        css = self.window.controller.theme.markdown.get_web_css()
        fonts_path = os.path.join(self.window.core.config.get_app_path(), "data", "fonts").replace("\\", "/")
        content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @font-face {
                  font-family: "Lato";
                  src: url('file:///"""+fonts_path+"""/Lato/Lato-Regular.ttf');
                }
                @font-face {
                  font-family: "Monaspace Neon";
                  src: url('file:///"""+fonts_path+"""/MonaspaceNeon/MonaspaceNeon-Regular.otf');
                }
                body {
                    margin: 4px;
                }
                """+css+"""
                """+HtmlFormatter(style=style, cssclass='source', lineanchors='line').get_style_defs('.highlight')+"""
            </style>
        </head>
        <body>
            """+self.html+"""
            <div id="_append_input_" class="append_input"></div>
            <div id="_append_output_" class="append_output"></div>
        </body>
        <script>
        document.addEventListener('keydown', function(event) {
            if (event.ctrlKey && event.key === 'f') {
                window.location.href = 'bridge://open_find'; // send to bridge
                event.preventDefault();
            }
        });
        function appendToInput(content) {
            var element = document.getElementById('_append_input_');
            if (element) {
                element.innerHTML += content;
            }
            // scroll to bottom
        }
        function appendToOutput(content) {
            var element = document.getElementById('_append_output_');
            if (element) {
                element.innerHTML += content;
            }
            //  scroll to bottom
        }
        </script>
        </html>
        """
        self.get_output_node().setHtml(content, baseUrl="file://")

    def clear_all(self):
        """Clear all"""
        self.html = ""
        self.flush()
