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
                hljs.configure({
                  ignoreUnescapedHTML: true,
                });
                const DEBUG_MODE = false;
                let bridgeConnected = false;
                let streamHandler;
                let nodeHandler;
                let nodeReplaceHandler;
                let scrollTimeout = null;
                let prevScroll = 0;
                let bridge;
                let streamQ = [];
                let streamRAF = 0;
                let pid = """
    _HTML_P2 = """                
                let collapsed_idx = [];
                let domOutputStream = document.getElementById('_append_output_');
                let domOutput = document.getElementById('_output_');
                let domInput = document.getElementById('_input_');
                let domLastCodeBlock = null;
                let domLastParagraphBlock = null;
                let htmlBuffer = "";
                let tips = """
    _HTML_P3 = """;
                let tips_hidden = false;

                let els = {};
                let highlightScheduled = false;
                let pendingHighlightRoot = null;
                let pendingHighlightMath = false;
                let highlightRAF = 0;  // RAF id for highlight batcher
                let scrollScheduled = false;

                // Auto-follow state: when false, live stream auto-scroll is suppressed
                let autoFollow = true;
                let lastScrollTop = 0;
                // Tracks whether user has performed any scroll-related interaction
                let userInteracted = false;
                const AUTO_FOLLOW_REENABLE_PX = 8; // px from bottom to re-enable auto-follow

                // FAB thresholds
                const SHOW_DOWN_THRESHOLD_PX = 0; // show "down" only when farther than this from bottom
                let currentFabAction = 'none'; // tracks current FAB state to avoid redundant work

                // timers
                let tipsTimers = [];

                // observers
                let roDoc = null;
                let roContainer = null;

                // FAB (scroll-to-top/bottom) scheduling
                let scrollFabUpdateScheduled = false;

                // Streaming micro-batching config
                const STREAM_MAX_PER_FRAME = 64; // defensive upper bound of operations per frame
                const STREAM_EMERGENCY_COALESCE_LEN = 1500; // when queue length is high, coalesce aggressively

                // clear previous references
                function resetEphemeralDomRefs() {
                    domLastCodeBlock = null;
                    domLastParagraphBlock = null;
                }
                function dropIfDetached() {
                    if (domLastCodeBlock && !domLastCodeBlock.isConnected) domLastCodeBlock = null;
                    if (domLastParagraphBlock && !domLastParagraphBlock.isConnected) domLastParagraphBlock = null;
                }
                function stopTipsTimers() {
                    tipsTimers.forEach(clearTimeout);
                    tipsTimers = [];
                }

                function teardown() {
                    // Cancel timers/RAF/observers to prevent background CPU usage
                    stopTipsTimers();
                    try {
                        if (streamRAF) {
                            cancelAnimationFrame(streamRAF);
                            streamRAF = 0;
                        }
                        if (highlightRAF) {
                            cancelAnimationFrame(highlightRAF);
                            highlightRAF = 0;
                        }
                    } catch (e) { /* ignore */ }
                    // Clear streaming queue to release memory immediately
                    streamQ.length = 0;
                    scrollFabUpdateScheduled = false;
                    scrollScheduled = false;
                    highlightScheduled = false;
                }

                history.scrollRestoration = "manual";
                document.addEventListener('keydown', function(event) {
                    if (event.ctrlKey && event.key === 'f') {
                        window.location.href = 'bridge://open_find:' + pid;
                        event.preventDefault();
                    }
                    if (event.key === 'Escape') {
                        window.location.href = 'bridge://escape';
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
                    // FAB refs
                    els.scrollFab = document.getElementById('scrollFab');
                    els.scrollFabIcon = document.getElementById('scrollFabIcon');
                }
                function bridgeConnect() {
                    // Idempotent connect
                    if (!bridge || !bridge.chunk || typeof bridge.chunk.connect !== 'function') return false;
                    if (bridgeConnected) return true;
                
                    // Ensure handler exists and is stable (same identity for disconnect/connect)
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
                        bridge.chunk.connect(streamHandler);
                        bridge.node.connect(nodeHandler);
                        bridge.nodeReplace.connect(nodeReplaceHandler);
                        bridgeConnected = true;
                        return true;
                    } catch (e) {
                        log(e);
                        return false;
                    }
                }
                
                function bridgeDisconnect() {
                    // Idempotent disconnect
                    if (!bridge || !bridge.chunk || typeof bridge.chunk.disconnect !== 'function') return false;
                    if (!bridgeConnected) return true;
                
                    try {
                        bridge.chunk.disconnect(streamHandler);
                        bridge.node.disconnect(nodeHandler);
                        bridge.nodeReplace.disconnect(nodeReplaceHandler);
                    } catch (e) { /* ignore */ }
                    bridgeConnected = false;
                
                    // Stop scheduled work and release pending chunks immediately
                    try { if (streamRAF) { cancelAnimationFrame(streamRAF); streamRAF = 0; } } catch (e) { /* ignore */ }
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
                        // Ensure we do not queue multiple highlight frames
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
                        if (DEBUG_MODE) log("math");
                    }
                    if (DEBUG_MODE) log("execute highlight");
                }
                function highlightCode(withMath = true, root = null) {
                     if (DEBUG_MODE) log("queue highlight, withMath: " + withMath);
                    highlightCodeInternal(root || document, withMath); // prevent blink on fast updates
                    // scheduleHighlight(root || document, withMath);  // disabled
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
                    if (DEBUG_MODE) log("execute math");
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
                    const el = document.scrollingElement || document.documentElement;
                    const distanceToBottom = el.scrollHeight - el.clientHeight - el.scrollTop;
                    return distanceToBottom <= marginPx;
                }
                function scheduleScroll(live = false) {
                    // Skip scheduling live auto-scroll when user disabled follow
                    if (live === true && autoFollow !== true) return;
                    if (scrollScheduled) return;
                    scrollScheduled = true;
                    requestAnimationFrame(function() {
                        scrollScheduled = false;
                        scrollToBottom(live);
                        // keep FAB state in sync after any programmatic scroll
                        scheduleScrollFabUpdate();
                    });
                }
                // Force immediate scroll to bottom (pre-interaction bootstrap)
                function forceScrollToBottomImmediate() {
                    const el = document.scrollingElement || document.documentElement;
                    el.scrollTop = el.scrollHeight; // no behavior, no RAF, deterministic
                    prevScroll = el.scrollHeight;
                }
                function scrollToBottom(live = false, force = false) {
                    const el = document.scrollingElement || document.documentElement;
                    const marginPx = 450;
                    const behavior = (live === true) ? 'instant' : 'smooth';

                    // Respect user-follow state during live updates
                    if (live === true && autoFollow !== true) {
                        // Keep prevScroll consistent for potential consumers
                        prevScroll = el.scrollHeight;
                        return;
                    }

                    // Allow initial auto-follow before any user interaction
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
                        highlightCode(true, element);
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
                function appendNode(content) {
                    userInteracted = false;
                    if (DEBUG_MODE) {
                        log("APPEND NODE: {" + content + "}");
                    }
                    clearStreamBefore();
                    prevScroll = 0;
                    const element = els.nodes || document.getElementById('_nodes_');
                    if (element) {
                        element.classList.remove('empty_list');
                        element.insertAdjacentHTML('beforeend', content);
                        highlightCode(true, element);
                        scrollToBottom(false);  // without schedule
                        scheduleScrollFabUpdate();    
                    }               
                    clearHighlightCache();
                }
                function replaceNodes(content) {
                    userInteracted = false;
                    if (DEBUG_MODE) {
                        log("REPLACE NODES: {" + content + "}");
                    }
                    clearStreamBefore();
                    prevScroll = 0;
                    const element = els.nodes || document.getElementById('_nodes_');
                    if (element) {
                        element.classList.remove('empty_list');
                        element.replaceChildren();
                        element.insertAdjacentHTML('beforeend', content);
                        highlightCode(true, element);
                        scrollToBottom(false, true);  // without schedule
                        scheduleScrollFabUpdate();
                    }
                    clearHighlightCache();
                }
                function clean() {
                    if (DEBUG_MODE) {
                        log("-- CLEAN DOM --");
                    }
                    userInteracted = false;
                    const el = els.nodes || document.getElementById('_nodes_');
                    if (el) {
                        el.replaceChildren();
                    }
                    resetEphemeralDomRefs();
                    els = {};
                    /*
                    try {
                        if (window.gc) {
                            window.gc();
                        }
                    } catch (e) {
                        // gc not available
                    }
                    */
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
                            highlightCode(true, extra);
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
                        highlightCode(true, container);
                        scheduleScroll();
                    }
                }
                function clearStream() {
                    hideTips();
                    if (DEBUG_MODE) {
                        log("STREAM CLEAR");
                    }
                    domLastParagraphBlock = null;
                    domLastCodeBlock = null;
                    domOutputStream = null;
                    const element = getStreamContainer();
                    if (element) {
                        let box = element.querySelector('.msg-box');
                        let msg;
                        if (!box) {
                            box = document.createElement('div');
                            box.classList.add('msg-box');
                            box.classList.add('msg-bot');
                            msg = document.createElement('div');
                            msg.classList.add('msg');
                            box.appendChild(msg);
                            element.appendChild(box);
                        } else {
                            msg = box.querySelector('.msg');
                        }
                        if (msg) {
                            msg.replaceChildren();
                        }
                    }
                }
                function beginStream() {
                    hideTips();
                    if (DEBUG_MODE) {
                        log("STREAM BEGIN");
                    }
                    userInteracted = false;
                    clearOutput();
                    // Ensure initial auto-follow baseline before any chunks overflow
                    forceScrollToBottomImmediate();
                    scheduleScroll();
                }
                function endStream() {
                    if (DEBUG_MODE) {
                        log("STREAM END");
                    }
                    clearOutput();
                    bridgeReconnect();
                }
                function enqueueStream(name_header, content, chunk, replace = false, is_code_block = false) {
                  // Push incoming chunk; scheduling is done with RAF to batch DOM ops
                  streamQ.push({name_header, content, chunk, replace, is_code_block});
                  if (!streamRAF) {
                    streamRAF = requestAnimationFrame(drainStream);
                  }
                }                
                function drainStream() {
                  streamRAF = 0;
                  let processed = 0;

                  // Emergency coalescing if queue grows too large
                  const shouldAggressiveCoalesce = streamQ.length >= STREAM_EMERGENCY_COALESCE_LEN;

                  while (streamQ.length && processed < STREAM_MAX_PER_FRAME) {
                    let {name_header, content, chunk, replace, is_code_block} = streamQ.shift();

                    // Coalesce contiguous simple appends to reduce DOM churn
                    if (!replace && !content && (chunk && chunk.length > 0)) {
                      // Collect chunks into an array to avoid O(n^2) string concatenation
                      const chunks = [chunk];
                      while (streamQ.length) {
                        const next = streamQ[0];
                        if (!next.replace && !next.content && next.is_code_block === is_code_block && next.name_header === name_header) {
                          chunks.push(next.chunk);
                          streamQ.shift();
                          if (!shouldAggressiveCoalesce) {
                            // Light coalescing per frame is enough under normal conditions
                            break;
                          }
                        } else {
                          break;
                        }
                      }
                      chunk = chunks.join('');
                    }

                    applyStream(name_header, content, chunk, replace, is_code_block);
                    processed++;
                  }

                  // If there are remaining items re-schedule next frame
                  if (streamQ.length) {
                    streamRAF = requestAnimationFrame(drainStream);
                  }
                }
                // Public API: enqueue and process in the next animation frame
                function appendStream(name_header, content, chunk, replace = false, is_code_block = false) {
                    enqueueStream(name_header, content, chunk, replace, is_code_block);
                }
                // Internal: performs actual DOM updates for a single merged chunk
                function applyStream(name_header, content, chunk, replace = false, is_code_block = false) {
                    dropIfDetached(); // clear references to detached elements
                    hideTips();
                    if (DEBUG_MODE) {
                        log("APPLY CHUNK: {" + chunk + "}, CONTENT: {"+content+"}, replace: " + replace + ", is_code_block: " + is_code_block);
                    }
                    const element = getStreamContainer();
                    let msg;
                    if (element) {
                        let box = element.querySelector('.msg-box');
                        if (!box) {
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
                            element.appendChild(box);
                        } else {
                            msg = box.querySelector('.msg');
                        }
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
                                    // Try to reuse cached last code block; fallback to cheap lastElementChild check
                                    let lastCodeBlock = domLastCodeBlock;
                                    if (!lastCodeBlock || !msg.contains(lastCodeBlock)) {
                                        const last = msg.lastElementChild;
                                        if (last && last.tagName === 'PRE') {
                                            const codeEl = last.querySelector('code');
                                            if (codeEl) {
                                                lastCodeBlock = codeEl;
                                            }
                                        } else {
                                            // Fallback scan only when necessary
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
                    }
                    // Initial auto-follow until first user interaction
                    if (userInteracted === false) {
                        forceScrollToBottomImmediate();
                    } else {
                        scheduleScroll(true);
                    }
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
                        highlightCode(true, element);
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
                    domOutputStream = null; // release handle to allow GC on old container subtree
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
                            const collapseBtn = wrapper.querySelector('code-header-collapse');
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

                // ---------- scroll bottom ----------
                function hasVerticalScroll() {
                    const el = document.scrollingElement || document.documentElement;
                    return (el.scrollHeight - el.clientHeight) > 1;
                }
                function distanceToBottomPx() {
                    const el = document.scrollingElement || document.documentElement;
                    return el.scrollHeight - el.clientHeight - el.scrollTop;
                }
                function isAtBottom(thresholdPx = 2) {
                    return distanceToBottomPx() <= thresholdPx;
                }
                function isLoaderHidden() {
                    const el = els.loader || document.getElementById('_loader_');
                    // If loader element is missing treat as hidden to avoid blocking FAB unnecessarily
                    return !el || el.classList.contains('hidden');
                }
                function updateScrollFab() {
                    const btn = els.scrollFab || document.getElementById('scrollFab');
                    const icon = els.scrollFabIcon || document.getElementById('scrollFabIcon');
                    if (!btn || !icon) return;

                    const hasScroll = hasVerticalScroll();
                    if (!hasScroll) {
                        btn.classList.remove('visible');
                        currentFabAction = 'none';
                        return;
                    }

                    const atBottom = isAtBottom();
                    const dist = distanceToBottomPx();
                    const loaderHidden = isLoaderHidden();

                    // Determine desired action and visibility based on requirements:
                    // - Show "down" only when at least SHOW_DOWN_THRESHOLD_PX away from bottom.
                    // - Show "up" only when loader-global has the 'hidden' class.
                    // - Otherwise hide the FAB to prevent overlap and noise.
                    let action = 'none'; // 'up' | 'down' | 'none'
                    if (atBottom) {
                        if (loaderHidden) {
                            action = 'up';
                        } else {
                            action = 'none';
                        }
                    } else {
                        if (dist >= SHOW_DOWN_THRESHOLD_PX) {
                            action = 'down';
                        } else {
                            action = 'none';
                        }
                    }

                    if (action === 'none') {
                        btn.classList.remove('visible');
                        currentFabAction = 'none';
                        return;
                    }

                    // Update icon and semantics only if changed to avoid redundant 'load' events
                    if (action !== currentFabAction) {
                        if (action === 'up') {
                            if (icon.src !== ICON_COLLAPSE) icon.src = ICON_COLLAPSE;
                            btn.title = "Go to top";
                        } else {
                            if (icon.src !== ICON_EXPAND) icon.src = ICON_EXPAND;
                            btn.title = "Go to bottom";
                        }
                        btn.setAttribute('aria-label', btn.title);
                        currentFabAction = action;
                    }

                    // Finally show
                    btn.classList.add('visible');
                }
                function scheduleScrollFabUpdate() {
                    if (scrollFabUpdateScheduled) return;
                    scrollFabUpdateScheduled = true;
                    requestAnimationFrame(function() {
                        scrollFabUpdateScheduled = false;
                        updateScrollFab();
                    });
                }
                function scrollToTopUser() {
                    // Explicit user-driven scroll disables auto-follow
                    userInteracted = true;
                    autoFollow = false;
                    try {
                        const el = document.scrollingElement || document.documentElement;
                        el.scrollTo({ top: 0, behavior: 'smooth' });
                    } catch (e) {
                        // Fallback in environments without smooth scrolling support
                        const el = document.scrollingElement || document.documentElement;
                        el.scrollTop = 0;
                    }
                    scheduleScrollFabUpdate();
                }
                function scrollToBottomUser() {
                    // User action to go to bottom re-enables auto-follow
                    userInteracted = true;
                    autoFollow = true;
                    try {
                        const el = document.scrollingElement || document.documentElement;
                        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
                    } catch (e) {
                        const el = document.scrollingElement || document.documentElement;
                        el.scrollTop = el.scrollHeight;
                    }
                    scheduleScrollFabUpdate();
                }
                // ---------- end of scroll bottom ----------

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
                    // Wheel up disables auto-follow immediately (works even at absolute bottom)
                    document.addEventListener('wheel', function(ev) {
                        userInteracted = true;
                        if (ev.deltaY < 0) {
                            autoFollow = false;
                        }
                    }, { passive: true });

                    // Track scroll direction and restore auto-follow when user returns to bottom
                    window.addEventListener('scroll', function() {
                        const el = document.scrollingElement || document.documentElement;
                        const top = el.scrollTop;

                        // User scrolled up (ignore tiny jitter)
                        if (top + 1 < lastScrollTop) {
                            autoFollow = false;
                        } else if (!autoFollow) {
                            const distanceToBottom = el.scrollHeight - el.clientHeight - top;
                            if (distanceToBottom <= AUTO_FOLLOW_REENABLE_PX) {
                                autoFollow = true;
                            }
                        }
                        lastScrollTop = top;
                    }, { passive: true });

                    // Scroll-to-top/bottom FAB wiring
                    if (els.scrollFab) {
                        els.scrollFab.addEventListener('click', function(ev) {
                            ev.preventDefault();
                            if (isAtBottom()) {
                                scrollToTopUser();
                            } else {
                                scrollToBottomUser();
                            }
                        }, { passive: false });
                    }
                    window.addEventListener('scroll', scheduleScrollFabUpdate, { passive: true });
                    window.addEventListener('resize', scheduleScrollFabUpdate, { passive: true });

                    // Initial state
                    scheduleScrollFabUpdate();  

                    container.addEventListener('click', function(event) {
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
                    });

                    // Cleanup on page lifecycle changes
                    window.addEventListener('pagehide', teardown, { passive: true });
                    window.addEventListener('beforeunload', teardown, { passive: true });
                });
                setTimeout(cycleTips, 10000);  // after 10 seconds
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

    # CSS for the scroll-to-top/bottom
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

    def __init__(self, window=None):
        """
        HTML Body

        :param window: Window instance
        """
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
        cfg = self.window.core.config
        fonts_path = os.path.join(cfg.get_app_path(), "data", "fonts").replace("\\", "/")
        syntax_style = self.window.core.config.get("render.code_syntax") or "default"
        perf_css = """
        #container, #_nodes_, #_append_output_, #_append_output_before_ {
            contain: layout paint;
            overscroll-behavior: contain;
        }
        .msg-box {
            contain: layout paint style;
            contain-intrinsic-size: 1px 600px;
        }
        .msg-box:not(:last-child) {       
            content-visibility: auto;
        }
        #container,
        #_nodes_,
        #_append_output_,
        #_append_output_before_ {
            backface-visibility: hidden;
            transform: translateZ(0);
        }
        .msg-box {
            box-shadow: none !important;
            filter: none !important;
        }
        .msg {
            text-rendering: optimizeSpeed;
        }
        """

        theme_css = self.window.controller.theme.markdown.get_web_css().replace('%fonts%', fonts_path)
        parts = [
            self._SPINNER,
            theme_css,
            "pre { color: #fff; }" if syntax_style in self._syntax_dark else "pre { color: #000; }",
            self.highlight.get_style_defs(),
            perf_css,
            self._SCROLL_FAB_CSS,  # keep FAB styles last to ensure precedence
        ]
        return "\n".join(parts)

    def prepare_action_icons(self, ctx: CtxItem) -> str:
        """
        Append action icons

        :param ctx: context item
        :return: HTML code
        """
        icons_html = "".join(self.get_action_icons(ctx, all=True))
        if icons_html:
            return f'<div class="action-icons" data-id="{ctx.id}">{icons_html}</div>'
        return ""

    def get_action_icons(self, ctx: CtxItem, all: bool = False) -> List[str]:
        """
        Get action icons for context item

        :param ctx: context item
        :param all: True to show all icons
        :return: list of icons
        """
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
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", f"{icon}.svg")
        return f'<img src="file://{icon_path}" class="action-img" title="{title}" alt="{title}" data-id="{item.id}">'

    def get_image_html(
            self,
            url: str,
            num: Optional[int] = None,
            num_all: Optional[int] = None
    ) -> str:
        """
        Get media image/video/audio HTML

        :param url: URL to image
        :param num: number of image
        :param num_all: number of all images
        :return: HTML code
        """
        url, path = self.window.core.filesystem.extract_local_url(url)
        basename = os.path.basename(path)

        # if video file then embed video player
        ext = os.path.splitext(basename)[1].lower()
        video_exts = (".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv")
        if ext in video_exts:
            # check if .webm file exists for better compatibility
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
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "language.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        return f'{icon}<a href="{url}" title="{url}">{url}</a> <small>{num_str}</small>'

    def get_docs_html(self, docs: List[Dict]) -> str:
        """
        Get Llama-index doc metadata HTML

        :param docs: list of document metadata
        :return: HTML code
        """
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
        app_path = self.window.core.config.get_app_path()
        icon_path = os.path.join(app_path, "data", "icons", "attachments.svg").replace("\\", "/")
        icon = f'<img src="file://{icon_path}" class="extra-src-icon">'
        num_str = f" [{num}]" if (num is not None and num_all is not None and num_all > 1) else ""
        url, path = self.window.core.filesystem.extract_local_url(url)
        return f'{icon} <b>{num_str}</b> <a href="{url}">{path}</a>'

    def prepare_tool_extra(self, ctx: CtxItem) -> str:
        """
        Prepare footer extra

        :param ctx: context item
        :return: HTML code
        """
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
        """
        Get all tips for the output view

        :return: JSON string of tips
        """
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
        """
        Build webview HTML code (fast path, minimal allocations)

        :param pid: process ID
        :return: HTML code
        """
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

        # Build file:// paths for FAB icons
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