#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.04 00:00:00                  #
# ================================================== #

import os
from json import dumps as _json_dumps
from random import shuffle as _shuffle

from typing import Optional, List, Dict

from pygpt_net.core.text.utils import elide_filename
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .syntax_highlight import SyntaxHighlight

import pygpt_net.js_rc
import pygpt_net.css_rc
import pygpt_net.fonts_rc


class Body:

    NUM_TIPS = 13

    _HTML_P0 = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    """
    _HTML_P1 = """
                </style>
                <link rel="stylesheet" href="qrc:///css/katex.min.css">
                <script type="text/javascript" src="qrc:///qtwebchannel/qwebchannel.js"></script>
                <script type="text/javascript" src="qrc:///js/highlight.min.js"></script>
                <script type="text/javascript" src="qrc:///js/katex.min.js"></script>
                <script>
                if (typeof hljs !== 'undefined') {
                     hljs.configure({
                      ignoreUnescapedHTML: true,
                    });
                }
                const streamQ = [];
                let DEBUG_MODE = false;
                let bridgeConnected = false;
                let streamHandler;
                let nodeHandler;
                let nodeReplaceHandler;
                let prevScroll = 0;
                let bridge;
                let streamRAF = 0;
                let batching = false;
                let needScroll = false;
                let pid = """
    _HTML_P2 = """                
                let collapsed_idx = [];
                let domOutputStream = null;
                let domLastCodeBlock = null;
                let domLastParagraphBlock = null;
                let domStreamMsg = null;
                let tips = """
    _HTML_P3 = """;
                let tips_hidden = false;

                let els = {};
                let highlightScheduled = false;
                let pendingHighlightRoot = null;
                let pendingHighlightMath = false;
                let highlightRAF = 0;
                let scrollScheduled = false;

                let autoFollow = true;
                let lastScrollTop = 0;
                let userInteracted = false;
                const AUTO_FOLLOW_REENABLE_PX = 8;

                const SHOW_DOWN_THRESHOLD_PX = 0;
                let currentFabAction = 'none';

                let tipsTimers = [];

                let scrollFabUpdateScheduled = false;

                const STREAM_MAX_PER_FRAME = 8;
                const STREAM_EMERGENCY_COALESCE_LEN = 1500;

                Object.defineProperty(window,'SE',{get(){return document.scrollingElement || document.documentElement;}});

                let wheelHandler = null;
                let scrollHandler = null;
                let resizeHandler = null;
                let fabClickHandler = null;
                let containerMouseOverHandler = null;
                let containerMouseOutHandler = null;
                let containerClickHandler = null;
                let keydownHandler = null;
                let docClickFocusHandler = null;

                let fabFreezeUntil = 0;
                const FAB_TOGGLE_DEBOUNCE_MS = 100;

                function resetEphemeralDomRefs() {
                    domLastCodeBlock = null;
                    domLastParagraphBlock = null;
                    domStreamMsg = null;
                }
                function dropIfDetached() {
                    if (domLastCodeBlock && !domLastCodeBlock.isConnected) domLastCodeBlock = null;
                    if (domLastParagraphBlock && !domLastParagraphBlock.isConnected) domLastParagraphBlock = null;
                    if (domStreamMsg && !domStreamMsg.isConnected) domStreamMsg = null;
                }
                function stopTipsTimers() {
                    tipsTimers.forEach(clearTimeout);
                    tipsTimers = [];
                }

                function cleanup() {
                    try { if (highlightRAF) { cancelAnimationFrame(highlightRAF); highlightRAF = 0; } } catch (e) {}
                    try { if (streamRAF) { cancelAnimationFrame(streamRAF); streamRAF = 0; } } catch (e) {}
                    stopTipsTimers();
                    try { bridgeDisconnect(); } catch (e) {}
                    if (wheelHandler) document.removeEventListener('wheel', wheelHandler, { passive: true });
                    if (scrollHandler) window.removeEventListener('scroll', scrollHandler, { passive: true });
                    if (resizeHandler) window.removeEventListener('resize', resizeHandler, { passive: true });
                    if (fabClickHandler && els.scrollFab) els.scrollFab.removeEventListener('click', fabClickHandler, { passive: false });
                    if (containerMouseOverHandler && els.container) els.container.removeEventListener('mouseover', containerMouseOverHandler, { passive: true });
                    if (containerMouseOutHandler && els.container) els.container.removeEventListener('mouseout', containerMouseOutHandler, { passive: true });
                    if (containerClickHandler && els.container) els.container.removeEventListener('click', containerClickHandler, { passive: false });
                    if (keydownHandler) document.removeEventListener('keydown', keydownHandler, { passive: false });
                    if (docClickFocusHandler) document.removeEventListener('click', docClickFocusHandler, { passive: true });
                    streamQ.length = 0;
                    collapsed_idx.length = 0;
                    resetEphemeralDomRefs();
                    els = {};
                    try { history.scrollRestoration = "auto"; } catch (e) {}
                }

                history.scrollRestoration = "manual";
                keydownHandler = function(event) {
                    if (event.ctrlKey && event.key === 'f') {
                        window.location.href = 'bridge://open_find:' + pid;
                        event.preventDefault();
                    }
                    if (event.key === 'Escape') {
                        window.location.href = 'bridge://escape';
                        event.preventDefault();
                    }
                };
                document.addEventListener('keydown', keydownHandler, { passive: false });

                docClickFocusHandler = function(event) {
                    if (event.target.closest('#scrollFab')) return;
                    if (event.target.tagName !== 'A' && !event.target.closest('a')) {
                        window.location.href = 'bridge://focus';
                    }
                };
                document.addEventListener('click', docClickFocusHandler, { passive: true });

                function log(text) {
                    if (bridge) {
                        bridge.log(text);
                    }
                }
                function initDomRefs() {
                    els.container = document.getElementById('container');
                    els.nodes = document.getElementById('_nodes_');
                    els.appendInput = document.getElementById('_append_input_');
                    els.appendOutputBefore = document.getElementById('_append_output_before_');
                    els.appendOutput = document.getElementById('_append_output_');
                    els.appendLive = document.getElementById('_append_live_');
                    els.footer = document.getElementById('_footer_');
                    els.loader = document.getElementById('_loader_');
                    els.tips = document.getElementById('tips');
                    els.scrollFab = document.getElementById('scrollFab');
                    els.scrollFabIcon = document.getElementById('scrollFabIcon');
                }

                function bridgeConnect() {
                    if (!bridge) return false;
                    if (bridgeConnected) return true;
                    if (!streamHandler) {
                        streamHandler = (name, html, chunk, replace, isCode) => {
                            appendStream(name, html, chunk, replace, isCode);
                        };
                        nodeHandler = (html) => {
                            appendNode(html);
                        };
                        nodeReplaceHandler = (html) => {
                            replaceNodes(html);
                        };
                    }
                    try {
                        if (bridge.chunk && typeof bridge.chunk.connect === 'function') bridge.chunk.connect(streamHandler);
                        if (bridge.node && typeof bridge.node.connect === 'function') bridge.node.connect(nodeHandler);
                        if (bridge.nodeReplace && typeof bridge.nodeReplace.connect === 'function') bridge.nodeReplace.connect(nodeReplaceHandler);
                        bridgeConnected = true;
                        return true;
                    } catch (e) {
                        log(e);
                        return false;
                    }
                }
                function bridgeDisconnect() {
                    if (!bridge) return false;
                    if (!bridgeConnected) return true;
                    try {
                        if (bridge.chunk && typeof bridge.chunk.disconnect === 'function') bridge.chunk.disconnect(streamHandler);
                        if (bridge.node && typeof bridge.node.disconnect === 'function') bridge.node.disconnect(nodeHandler);
                        if (bridge.nodeReplace && typeof bridge.nodeReplace.disconnect === 'function') bridge.nodeReplace.disconnect(nodeReplaceHandler);
                    } catch (e) { }
                    bridgeConnected = false;
                    try { if (streamRAF) { cancelAnimationFrame(streamRAF); streamRAF = 0; } } catch (e) { }
                    streamQ.length = 0;
                    return true;
                }
                function bridgeReconnect() {
                    bridgeDisconnect();
                    return bridgeConnect();
                }

                function scheduleHighlight(root, withMath = true) {
                    const scope = root && root.nodeType === 1 ? root : document;
                    if (!pendingHighlightRoot || pendingHighlightRoot === document) {
                        pendingHighlightRoot = scope;
                    } else if (!pendingHighlightRoot.contains(scope)) {
                        pendingHighlightRoot = document;
                    }
                    if (withMath) pendingHighlightMath = true;
                    if (highlightScheduled) return;
                    highlightScheduled = true;
                    if (highlightRAF) {
                        cancelAnimationFrame(highlightRAF);
                        highlightRAF = 0;
                    }
                    highlightRAF = requestAnimationFrame(function() {
                        try {
                            highlightCodeInternal(pendingHighlightRoot || document, pendingHighlightMath);
                        } finally {
                            highlightScheduled = false;
                            pendingHighlightRoot = null;
                            pendingHighlightMath = false;
                            highlightRAF = 0;
                        }
                    });
                }
                function highlightCodeInternal(root, withMath) {
                    (root || document).querySelectorAll('pre code:not(.hljs)').forEach(el => {
                        hljs.highlightElement(el);
                    });
                    if (withMath) {
                        renderMath(root);
                    }
                }
                function highlightCode(withMath = true, root = null) {
                    highlightCodeInternal(root || document, withMath);
                }
                function hideTips() {
                    if (tips_hidden) return;
                    stopTipsTimers();
                    const t = els.tips || document.getElementById('tips');
                    if (t) t.style.display = 'none';
                    tips_hidden = true;
                }
                function showTips() {
                    if (tips_hidden) return;
                    if (tips.length === 0) return;
                    const t = els.tips || document.getElementById('tips');
                    if (t) t.style.display = 'block';
                    tips_hidden = false;
                }
                function cycleTips() {
                    if (tips_hidden) return;
                    if (tips.length === 0) return;
                    let currentTip = 0;
                    function showNextTip() {
                        if (tips_hidden) return;
                        const tipContainer = els.tips || document.getElementById('tips');
                        if (!tipContainer) return;
                        tipContainer.innerHTML = tips[currentTip];
                        tipContainer.classList.add('visible');
                        tipsTimers.push(setTimeout(function() {
                            if (tips_hidden) return;
                            tipContainer.classList.remove('visible');
                            tipsTimers.push(setTimeout(function(){
                                currentTip = (currentTip + 1) % tips.length;
                                showNextTip();
                            }, 1000));
                        }, 15000));
                    }
                    stopTipsTimers();
                    showNextTip();
                }
                function renderMath(root) {
                    const scope = root || document;
                    const scripts = scope.querySelectorAll('script[type^="math/tex"]');
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
                        const parent = script.parentNode;
                        if (parent) parent.replaceChild(element, script);
                      });
                }

                function isNearBottom(marginPx = 100) {
                    const el = SE;
                    const distanceToBottom = el.scrollHeight - el.clientHeight - el.scrollTop;
                    return distanceToBottom <= marginPx;
                }
                function scheduleScroll(live = false) {
                    if (live === true && autoFollow !== true) return;
                    if (scrollScheduled) return;
                    scrollScheduled = true;
                    requestAnimationFrame(function() {
                        scrollScheduled = false;
                        scrollToBottom(live);
                        scheduleScrollFabUpdate();
                    });
                }
                function forceScrollToBottomImmediate() {
                    const el = SE;
                    el.scrollTop = el.scrollHeight;
                    prevScroll = el.scrollHeight;
                }
                function scrollToBottom(live = false, force = false) {
                    const el = SE;
                    const marginPx = 450;
                    const behavior = (live === true) ? 'instant' : 'smooth';
                    if (live === true && autoFollow !== true) {
                        prevScroll = el.scrollHeight;
                        return;
                    }
                    if ((live === true && userInteracted === false) || isNearBottom(marginPx) || live == false || force) {
                        el.scrollTo({ top: el.scrollHeight, behavior });
                    }
                    prevScroll = el.scrollHeight;
                }

                function appendToInput(content) {
                    userInteracted = false;
                    const element = els.appendInput || document.getElementById('_append_input_');
                    if (element) {
                        element.insertAdjacentHTML('beforeend', content);
                        scheduleScroll();
                    }
                }
                function getStreamContainer() {
                    if (domOutputStream && domOutputStream.isConnected) {
                        return domOutputStream;
                    }
                    let element = els.appendOutput || document.getElementById('_append_output_');
                    if (element) {
                        domOutputStream = element;
                    }
                    return element;
                }
                function getStreamMsg(create = true, name_header = '') {
                    const container = getStreamContainer();
                    if (!container) return null;
                    if (domStreamMsg && domStreamMsg.isConnected) return domStreamMsg;
                    let box = container.querySelector('.msg-box');
                    let msg = null;
                    if (!box && create) {
                        box = document.createElement('div');
                        box.classList.add('msg-box');
                        box.classList.add('msg-bot');
                        if (name_header != '') {
                            const name = document.createElement('div');
                            name.classList.add('name-header');
                            name.classList.add('name-bot');
                            name.innerHTML = name_header;
                            box.appendChild(name);
                        }
                        msg = document.createElement('div');
                        msg.classList.add('msg');
                        box.appendChild(msg);
                        container.appendChild(box);
                    } else if (box) {
                        msg = box.querySelector('.msg');
                    }
                    if (msg) domStreamMsg = msg;
                    return msg;
                }
                function appendNode(content) {
                    userInteracted = false;
                    clearStreamBefore();
                    prevScroll = 0;
                    const element = els.nodes || document.getElementById('_nodes_');
                    if (element) {
                        element.classList.remove('empty_list');
                        element.insertAdjacentHTML('beforeend', content);
                        scheduleHighlight(element, true);
                        scrollToBottom(false);
                        scheduleScrollFabUpdate();    
                    }               
                    clearHighlightCache();
                }
                function replaceNodes(content) {
                    userInteracted = false;
                    clearStreamBefore();
                    prevScroll = 0;
                    const element = els.nodes || document.getElementById('_nodes_');
                    if (element) {
                        element.classList.remove('empty_list');
                        element.replaceChildren();
                        element.insertAdjacentHTML('beforeend', content);
                        scheduleHighlight(element, true);
                        scrollToBottom(false, true);
                        scheduleScrollFabUpdate();
                    }
                    clearHighlightCache();
                }
                function clean() {
                    userInteracted = false;
                    const el = els.nodes || document.getElementById('_nodes_');
                    if (el) {
                        el.replaceChildren();
                    }
                    resetEphemeralDomRefs();
                    els = {};
                }
                function clearHighlightCache() {                
                    //
                }
                function appendExtra(id, content) {
                    hideTips();
                    prevScroll = 0;
                    const element = document.getElementById('msg-bot-' + id);
                    if (element) {
                        const extra = element.querySelector('.msg-extra');
                        if (extra) {
                            extra.insertAdjacentHTML('beforeend', content);
                            scheduleHighlight(extra, true);
                            scheduleScroll();
                        }
                    }
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
                    resetEphemeralDomRefs();
                    highlightCode();
                    scheduleScroll();
                }
                function removeNodesFromId(id) {
                    prevScroll = 0;
                    const container = els.nodes || document.getElementById('_nodes_');
                    if (container) {
                        const elements = container.querySelectorAll('.msg-box');
                        let remove = false;
                        elements.forEach(function(element) {
                            if (element.id && element.id.endsWith('-' + id)) {
                                remove = true;
                            }
                            if (remove) {
                                element.remove();
                            }
                        });
                        resetEphemeralDomRefs();
                        scheduleHighlight(container, true);
                        scheduleScroll();
                    }
                }
                function clearStream() {
                    hideTips();
                    domLastParagraphBlock = null;
                    domLastCodeBlock = null;
                    domStreamMsg = null;
                    domOutputStream = null;
                    el = getStreamContainer();
                    if (!el) return;
                    el.replaceChildren();
                }
                function beginStream() {
                    hideTips();
                    userInteracted = false;
                    clearOutput();
                    forceScrollToBottomImmediate();
                    scheduleScroll();
                }
                function endStream() {
                    clearOutput();
                    bridgeReconnect();
                }

                function enqueueStream(name_header, content, chunk, replace = false, is_code_block = false) {
                  streamQ.push({name_header, content, chunk, replace, is_code_block});
                  if (!streamRAF) {
                    streamRAF = requestAnimationFrame(drainStream);
                  }
                }                
                function drainStream() {
                  streamRAF = 0;
                  let processed = 0;
                  const shouldAggressiveCoalesce = streamQ.length >= STREAM_EMERGENCY_COALESCE_LEN;
                
                  batching = true;        // start partii
                  while (streamQ.length && processed < STREAM_MAX_PER_FRAME) {
                    let {name_header, content, chunk, replace, is_code_block} = streamQ.shift();
                    if (!replace && !content && (chunk && chunk.length > 0)) {
                      const chunks = [chunk];
                      while (streamQ.length) {
                        const next = streamQ[0];
                        if (!next.replace && !next.content && next.is_code_block === is_code_block && next.name_header === name_header) {
                          chunks.push(next.chunk);
                          streamQ.shift();
                          if (!shouldAggressiveCoalesce) break;
                        } else break;
                      }
                      chunk = chunks.join('');
                    }
                    applyStream(name_header, content, chunk, replace, is_code_block);
                    processed++;
                  }
                  batching = false;       // koniec partii
                
                  // jedno przewinięcie na partię
                  if (needScroll) {
                    if (userInteracted === false) forceScrollToBottomImmediate();
                    else scheduleScroll(true);
                    needScroll = false;
                  }
                
                  if (streamQ.length) {
                    streamRAF = requestAnimationFrame(drainStream);
                  }
                }
                function appendStream(name_header, content, chunk, replace = false, is_code_block = false) {
                    enqueueStream(name_header, content, chunk, replace, is_code_block);
                }
                function applyStream(name_header, content, chunk, replace = false, is_code_block = false) {
                    dropIfDetached();
                    hideTips();
                    const msg = getStreamMsg(true, name_header);
                    if (msg) {
                        if (replace) {                            
                            domLastCodeBlock = null;
                            domLastParagraphBlock = null;
                            msg.replaceChildren();
                            if (content) {
                              msg.insertAdjacentHTML('afterbegin', content);
                            }
                            let doMath = true;
                            if (is_code_block) {
                                doMath = false;
                            }
                            highlightCode(doMath, msg);
                        } else {
                            if (is_code_block) {
                                let lastCodeBlock = domLastCodeBlock;
                                if (!lastCodeBlock || !msg.contains(lastCodeBlock)) {
                                    const last = msg.lastElementChild;
                                    if (last && last.tagName === 'PRE') {
                                        const codeEl = last.querySelector('code');
                                        if (codeEl) {
                                            lastCodeBlock = codeEl;
                                        }
                                    } else {
                                        const codes = msg.querySelectorAll('pre code');
                                        if (codes.length > 0) {
                                            lastCodeBlock = codes[codes.length - 1];
                                        }
                                    }
                                }
                                if (lastCodeBlock) {
                                    lastCodeBlock.insertAdjacentHTML('beforeend', chunk);
                                    domLastCodeBlock = lastCodeBlock;
                                } else {
                                    msg.insertAdjacentHTML('beforeend', chunk);
                                    domLastCodeBlock = null;
                                }
                            } else {
                                domLastCodeBlock = null;
                                let p = (domLastParagraphBlock && msg.contains(domLastParagraphBlock))
                                    ? domLastParagraphBlock
                                    : (msg.lastElementChild && msg.lastElementChild.tagName === 'P'
                                        ? msg.lastElementChild
                                        : null);
                                if (p) {
                                    p.insertAdjacentHTML('beforeend', chunk);
                                    domLastParagraphBlock = p;
                                } else {
                                    msg.insertAdjacentHTML('beforeend', chunk);
                                    const last = msg.lastElementChild;
                                    domLastParagraphBlock = (last && last.tagName === 'P') ? last : null;
                                }
                            }
                        }
                    }
                    if (batching) {
                        needScroll = true;
                      } else {
                        if (userInteracted === false) {
                          forceScrollToBottomImmediate();
                        } else {
                          scheduleScroll(true);
                        }
                      }
                      fabFreezeUntil = performance.now() + FAB_TOGGLE_DEBOUNCE_MS;
                      scheduleScrollFabUpdate();
                }
                function nextStream() {
                    hideTips();
                    const element = els.appendOutput || document.getElementById('_append_output_');
                    const elementBefore = els.appendOutputBefore || document.getElementById('_append_output_before_');
                    if (element && elementBefore) {
                        const frag = document.createDocumentFragment();
                        while (element.firstChild) {
                            frag.appendChild(element.firstChild);
                        }
                        elementBefore.appendChild(frag);
                        domLastCodeBlock = null;
                        domLastParagraphBlock = null;
                        domStreamMsg = null;
                        scheduleScroll();
                    }
                }
                function clearStreamBefore() {
                    hideTips();
                    const element = els.appendOutputBefore || document.getElementById('_append_output_before_');
                    if (element) {
                        element.replaceChildren();
                    }
                }
                function appendToolOutput(content) {
                    hideToolOutputLoader();
                    enableToolOutput();
                    const elements = document.querySelectorAll('.tool-output');
                    if (elements.length > 0) {
                        const last = elements[elements.length - 1];
                        const contentEl = last.querySelector('.content');
                        if (contentEl) {
                            contentEl.insertAdjacentHTML('beforeend', content);
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
                            contentEl.innerHTML = content;
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
                            contentEl.replaceChildren();
                        }
                    }
                }
                function showToolOutputLoader() {
                    return;
                }
                function hideToolOutputLoader() {
                    const elements = document.querySelectorAll('.msg-bot');
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
                            if (contentEl) {
                                if (contentEl.style.display === 'none') {
                                    contentEl.style.display = 'block';
                                } else {
                                    contentEl.style.display = 'none';
                                }
                            }
                            const toggleEl = outputEl.querySelector('.toggle-cmd-output img');
                            if (toggleEl) {
                                toggleEl.classList.toggle('toggle-expanded');
                            }
                        }
                    }
                }
                function replaceLive(content) {
                    const element = els.appendLive || document.getElementById('_append_live_');
                    if (element) {
                        if (element.classList.contains('hidden')) {
                            element.classList.remove('hidden');
                            element.classList.add('visible');
                        }
                        element.innerHTML = content;
                        scheduleHighlight(element, true);
                        scheduleScroll();
                    }
                }
                function updateFooter(content) {
                    const element = els.footer || document.getElementById('_footer_');
                    if (element) {
                        element.innerHTML = content;
                    }
                }
                function clearNodes() {
                    prevScroll = 0;
                    clearStreamBefore();
                    const element = els.nodes || document.getElementById('_nodes_');
                    if (element) {
                        element.replaceChildren();
                        element.classList.add('empty_list');
                    }
                    resetEphemeralDomRefs();
                }
                function clearInput() {
                    const element = els.appendInput || document.getElementById('_append_input_');
                    if (element) {
                        element.replaceChildren();
                    }
                }
                function clearOutput() {
                    clearStreamBefore();
                    domLastCodeBlock = null;
                    domLastParagraphBlock = null;
                    domStreamMsg = null;
                    domOutputStream = null;
                    const element = els.appendOutput || document.getElementById('_append_output_');
                    if (element) {
                        element.replaceChildren();
                    }
                    clearHighlightCache();
                }
                function clearLive() {
                    const element = els.appendLive || document.getElementById('_append_live_');
                    if (element) {
                        if (element.classList.contains('visible')) {
                            element.classList.remove('visible');
                            element.classList.add('hidden');
                            setTimeout(function() {
                                element.replaceChildren();
                                resetEphemeralDomRefs();
                            }, 1000);
                        } else {
                            element.replaceChildren();
                            resetEphemeralDomRefs();
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
                    let style = document.getElementById('app-style');
                    if (!style) {
                        style = document.createElement('style');
                        style.id = 'app-style';
                        document.head.appendChild(style);
                    }
                    style.textContent = styles;
                }
                function restoreCollapsedCode(root) {
                    const scope = root || document;
                    const codeWrappers = scope.querySelectorAll('.code-wrapper');
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
                    const el = els.loader || document.getElementById('_loader_');
                    if (el) {
                        if (el.classList.contains('hidden')) {
                            el.classList.remove('hidden');
                        }
                        el.classList.add('visible');
                    }
                }
                function hideLoading() {
                    const el = els.loader || document.getElementById('_loader_');
                    if (el) {
                        if (el.classList.contains('visible')) {
                            el.classList.remove('visible');
                        }
                        el.classList.add('hidden');
                    }
                }

                function hasVerticalScroll() {
                    const el = SE;
                    return (el.scrollHeight - el.clientHeight) > 1;
                }
                function distanceToBottomPx() {
                    const el = SE;
                    return el.scrollHeight - el.clientHeight - el.scrollTop;
                }
                function isAtBottom(thresholdPx = 2) {
                    return distanceToBottomPx() <= thresholdPx;
                }

                function computeFabAction() {
                    const el = SE;
                    const hasScroll = (el.scrollHeight - el.clientHeight) > 1;
                    if (!hasScroll) return 'none';
                    const dist = el.scrollHeight - el.clientHeight - el.scrollTop;
                    if (dist <= 2) return 'up';
                    if (dist >= SHOW_DOWN_THRESHOLD_PX) return 'down';
                    return 'none';
                }
                function updateScrollFab(force = false, actionOverride = null, bypassFreeze = false) {
                    const btn = els.scrollFab || document.getElementById('scrollFab');
                    const icon = els.scrollFabIcon || document.getElementById('scrollFabIcon');
                    if (!btn || !icon) return;

                    const action = actionOverride || computeFabAction();
                    if (!force && !bypassFreeze && performance.now() < fabFreezeUntil && action !== currentFabAction) {
                        return;
                    }
                    if (action === 'none') {
                        if (currentFabAction !== 'none' || force) {
                            btn.classList.remove('visible');
                            currentFabAction = 'none';
                        }
                        return;
                    }
                    if (action !== currentFabAction || force) {
                        if (action === 'up') {
                            if (icon.dataset.dir !== 'up') {
                                icon.src = ICON_COLLAPSE;
                                icon.dataset.dir = 'up';
                            }
                            btn.title = "Go to top";
                        } else {
                            if (icon.dataset.dir !== 'down') {
                                icon.src = ICON_EXPAND;
                                icon.dataset.dir = 'down';
                            }
                            btn.title = "Go to bottom";
                        }
                        btn.setAttribute('aria-label', btn.title);
                        currentFabAction = action;
                        btn.classList.add('visible');
                    } else if (!btn.classList.contains('visible')) {
                        btn.classList.add('visible');
                    }
                }
                function scheduleScrollFabUpdate() {
                    if (scrollFabUpdateScheduled) return;
                    scrollFabUpdateScheduled = true;
                    requestAnimationFrame(function() {
                        scrollFabUpdateScheduled = false;
                        const action = computeFabAction();
                        if (action !== currentFabAction) {
                            updateScrollFab(false, action);
                        }
                    });
                }

                function maybeEnableAutoFollowByProximity() {
                    const el = SE;
                    if (!autoFollow) {
                        const distanceToBottom = el.scrollHeight - el.clientHeight - el.scrollTop;
                        if (distanceToBottom <= AUTO_FOLLOW_REENABLE_PX) {
                            autoFollow = true;
                        }
                    }
                }
                function scrollToTopUser() {
                    userInteracted = true;
                    autoFollow = false;
                    try {
                        const el = SE;
                        el.scrollTo({ top: 0, behavior: 'smooth' });
                        lastScrollTop = el.scrollTop;
                    } catch (e) {
                        const el = SE;
                        el.scrollTop = 0;
                        lastScrollTop = 0;
                    }
                }
                function scrollToBottomUser() {
                    userInteracted = true;
                    autoFollow = false;
                    try {
                        const el = SE;
                        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
                        lastScrollTop = el.scrollTop;
                    } catch (e) {
                        const el = SE;
                        el.scrollTop = el.scrollHeight;
                        lastScrollTop = el.scrollTop;
                    }
                    maybeEnableAutoFollowByProximity();
                }

                document.addEventListener('DOMContentLoaded', function() {
                    new QWebChannel(qt.webChannelTransport, function (channel) {
                        bridge = channel.objects.bridge;
                        bridgeConnect();                        
                        if (bridge.js_ready) bridge.js_ready();
                    });
                    initDomRefs();
                    const container = els.container;

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
                    containerMouseOverHandler = function(event) {
                        if (event.target.classList.contains('action-img')) {
                            const id = event.target.getAttribute('data-id');
                            addClassToMsg(id, 'msg-highlight');
                        }
                    };
                    containerMouseOutHandler = function(event) {
                        if (event.target.classList.contains('action-img')) {
                            const id = event.target.getAttribute('data-id');
                            removeClassFromMsg(id, 'msg-highlight');
                        }
                    };
                    container.addEventListener('mouseover', containerMouseOverHandler, { passive: true });
                    container.addEventListener('mouseout', containerMouseOutHandler, { passive: true });

                    wheelHandler = function(ev) {
                        userInteracted = true;
                        if (ev.deltaY < 0) {
                            autoFollow = false;
                        } else {
                            maybeEnableAutoFollowByProximity();
                        }
                    };
                    document.addEventListener('wheel', wheelHandler, { passive: true });

                    scrollHandler = function() {
                        const el = SE;
                        const top = el.scrollTop;
                        if (top + 1 < lastScrollTop) {
                            autoFollow = false;
                        }
                        maybeEnableAutoFollowByProximity();
                        lastScrollTop = top;
                        const action = computeFabAction();
                        if (action !== currentFabAction) {
                            updateScrollFab(false, action, true);
                        }
                    };
                    window.addEventListener('scroll', scrollHandler, { passive: true });

                    if (els.scrollFab) {
                        fabClickHandler = function(ev) {
                            ev.preventDefault();
                            ev.stopPropagation();
                            const action = computeFabAction();
                            if (action === 'up') {
                                scrollToTopUser();
                            } else if (action === 'down') {
                                scrollToBottomUser();
                            }
                            fabFreezeUntil = performance.now() + FAB_TOGGLE_DEBOUNCE_MS;
                            updateScrollFab(true);
                        };
                        els.scrollFab.addEventListener('click', fabClickHandler, { passive: false });
                    }

                    resizeHandler = function() {
                        maybeEnableAutoFollowByProximity();
                        scheduleScrollFabUpdate();
                    };
                    window.addEventListener('resize', resizeHandler, { passive: true });

                    updateScrollFab(true);

                    containerClickHandler = function(event) {
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
                    };
                    container.addEventListener('click', containerClickHandler, { passive: false });

                    // window.addEventListener('pagehide', cleanup, { once: true });
                    // window.addEventListener('beforeunload', cleanup, { once: true });
                });
                setTimeout(cycleTips, 10000);
                </script>
            </head>
            <body """
    _HTML_P4 = """>
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
            <button id="scrollFab" class="scroll-fab" type="button" title="Go to top" aria-label="Go to top">
                <img id="scrollFabIcon" src="" alt="Scroll">
            </button>
            </body>
            </html>
            """

    _SPINNER = """
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

    _SCROLL_FAB_CSS = """
        #scrollFab.scroll-fab {
            position: fixed;
            //left: 50%;
            right: 16px;
            bottom: 16px;
            width: 40px;
            height: 40px;
            border: none;
            background: transparent;
            padding: 0;
            margin: 0;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2147483647;
            cursor: pointer;
            opacity: .65;
            transition: opacity .2s ease, transform .2s ease;
            //transform: translate(-50%, 0);
            will-change: transform, opacity;
            pointer-events: auto;
            -webkit-tap-highlight-color: transparent;
        }
        #scrollFab.scroll-fab.visible {
            display: inline-flex;
        }
        #scrollFab.scroll-fab:hover {
            opacity: 1;
            //transform: translate(-50%, -1px);
        }
        #scrollFab.scroll-fab img {
            width: 100%;
            height: 100%;
            display: block;
            pointer-events: none;
        }
        @media (prefers-reduced-motion: reduce) {
            #scrollFab.scroll-fab {
                transition: none;
            }
        }
    """

    _PERFORMANCE_CSS = """
        #container, #_nodes_, #_append_output_, #_append_output_before_ {
            contain: layout paint;
            overscroll-behavior: contain;
            backface-visibility: hidden;
            transform: translateZ(0);
        }
        .msg-box {
            contain: layout paint style;
            contain-intrinsic-size: 1px 600px;            
            box-shadow: none !important;
            filter: none !important;
        }
        .msg-box:not(:last-child) {       
            content-visibility: auto;
        }
        .msg {
            text-rendering: optimizeSpeed;
        }
        """

    def __init__(self, window=None):
        self.window = window
        self.highlight = SyntaxHighlight(window)
        self._tip_keys = tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))
        self._syntax_dark = (
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
        )

    def is_timestamp_enabled(self) -> bool:
        return self.window.core.config.get('output_timestamp')

    def prepare_styles(self) -> str:
        cfg = self.window.core.config
        fonts_path = os.path.join(cfg.get_app_path(), "data", "fonts").replace("\\", "/")
        syntax_style = self.window.core.config.get("render.code_syntax") or "default"
        theme_css = self.window.controller.theme.markdown.get_web_css().replace('%fonts%', fonts_path)
        parts = [
            self._SPINNER,
            self._SCROLL_FAB_CSS,
            theme_css,
            "pre { color: #fff; }" if syntax_style in self._syntax_dark else "pre { color: #000; }",
            self.highlight.get_style_defs(),
            self._PERFORMANCE_CSS
        ]
        return "\n".join(parts)

    def prepare_action_icons(self, ctx: CtxItem) -> str:
        icons_html = "".join(self.get_action_icons(ctx, all=True))
        if icons_html:
            return f'<div class="action-icons" data-id="{ctx.id}">{icons_html}</div>'
        return ""

    def get_action_icons(self, ctx: CtxItem, all: bool = False) -> List[str]:
        icons: List[str] = []
        if ctx.output:
            cid = ctx.id
            t = trans
            icons.append(
                f'<a href="extra-audio-read:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("volume", t("ctx.extra.audio"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-copy:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("copy", t("ctx.extra.copy"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-replay:{cid}" class="action-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("reload", t("ctx.extra.reply"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-edit:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("edit", t("ctx.extra.edit"), ctx)}</span></a>')
            icons.append(
                f'<a href="extra-delete:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("delete", t("ctx.extra.delete"), ctx)}</span></a>')
            if not self.window.core.ctx.is_first_item(cid):
                icons.append(
                    f'<a href="extra-join:{cid}" class="action-icon edit-icon" data-id="{cid}" role="button"><span class="cmd">{self.get_icon("playlist_add", t("ctx.extra.join"), ctx)}</span></a>')
        return icons

    def get_icon(self, icon: str, title: Optional[str] = None, item: Optional[CtxItem] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", f"{icon}.svg")
        return f'<img src="file://{icon_path}" class="action-img" title="{title}" alt="{title}" data-id="{item.id}">'

    def get_image_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
        url, path = self.window.core.filesystem.extract_local_url(url)
        basename = os.path.basename(path)
        ext = os.path.splitext(basename)[1].lower()
        video_exts = (".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv")
        if ext in video_exts:
            if ext != ".webm":
                webm_path = os.path.splitext(path)[0] + ".webm"
                if os.path.exists(webm_path):
                    path = webm_path
                    ext = ".webm"
            return f'''
            <div class="extra-src-video-box" title="{url}">
                <video class="video-player" controls>
                    <source src="{path}" type="video/{ext[1:]}">
                </video>
                <p><a href="bridge://play_video/{url}" class="title">{elide_filename(basename)}</a></p>
            </div>
            '''
        return f'<div class="extra-src-img-box" title="{url}"><div class="img-outer"><div class="img-wrapper"><a href="{url}"><img src="{path}" class="image"></a></div><a href="{url}" class="title">{elide_filename(basename)}</a></div></div><br/>'

    def get_url_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "language.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        return f'{icon}<a href="{url}" title="{url}">{url}</a> <small>{num_str}</small>'

    def get_docs_html(self, docs: List[Dict]) -> str:
        html_parts: List[str] = []
        src_parts: List[str] = []
        num = 1
        limit = 3

        try:
            for item in docs:
                for uuid, doc_json in item.items():
                    entries = ", ".join(f"<b>{k}:</b> {doc_json[k]}" for k in doc_json)
                    src_parts.append(f"<p><small>[{num}] {uuid}: {entries}</small></p>")
                    num += 1
                    if num >= limit:
                        break
                if num >= limit:
                    break
        except Exception:
            pass

        if src_parts:
            app_path = self.window.core.config.get_app_path()
            icon_path = os.path.join(app_path, "data", "icons", "db.svg").replace("\\", "/")
            icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
            html_parts.append(f'<p>{icon}<small><b>{trans("chat.prefix.doc")}:</b></small></p>')
            html_parts.append('<div class="cmd">')
            html_parts.append(f"<p>{''.join(src_parts)}</p>")
            html_parts.append("</div> ")

        return "".join(html_parts)

    def get_file_html(self, url: str, num: Optional[int] = None, num_all: Optional[int] = None) -> str:
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "attachments.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        url, path = self.window.core.filesystem.extract_local_url(url)
        return f'{icon} <b>{num_str}</b> <a href="{url}">{path}</a>'

    def prepare_tool_extra(self, ctx: CtxItem) -> str:
        extra = ctx.extra
        if not extra:
            return ""

        parts: List[str] = ['<div class="msg-extra">']

        if "plugin" in extra:
            event = Event(Event.TOOL_OUTPUT_RENDER, {
                'tool': extra["plugin"],
                'html': '',
                'multiple': False,
                'content': extra,
            })
            event.ctx = ctx
            self.window.dispatch(event, all=True)
            if event.data['html']:
                parts.append(f'<div class="tool-output-block">{event.data["html"]}</div>')

        elif "tool_output" in extra and isinstance(extra["tool_output"], list):
            for tool in extra["tool_output"]:
                if "plugin" not in tool:
                    continue
                event = Event(Event.TOOL_OUTPUT_RENDER, {
                    'tool': tool["plugin"],
                    'html': '',
                    'multiple': True,
                    'content': tool,
                })
                event.ctx = ctx
                self.window.dispatch(event, all=True)
                if event.data['html']:
                    parts.append(f'<div class="tool-output-block">{event.data["html"]}</div>')

        parts.append("</div>")
        return "".join(parts)

    def get_all_tips(self) -> str:
        if not self.window.core.config.get("layout.tooltips", False):
            return "[]"

        _trans = trans
        prefix = _trans("output.tips.prefix")
        keys = self._tip_keys if hasattr(self, "_tip_keys") and len(self._tip_keys) == self.NUM_TIPS \
            else tuple(f"output.tips.{i}" for i in range(1, self.NUM_TIPS + 1))

        tips = [f"<p><b>{prefix}</b>: {_trans(k)}</p>" for k in keys]
        _shuffle(tips)
        return _json_dumps(tips)

    def get_html(self, pid: int) -> str:
        cfg_get = self.window.core.config.get
        style = cfg_get("theme.style", "blocks")
        classes = ["theme-" + style]
        if cfg_get('render.blocks'):
            classes.append("display-blocks")
        if cfg_get('ctx.edit_icons'):
            classes.append("display-edit-icons")
        if self.is_timestamp_enabled():
            classes.append("display-timestamp")
        classes_str = f' class="{" ".join(classes)}"' if classes else ""
        styles_css = self.prepare_styles()
        tips_json = self.get_all_tips()

        app_path = self.window.core.config.get_app_path().replace("\\", "/")
        expand_path = os.path.join(app_path, "data", "icons", "expand.svg").replace("\\", "/")
        collapse_path = os.path.join(app_path, "data", "icons", "collapse.svg").replace("\\", "/")
        icons_js = f';const ICON_EXPAND="file://{expand_path}";const ICON_COLLAPSE="file://{collapse_path}";'

        return ''.join((
            self._HTML_P0,
            styles_css,
            self._HTML_P1,
            str(pid),
            icons_js,
            self._HTML_P2,
            tips_json,
            self._HTML_P3,
            classes_str,
            self._HTML_P4,
        ))