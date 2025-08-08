#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.08 19:00:00                  #
# ================================================== #

import os
import random
from typing import Optional, List, Dict

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .syntax_highlight import SyntaxHighlight

import pygpt_net.js_rc
import pygpt_net.css_rc
import pygpt_net.fonts_rc

class Body:

    NUM_TIPS = 13

    def __init__(self, window=None):
        """
        HTML Body

        :param window: Window instance
        """
        self.window = window
        self.highlight = SyntaxHighlight(window)

    def is_timestamp_enabled(self) -> bool:
        """
        Check if timestamp is enabled

        :return: True if timestamp is enabled
        """
        return self.window.core.config.get('output_timestamp')

    def prepare_styles(self) -> str:
        """
        Prepare CSS styles

        :return: CSS styles
        """
        syntax_dark = [
            "dracula",
            "fruity",
            "github-dark",
            "gruvbox-dark",
            "inkpot",
            "material",
            "monokai",
            "native",
            "nord",
            "nord-darker",
            "one-dark",
            "paraiso-dark",
            "rrt",
            "solarized-dark",
            "stata-dark",
            "vim",
            "zenburn",
        ]
        syntax_style = self.window.core.config.get("render.code_syntax")
        if syntax_style is None or syntax_style == "":
            syntax_style = "default"
        fonts_path = os.path.join(self.window.core.config.get_app_path(), "data", "fonts").replace("\\", "/")
        # loader
        stylesheet = """
        .lds-ring {
          /* change color here */
          color: #1c4c5b
        }
        .lds-ring,
        .lds-ring div {
          box-sizing: border-box;
        }
        .lds-ring {
          display: inline-block;
          position: relative;
          width: 80px;
          height: 80px;
        }
        .lds-ring div {
          box-sizing: border-box;
          display: block;
          position: absolute;
          width: 64px;
          height: 64px;
          margin: 8px;
          border: 8px solid currentColor;
          border-radius: 50%;
          animation: lds-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
          border-color: currentColor transparent transparent transparent;
        }
        .lds-ring div:nth-child(1) {
          animation-delay: -0.45s;
        }
        .lds-ring div:nth-child(2) {
          animation-delay: -0.3s;
        }
        .lds-ring div:nth-child(3) {
          animation-delay: -0.15s;
        }
        @keyframes lds-ring {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
        """
        stylesheet += self.window.controller.theme.markdown.get_web_css().replace('%fonts%', fonts_path)
        if syntax_style in syntax_dark:
            stylesheet += "pre { color: #fff; }"
        else:
            stylesheet += "pre { color: #000; }"

        return stylesheet + " " + self.highlight.get_style_defs()

    def prepare_action_icons(
            self,
            ctx: CtxItem
    ) -> str:
        """
        Append action icons

        :param ctx: context item
        :return: HTML code
        """
        html = ""
        show_edit = True
        # show_edit = self.window.core.config.get('ctx.edit_icons')
        icons_html = "".join(self.get_action_icons(ctx, all=show_edit))
        if icons_html != "":
            extra = "<div class=\"action-icons\" data-id=\"{}\">{}</div>".format(ctx.id, icons_html)
            html += extra
        return html

    def get_action_icons(
            self,
            ctx: CtxItem,
            all: bool = False
    ) -> List[str]:
        """
        Get action icons for context item

        :param ctx: context item
        :param all: True to show all icons
        :return: list of icons
        """
        icons = []

        # audio read
        if ctx.output is not None and ctx.output != "":
            icons.append(
                '<a href="extra-audio-read:{}" class="action-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    ctx.id,
                    self.get_icon("volume", trans("ctx.extra.audio"), ctx)
                )
            )
            # copy ctx
            icons.append(
                '<a href="extra-copy:{}" class="action-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    ctx.id,
                    self.get_icon("copy", trans("ctx.extra.copy"), ctx)
                )
            )
            # regen link
            icons.append(
                '<a href="extra-replay:{}" class="action-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    ctx.id,
                    self.get_icon("reload", trans("ctx.extra.reply"), ctx)
                )
            )
            # edit link
            icons.append(
                '<a href="extra-edit:{}" class="action-icon edit-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    ctx.id,
                    self.get_icon("edit", trans("ctx.extra.edit"), ctx)
                )
            )
            # delete link
            icons.append(
                '<a href="extra-delete:{}" class="action-icon edit-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                    ctx.id,
                    ctx.id,
                    self.get_icon("delete", trans("ctx.extra.delete"), ctx)
                )
            )

            # join link
            if not self.window.core.ctx.is_first_item(ctx.id):
                icons.append(
                    '<a href="extra-join:{}" class="action-icon edit-icon" data-id="{}" role="button"><span class="cmd">{}</span></a>'.format(
                        ctx.id,
                        ctx.id,
                        self.get_icon("playlist_add", trans("ctx.extra.join"), ctx)
                    )
                )
        return icons

    def get_icon(
            self,
            icon: str,
            title: Optional[str] = None,
            item: Optional[CtxItem] = None
    ) -> str:
        """
        Get icon

        :param icon: icon name
        :param title: icon title
        :param item: context item
        :return: icon HTML
        """
        icon = os.path.join(self.window.core.config.get_app_path(), "data", "icons", icon + ".svg")
        return '<img src="file://{}" class="action-img" title="{}" alt="{}" data-id="{}">'.format(
            icon, title, title, item.id)

    def get_image_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
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
        basename = os.path.basename(path)
        return """<div class="extra-src-img-box" title="{url}"><div class="img-outer"><div class="img-wrapper"><a href="{url}"><img src="{path}" class="image"></a></div>
        <a href="{url}" class="title">{title}</a></div></div>""". \
            format(prefix=trans('chat.prefix.img'),
                   url=url,
                   title=basename,
                   path=path,
                   num=num_str)

    def get_url_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get URL HTML

        :param url: external URL
        :param num: number of URL
        :param num_all: number of all URLs
        :return: HTML code
        """
        icon_path = os.path.join(
            self.window.core.config.get_app_path(),
            "data", "icons", "language.svg"
        )
        icon = '<img src="file://{}" class="extra-src-icon">'.format(icon_path)
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        return """{icon}<a href="{url}" title="{url}">{url}</a> <small>{num}</small>""". \
            format(url=url,
                   num=num_str,
                   icon=icon,
            )

    def get_docs_html(self, docs: List[Dict]) -> str:
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

        icon_path = os.path.join(
            self.window.core.config.get_app_path(),
            "data", "icons", "db.svg"
        )
        icon = '<img src="file://{}" class="extra-src-icon">'.format(icon_path)
        if html_sources != "":
            html += "<p>{icon}<small><b>{prefix}:</b></small></p>".format(
                prefix=trans('chat.prefix.doc'),
                icon=icon,
            )
            html += "<div class=\"cmd\">"
            html += "<p>" + html_sources + "</p>"
            html += "</div> "
        return html

    def get_file_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get file HTML

        :param url: URL to file
        :param num: number of file
        :param num_all: number of all files
        :return: HTML code
        """
        icon_path = os.path.join(
            self.window.core.config.get_app_path(),
            "data", "icons", "attachments.svg"
        )
        icon = '<img src="file://{}" class="extra-src-icon">'.format(icon_path)
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """{icon} <b>{num}</b> <a href="{url}">{path}</a>""". \
            format(url=url,
                   path=path,
                   num=num_str,
                   icon=icon,
            )

    def prepare_tool_extra(self, ctx: CtxItem) -> str:
        """
        Prepare footer extra

        :param ctx: context item
        :return: HTML code
        """
        html = ""
        if ctx.extra is not None and ctx.extra != "":
            html += "<div class=\"msg-extra\">"

            # single tool
            if "plugin" in ctx.extra:
                event = Event(Event.TOOL_OUTPUT_RENDER, {
                    'tool': ctx.extra["plugin"],
                    'html': '',
                    'multiple': False,
                    'content': ctx.extra,  # tool output
                })
                event.ctx = ctx
                self.window.dispatch(event, all=True)  # handle by plugins
                if event.data['html']:
                    html += "<div class=\"tool-output-block\">" + event.data['html'] + "</div>"

            # multiple tools, list
            elif "tool_output" in ctx.extra and isinstance(ctx.extra["tool_output"], list):
                for key, tool in enumerate(ctx.extra["tool_output"]):
                    if "plugin" not in tool:
                        continue
                    event = Event(Event.TOOL_OUTPUT_RENDER, {
                        'tool': tool["plugin"],
                        'html': '',
                        'multiple': True,
                        'content': tool,  # tool output[]
                    })
                    event.ctx = ctx
                    self.window.dispatch(event, all=True)
                    if event.data['html']:
                        html += "<div class=\"tool-output-block\">" + event.data['html'] + "</div>"
            html += "</div>"
        return html

    def get_all_tips(self) -> str:
        """
        Generuje listę wszystkich tipów jako elementy HTML,
        tasuje je i zwraca jako string JSON.
        """
        if not self.window.core.config.get("layout.tooltips", False):
            return "[]"
        tips_list = []
        for i in range(1, self.NUM_TIPS + 1):
            tip_html = "<p><b>" + trans("output.tips.prefix") + "</b>: " + trans("output.tips." + str(i)) + "</p>"
            tips_list.append(tip_html)
        random.shuffle(tips_list)
        import json
        return json.dumps(tips_list)

    def get_html(self, pid: int) -> str:
        """
        Build webview HTML code

        :return: HTML code
        """
        tips_json = self.get_all_tips()
        classes = []
        classes_str = ""
        style = self.window.core.config.get("theme.style", "blocks")
        if self.window.core.config.get('render.blocks'):
            classes.append("display-blocks")
        if self.window.core.config.get('ctx.edit_icons'):
            classes.append("display-edit-icons")
        if self.is_timestamp_enabled():
            classes.append("display-timestamp")
        classes.append("theme-" + style)
        if classes:
            classes_str = ' class="' + " ".join(classes) + '"'

        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                """ + self.prepare_styles() + """
            </style>
            <link rel="stylesheet" href="qrc:///css/katex.min.css">
            <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script type="text/javascript" src="qrc:///js/highlight.min.js"></script>
            <script type="text/javascript" src="qrc:///js/katex.min.js"></script>
            <script type="text/javascript" src="qrc:///js/auto-render.min.js"></script>
            <script>
        
            let scrollTimeout = null;
            let prevScroll = 0;
            let bridge;
            let pid = """ + str(pid) + """
            new QWebChannel(qt.webChannelTransport, function (channel) {
                bridge = channel.objects.bridge;
            });
            let collapsed_idx = [];
            let domOutputStream = document.getElementById('_append_output_');
            let domOutput = document.getElementById('_output_');
            let domInput = document.getElementById('_input_');
            let domLastCodeBlock = null;
            let domLastParagraphBlock = null;
            let htmlBuffer = "";
            let tips = """ + tips_json + """;
            let tips_hidden = false;
        
            history.scrollRestoration = "manual";
            document.addEventListener('keydown', function(event) {
                if (event.ctrlKey && event.key === 'f') {
                    window.location.href = 'bridge://open_find:' + pid; // send to bridge
                    event.preventDefault();
                }
                if (event.key === 'Escape') {
                    window.location.href = 'bridge://escape'; // send to bridge
                    event.preventDefault();
                }
            });
            document.addEventListener('click', function(event) {
                if (event.target.tagName !== 'A' && !event.target.closest('a')) {
                    window.location.href = 'bridge://focus';
                }
            });
            function log(text) {
                if (bridge) {
                    bridge.log(text);
                }
            }
            function prepare() {        
                collapsed_idx = [];  // clear collapsed code
                hideTips();
            }
            function sanitize(content) {
                var parser = new DOMParser();
                var doc = parser.parseFromString(content, "text/html");
                var codeElements = doc.querySelectorAll('code, pre');
                codeElements.forEach(function(element) {
                    var html = element.outerHTML;
                    var newHtml = html.replace(/&amp;lt;/g, '<').replace(/&amp;gt;/g, '>');
                    element.outerHTML = newHtml;
                });
                return doc.documentElement.outerHTML;
            }
            function highlightCode(withMath = true) {
                document.querySelectorAll('pre code').forEach(el => {
                    if (!el.classList.contains('hljs')) hljs.highlightElement(el);
                });
                if (withMath) {
                    renderMath();
                }  
                restoreCollapsedCode();   
            }
            function hideTips() {
                if (tips_hidden) return;
                document.getElementById('tips').style.display = 'none';
                tips_hidden = true;
            }
            function showTips() {
                if (tips_hidden) return;
                if (tips.length === 0) return;
                document.getElementById('tips').style.display = 'block';
                tips_hidden = false;
            }    
            function cycleTips() {
                if (tips_hidden) return;
                if (tips.length === 0) return;
                let tipContainer = document.getElementById('tips');
                let currentTip = 0;
                function showNextTip() {
                    if (tips_hidden) return;
                    tipContainer.innerHTML = tips[currentTip];
                    tipContainer.classList.add('visible');    
                    setTimeout(function() {
                        if (tips_hidden) return;
                        tipContainer.classList.remove('visible');
                        setTimeout(function(){
                            currentTip = (currentTip + 1) % tips.length;
                            showNextTip();
                        }, 1000);
                    }, 10000);
                }
                showNextTip();
            }
            function renderMath() {
                  const scripts = document.querySelectorAll('script[type^="math/tex"]');
                  scripts.forEach(function(script) {
                    const displayMode = script.type.indexOf('mode=display') > -1;
                    const mathContent = script.textContent || script.innerText;
                    const element = document.createElement(displayMode ? 'div' : 'span');
                    try {
                      katex.render(mathContent, element, {
                        displayMode: displayMode,
                        throwOnError: false
                      });
                    } catch (err) {
                      element.textContent = mathContent;
                    }
                    script.parentNode.replaceChild(element, script);
                  });
            }
            function scrollToBottom() {
                window.scrollTo(0, document.body.scrollHeight);
                prevScroll = document.body.scrollHeight;
                getScrollPosition();  // store using bridge
            }
            function appendToInput(content) {
                const element = document.getElementById('_append_input_');
                if (element) {
                    element.insertAdjacentHTML('beforeend', sanitize(content));
                }
                highlightCode();
                scrollToBottom();
            }
            function appendToOutput(bot_name, content) {
                hideTips();
                const element = document.getElementById('_append_output_');
                if (element) {
                    let box = element.querySelector('.msg-box');
                    let msg;
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
                        msg.insertAdjacentHTML('beforeend', sanitize(content));
                    }
                }
                highlightCode();
                scrollToBottom();
            }
            function appendNode(content) {
                clearStreamBefore();
                prevScroll = 0;
                const element = document.getElementById('_nodes_');
                if (element) {
                    element.classList.remove('empty_list');
                    element.insertAdjacentHTML('beforeend', sanitize(content));
                }
                highlightCode();
                scrollToBottom();
            }
            function appendExtra(id, content) {
                hideTips();
                prevScroll = 0;
                const element = document.getElementById('msg-bot-' + id);
                if (element) {
                    const extra = element.querySelector('.msg-extra');
                    if (extra) {
                        extra.insertAdjacentHTML('beforeend', sanitize(content));
                    }
                }
                highlightCode();
                scrollToBottom();
            }
            function removeNode(id) {
                prevScroll = 0;
                let element = document.getElementById('msg-user-' + id);
                if (element) {
                    element.remove();
                }
                element = document.getElementById('msg-bot-' + id);
                if (element) {
                    element.remove();
                }
                highlightCode();
                scrollToBottom();
            }
            function removeNodesFromId(id) {
                prevScroll = 0;
                const container = document.getElementById('_nodes_');
                if (container) {
                    const elements = container.querySelectorAll('.msg-box');
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
            function getStreamContainer() {
                let element;
                if (domOutputStream) {
                    element = domOutputStream;
                } else {            
                    element = document.getElementById('_append_output_');
                    if (element) {
                        domOutputStream = element;
                    }
                }  
                return element;
            }        
            function clearStream() {
                hideTips();
                domLastParagraphBlock = null;
                domLastCodeBlock = null;
                domOutputStream = null;
                const element = getStreamContainer();
                let msg;
                if (element) {
                    let box = element.querySelector('.msg-box');
                    let msg;
                    if (!box) {
                        box = document.createElement('div');
                        box.classList.add('msg-box');
                        box.classList.add('msg-bot');
                        const name = document.createElement('div');
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
                        msg.innerHTML = ''; // clear previous content
                    }
                }
            }
            function beginStream() {
                hideTips();
                clearOutput();
            }
            function endStream() {
                clearOutput();
            }
            function appendStream(bot_name, content, chunk, replace = false, is_code_block = false) {
                hideTips();
                const element = getStreamContainer();
                doHighlight = true;
                doMath = true;
                let msg;
                if (element) {
                    let box = element.querySelector('.msg-box');
                    let msg;
                    if (!box) {
                        box = document.createElement('div');
                        box.classList.add('msg-box');
                        box.classList.add('msg-bot');
                        const name = document.createElement('div');
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
                        if (replace) {
                            msg.innerHTML = sanitize(content);
                            domLastCodeBlock = null; // reset last code block
                            domLastParagraphBlock = null; // reset last paragraph block
                        } else {
                            if (is_code_block) {
                                let lastCodeBlock;
                                if (domLastCodeBlock) {
                                    lastCodeBlock = domLastCodeBlock;
                                } else {
                                    // find last code block in the message
                                    const msgBlocks = msg.querySelectorAll('pre');
                                    if (msgBlocks.length > 0) {
                                        lastCodeBlock = msgBlocks[msgBlocks.length - 1].querySelector('code');
                                    }
                                }
                                if (lastCodeBlock) {
                                    // append to last code block
                                    lastCodeBlock.insertAdjacentHTML('beforeend', chunk);
                                    domLastCodeBlock = lastCodeBlock;
                                    doHighlight = false;
                                } else {
                                    // if no code block, append chunk as normal text
                                    msg.insertAdjacentHTML('beforeend', chunk); // append chunk
                                    domLastCodeBlock = null; // reset last code block
                                }
                                doMath = false; // disable math rendering for code blocks
                            } else {
                                domLastCodeBlock = null; // reset last code block
                                if (msg.innerHTML.trim().endsWith('</p>')) {
                                    let lastParagraphBlock;
                                    if (domLastParagraphBlock) {
                                        lastParagraphBlock = domLastParagraphBlock;
                                    } else {
                                        const blocksParagraph = msg.querySelectorAll('p');
                                        if (blocksParagraph.length > 0) {
                                            lastParagraphBlock = blocksParagraph[blocksParagraph.length - 1];
                                        }
                                    }
                                    if (lastParagraphBlock) {
                                        domLastParagraphBlock = lastParagraphBlock; // store last paragraph block
                                        lastParagraphBlock.insertAdjacentHTML('beforeend', chunk); // append to last paragraph
                                    } else {
                                        domLastParagraphBlock = null; // reset last paragraph block
                                        msg.insertAdjacentHTML('beforeend', chunk); // append chunk
                                    }                                        
                                } else {
                                    domLastParagraphBlock = null; // reset last paragraph block
                                    msg.insertAdjacentHTML('beforeend', chunk); // append chunk
                                }
                                doHighlight = false;
                            }
                        }
                    }
                }
                if (replace) {
                    if (doHighlight) {
                        highlightCode(doMath);  // with or without math
                    }
                    scrollToBottom();
                }    
            }
            function replaceOutput(bot_name, content) {
                hideTips();
                const element = getStreamContainer();
                if (element) {
                    let box = element.querySelector('.msg-box');
                    let msg;
                    if (!box) {
                        box = document.createElement('div');
                        box.classList.add('msg-box');
                        box.classList.add('msg-bot');
                        const name = document.createElement('div');
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
                        msg.innerHTML = sanitize(content);
                    }
                }
                highlightCode();
                scrollToBottom();
            }
            function nextStream() {
                hideTips();
                // Clear the current stream output and copy it to the before output
                // 1. copy current output from _append_output_ to _append_output_before_
                // 2. clear _append_output_
                const element = document.getElementById('_append_output_');
                const elementBefore = document.getElementById('_append_output_before_');
                if (element && elementBefore) {
                    elementBefore.insertAdjacentHTML('beforeend', element.innerHTML);
                    element.innerHTML = ''; // clear current output
                    domLastCodeBlock = null; // reset last code block
                    domLastParagraphBlock = null; // reset last paragraph block
                    scrollToBottom();
                }
            }
            function clearStreamBefore() {
                hideTips();
                const element = document.getElementById('_append_output_before_');
                if (element) {
                    element.innerHTML = ''; // clear previous content
                }
            }
            function replaceOutput(bot_name, content) {     
                hideTips();   
                const element = getStreamContainer();
                if (element) {
                    let box = element.querySelector('.msg-box');
                    let msg;
                    if (!box) {
                        box = document.createElement('div');
                        box.classList.add('msg-box');
                        box.classList.add('msg-bot');
                        const name = document.createElement('div');
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
                        msg.innerHTML = sanitize(content);
                    }
                }
                highlightCode();
                scrollToBottom();
            }
            function appendToolOutput(content) {
                hideToolOutputLoader();
                enableToolOutput();
                const elements = document.querySelectorAll('.tool-output');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    const contentEl = last.querySelector('.content');
                    if (contentEl) {
                        contentEl.insertAdjacentHTML('beforeend', sanitize(content));
                    }
                }
            }
            function updateToolOutput(content) {
                hideToolOutputLoader();
                enableToolOutput();
                const elements = document.querySelectorAll('.tool-output');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    const contentEl = last.querySelector('.content');
                    if (contentEl) {
                        contentEl.innerHTML = sanitize(content);
                    }
                }
            }
            function clearToolOutput(content) {
                hideToolOutputLoader();
                enableToolOutput();
                const elements = document.querySelectorAll('.tool-output');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    const contentEl = last.querySelector('.content');
                    if (contentEl) {
                        contentEl.innerHTML = '';
                    }
                }
            }
            function showToolOutputLoader() {
                return; // disabled
                const elements = document.querySelectorAll('.msg-bot');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    const contentEl = last.querySelector('.spinner');
                    if (contentEl) {
                        contentEl.style.display = 'inline-block';
                    }
                }
            }
            function hideToolOutputLoader() {
                const elements = document.querySelectorAll('.msg-bot');
                // hide all loaders
                if (elements.length > 0) {
                    elements.forEach(function(element) {
                        const contentEl = element.querySelector('.spinner');
                        if (contentEl) {
                            contentEl.style.display = 'none';
                        }
                    });
                }
            }
            function beginToolOutput() {
                showToolOutputLoader();
            }
            function endToolOutput() {
                hideToolOutputLoader();
            }
            function enableToolOutput() {
                const elements = document.querySelectorAll('.tool-output');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    last.style.display = 'block';
                }
            }
            function disableToolOutput() {
                const elements = document.querySelectorAll('.tool-output');
                if (elements.length > 0) {
                    const last = elements[elements.length - 1];
                    last.style.display = 'none';
                }
            }
            function toggleToolOutput(id) {
                const element = document.getElementById('msg-bot-' + id);
                if (element) {
                    const outputEl = element.querySelector('.tool-output');
                    if (outputEl) {
                        const contentEl = outputEl.querySelector('.content');
                        if (contentEl.style.display === 'none') {
                            contentEl.style.display = 'block';
                        } else {
                            contentEl.style.display = 'none';
                        }
                        const toggleEl = outputEl.querySelector('.toggle-cmd-output img');
                        if (toggleEl) {
                            toggleEl.classList.toggle('toggle-expanded');
                        }
                    }
                }
            }
            function replaceLive(content) {
                const element = document.getElementById('_append_live_');
                if (element) {
                    if (element.classList.contains('hidden')) {
                        element.classList.remove('hidden');
                        element.classList.add('visible');
                    }
                    element.innerHTML = sanitize(content);
                }
                highlightCode();
                scrollToBottom();
            }
            function updateFooter(content) {
                const element = document.getElementById('_footer_');
                if (element) {
                    element.innerHTML = content;
                }
            }
            function clearNodes() {
                prevScroll = 0;
                clearStreamBefore();
                const element = document.getElementById('_nodes_');
                if (element) {
                    element.innerHTML = '';
                    element.classList.add('empty_list');
                }
            }
            function clearInput() {
                const element = document.getElementById('_append_input_');
                if (element) {
                    element.innerHTML = '';
                }
            }
            function clearOutput() {
                clearStreamBefore();
                domLastCodeBlock = null;
                domLastParagraphBlock = null;
                const element = document.getElementById('_append_output_');
                if (element) {
                    element.innerHTML = '';
                }
            }
            function clearLive() {
                const element = document.getElementById('_append_live_');
                if (element) {
                    if (element.classList.contains('visible')) {
                        element.classList.remove('visible');
                        element.classList.add('hidden');
                        // timeout to clear content
                        setTimeout(function() {
                            element.innerHTML = '';
                        }, 1000);
                    } else {
                        element.innerHTML = '';
                    }
                }
            }
            function enableEditIcons() {
                const container = document.body;
                if (container) {
                    container.classList.add('display-edit-icons');
                }
            }
            function disableEditIcons() {
                const container = document.body;
                if (container) {
                    container.classList.remove('display-edit-icons');
                }
            }
            function enableTimestamp() {
                const container = document.body;
                if (container) {
                    container.classList.add('display-timestamp');
                }
            }
            function disableTimestamp() {
                const container = document.body;
                if (container) {
                    container.classList.remove('display-timestamp');
                }
            }
            function enableBlocks() {
                const container = document.body;
                if (container) {
                    container.classList.add('display-blocks');
                }
            }
            function disableBlocks() {
                const container = document.body;
                if (container) {
                    container.classList.remove('display-blocks');
                }
            }
            function updateCSS(styles) {
                const style = document.createElement('style');
                style.innerHTML = styles;
                const oldStyle = document.querySelector('style');
                if (oldStyle) {
                    oldStyle.remove();
                }
                document.head.appendChild(style);
            }
            function restoreCollapsedCode() {
                const codeWrappers = document.querySelectorAll('.code-wrapper');
                codeWrappers.forEach(function(wrapper) {
                    const index = wrapper.getAttribute('data-index');
                    const localeCollapse = wrapper.getAttribute('data-locale-collapse');
                    const localeExpand = wrapper.getAttribute('data-locale-expand');
                    const source = wrapper.querySelector('code');                
                    if (source && collapsed_idx.includes(index)) {
                        source.style.display = 'none';
                        const collapseBtn = wrapper.querySelector('.code-header-collapse');                    
                        if (collapseBtn) {
                            const collapseSpan = collapseBtn.querySelector('span');
                            if (collapseSpan) {
                                collapseSpan.textContent = localeExpand;
                            }
                            collapseBtn.classList.add('collapsed');
                        }
                    } else if (source) {
                        source.style.display = 'block';
                        const collapseBtn = wrapper.querySelector('.code-header-collapse');
                        if (collapseBtn) {
                            const collapseSpan = collapseBtn.querySelector('span');
                            if (collapseSpan) {
                                collapseSpan.textContent = localeCollapse;
                            }
                            collapseBtn.classList.remove('collapsed');
                        }
                    }
                });
            }
            function bridgeCopyCode(text) {
                if (bridge) {
                    bridge.copy_text(text);
                }
            }
            function bridgePreviewCode(text) {
                if (bridge) {
                    bridge.preview_text(text);
                }
            }
            function bridgeRunCode(text) {
                if (bridge) {
                    bridge.run_text(text);
                }
            }
            function bridgeUpdateScrollPosition(pos) {
                if (bridge) {
                    bridge.update_scroll_position(pos);
                }
            }
            function getScrollPosition() {
                bridgeUpdateScrollPosition(window.scrollY);
            }
            function setScrollPosition(pos) {
                window.scrollTo(0, pos);
                prevScroll = parseInt(pos);
            }  
            function showLoading() {
                hideTips();
                const el = document.getElementById('_loader_');
                if (el) {
                    if (el.classList.contains('hidden')) {
                        el.classList.remove('hidden');
                    }
                    el.classList.add('visible');
                }
            }
            function hideLoading() {
                const el = document.getElementById('_loader_');
                if (el) {
                    if (el.classList.contains('visible')) {
                        el.classList.remove('visible');
                    }
                    el.classList.add('hidden');
                }
            }
            document.addEventListener('DOMContentLoaded', function() {
                const container = document.getElementById('container');
                function addClassToMsg(id, className) {
                    const msgElement = document.getElementById('msg-bot-' + id);
                    if (msgElement) {
                        msgElement.classList.add(className);
                    }
                }
                function removeClassFromMsg(id, className) {
                    const msgElement = document.getElementById('msg-bot-' + id);
                    if (msgElement) {
                        msgElement.classList.remove(className);
                    }
                }
                container.addEventListener('mouseover', function(event) {
                    if (event.target.classList.contains('action-img')) {
                        const id = event.target.getAttribute('data-id');
                        addClassToMsg(id, 'msg-highlight');
                    }
                });        
                container.addEventListener('mouseout', function(event) {
                    if (event.target.classList.contains('action-img')) {
                        const id = event.target.getAttribute('data-id');
                        removeClassFromMsg(id, 'msg-highlight');
                    }
                });
                container.addEventListener('click', function(event) {
                    // btn copy
                    const copyButton = event.target.closest('.code-header-copy');
                    if (copyButton) {
                        event.preventDefault();
                        const parent = event.target.closest('.code-wrapper');
                        const source = parent.querySelector('code');
                        const localeCopy = parent.getAttribute('data-locale-copy');
                        const localeCopied = parent.getAttribute('data-locale-copied');
                        if (source) {
                            const text = source.textContent || source.innerText;
                            bridgeCopyCode(text);
                            const copySpan = copyButton.querySelector('span');
                            if (copySpan) {
                                copySpan.textContent = localeCopied;
                                setTimeout(function() {
                                    copySpan.textContent = localeCopy;
                                }, 1000);
                            }
                        }                        
                    }            
                    // btn run
                    const runButton = event.target.closest('.code-header-run');
                    if (runButton) {
                        event.preventDefault();
                        const parent = event.target.closest('.code-wrapper');
                        const source = parent.querySelector('code');
                        if (source) {
                            const text = source.textContent || source.innerText;
                            bridgeRunCode(text);
                        }                        
                    }    
                    // btn preview
                    const previewButton = event.target.closest('.code-header-preview');
                    if (previewButton) {
                        event.preventDefault();
                        const parent = event.target.closest('.code-wrapper');
                        const source = parent.querySelector('code');
                        if (source) {
                            const text = source.textContent || source.innerText;
                            bridgePreviewCode(text);
                        }                        
                    }
                    // btn collapse
                    const collapseButton = event.target.closest('.code-header-collapse');
                    if (collapseButton) {
                        event.preventDefault();
                        const parent = collapseButton.closest('.code-wrapper');
                        const index = parent.getAttribute('data-index');
                        const source = parent.querySelector('code');
                        const localeCollapse = parent.getAttribute('data-locale-collapse');
                        const localeExpand = parent.getAttribute('data-locale-expand');
                        if (source) {
                            if (source.style.display === 'none') {
                                source.style.display = 'block';
                                collapseButton.classList.remove('collapsed');
                                const idx = collapsed_idx.indexOf(index);
                                if (idx !== -1) {
                                    collapsed_idx.splice(idx, 1);
                                    const collapseSpan = collapseButton.querySelector('span');
                                    if (collapseSpan) {
                                        collapseSpan.textContent = localeCollapse;
                                    }
                                }
                            } else {
                                source.style.display = 'none';
                                collapseButton.classList.add('collapsed');
                                if (!collapsed_idx.includes(index)) {
                                    collapsed_idx.push(index);
                                    const collapseSpan = collapseButton.querySelector('span');
                                    if (collapseSpan) {
                                        collapseSpan.textContent = localeExpand;
                                    }
                                }
                            }
                        }
                    }
                });
            });
            setTimeout(cycleTips, 4000);
            </script>
        </head>
        <body """ + classes_str + """>
        <div id="container">
            <div id="_nodes_" class="nodes empty_list"></div>
            <div id="_append_input_" class="append_input"></div>
            <div id="_append_output_before_" class="append_output"></div>
            <div id="_append_output_" class="append_output"></div>            
            <div id="_append_live_" class="append_live hidden"></div>
            <div id="_footer_" class="footer"></div>
            <div id="_loader_" class="loader-global hidden">
                <div class="lds-ring"><div></div><div></div><div></div><div></div></div>
            </div>
            <div id="tips" class="tips"></div>
        </div>
        </body>
        </html>
        """
