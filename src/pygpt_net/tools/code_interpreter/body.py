#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.19 07:00:00                  #
# ================================================== #

import os

from pygpt_net.core.render.web.syntax_highlight import SyntaxHighlight


class Body:

    def __init__(self, window=None):
        """
        HTML Body

        :param window: Window instance
        """
        self.window = window
        self.highlight = SyntaxHighlight(window)

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

        stylesheet += """
          body {max-width: 100%; } 
          pre { margin-top: 0; margin-bottom: 0.25rem; } 
          a:hover { cursor: pointer; }
          .output-image { max-width: 100%; height: auto; }
        """
        return stylesheet + " " + self.highlight.get_style_defs()

    def get_html(self, pid: int) -> str:
        """
        Build webview HTML code

        :return: HTML code
        """
        classes = []
        classes_str = ""
        style = self.window.core.config.get("theme.style", "blocks")
        if self.window.core.config.get('render.blocks'):
            classes.append("display-blocks")
        if self.window.core.config.get('ctx.edit_icons'):
            classes.append("display-edit-icons")
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
        <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script type="text/javascript" src="qrc:///js/highlight.min.js"></script>
        <script type="text/javascript" src="qrc:///js/auto-render.min.js"></script>
        <script>

        let scrollTimeout = null;
        let prevScroll = 0;
        let bridge;
        let pid = """ + str(pid) + """
        new QWebChannel(qt.webChannelTransport, function (channel) {
            bridge = channel.objects.bridge;
        });
        history.scrollRestoration = "manual";
        document.addEventListener('keydown', function(event) {
            if (event.ctrlKey && event.key === 'f') {
                //window.location.href = 'bridge://open_find:' + pid; // send to bridge
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
        function sanitize(content) {
            var parser = new DOMParser();
            var doc = parser.parseFromString(content, "text/html");
            var codeElements = doc.querySelectorAll('code, pre');
            codeElements.forEach(function(element) {
                var html = element.outerHTML;
                var newHtml = html.replace(/&amp;lt;/g, '&lt;').replace(/&amp;gt;/g, '&gt;');
                element.outerHTML = newHtml;
            });
            return doc.documentElement.outerHTML;
        }
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
        
        // ----------------------------------
        function insertOutput(content, type) {
            const element = document.getElementById('_append_output_');
            if (element) {
                // first remove all nodes inside
                const pre = document.createElement('pre');
                pre.classList.add('type-' + type);
                const code = document.createElement('code');
                code.classList.add('language-python');
                code.innerHTML = sanitize(content);
                pre.appendChild(code);
                element.appendChild(pre);
            }
            highlightCode();
            scrollToBottom();
        }
        function replaceOutput(content) {
            const element = document.getElementById('_append_output_');
            if (element) {
                // first remove all nodes inside
                element.innerHTML = '';
                const pre = document.createElement('pre');
                const code = document.createElement('code');
                code.classList.add('language-python');
                code.innerHTML = sanitize(content);
                pre.appendChild(code);
                element.appendChild(pre);
            }
            highlightCode();
            scrollToBottom();
        }
        function beginOutput(type) {
            const element = document.getElementById('_append_output_');
            if (element) {
                const pre = document.createElement('pre');
                pre.classList.add('type-' + type);
                const code = document.createElement('code');
                code.classList.add('language-python');
                pre.appendChild(code);
                element.appendChild(pre);
            }
        }
        function endOutput(type) {
            const element = document.getElementById('_append_output_');
            if (element) {
               // get last <pre> element, if empty then remove it
                const nodes = element.querySelectorAll('pre code');
                if (nodes.length > 0) {
                    const last = nodes[nodes.length - 1];
                    if (last.innerHTML.trim() === '') {
                        last.parentElement.remove(); // remove empty <pre>
                    }
                }
            }
            highlightCode()
        }
        function appendToOutput(content) {
            const element = document.getElementById('_append_output_');
            if (element) {
                const nodes = element.querySelectorAll('pre code');
                if (nodes.length === 0) {
                    appendBegin();
                    const pre = document.querySelector('pre');
                    const code = pre.querySelector('code');
                    code.innerHTML = content;
                } else {
                    const last = nodes[nodes.length - 1];
                    last.innerHTML += content;
                }
            }
            scrollToBottom();
        }
        function appendImage(path, url) {
            const element = document.getElementById('_append_output_');
            if (element) {
                const a = document.createElement('a');
                a.href = url || path;  // use provided URL or local path
                const img = document.createElement('img');
                img.src = path;
                img.classList.add('output-image');
                img.alt = 'Output Image';
                img.title = 'Output Image';
                a.appendChild(img);
                element.appendChild(a);
            }
        }
        
        function clearOutput() {
            const element = document.getElementById('_append_output_');
            if (element) {
                element.textContent = '';
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
        document.addEventListener('DOMContentLoaded', function() {
            const container = document.getElementById('container');
            container.addEventListener('click', function(event) {                
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
        </script>
        </head>
        <body """ + classes_str + """>
        <div id="container">
            <div id="_append_output_" class="append_output"></div>    
        </div>
        </body>
        </html>
        """
