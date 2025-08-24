#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 03:00:00                  #
# ================================================== #
# Based on OpenAI examples: https://github.com/openai/openai-agents-python/blob/main/examples
from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Any

from agents import Runner, custom_span

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.preset import PresetItem

from .agents.planner_agent import WebSearchItem, WebSearchPlan, get_planner_agent
from .agents.search_agent import get_search_agent
from .agents.writer_agent import ReportData, get_writer_agent


class ResearchManager:
    def __init__(
            self,
            window,
            preset: PresetItem,
            tools: List,
            ctx: CtxItem,
            bridge: ConnectionContext,
            stream: bool,
            planner_config: Dict[str, Any],
            search_config: Dict[str, Any],
            writer_config: Dict[str, Any],
            history: List[Dict] = None,
    ) -> None:
        self.window = window
        self.tools = tools
        self.preset = preset
        self.ctx = ctx
        self.bridge = bridge
        self.stream = stream
        self.begin = True
        self.planner_config = planner_config
        self.search_config = search_config
        self.writer_config = writer_config
        self.history = history if history is not None else []

    def send_stream(self, message: str) -> None:
        """
        Send a message to the stream.

        :param message: The message to send.
        """
        if not self.stream:
            return
        self.ctx.stream = message
        if self.bridge.on_step:
            self.bridge.on_step(self.ctx, self.begin)
        self.begin = False

    async def run(self, query: str) -> str:
        """
        Run the research process.

        :param query: The query to research.
        :return: The final report as a markdown string.
        """
        # extract input from history
        if self.history:
            self.history[-1]['content'] = f"Query: {self.history[-1]['content']}"

        self.send_stream(f"Starting research...\n")
        search_plan = await self._plan_searches(self.history)
        search_results = await self._perform_searches(search_plan)
        report = await self._write_report(query, search_results)
        final_report = f"Report summary\n\n{report.short_summary}"
        self.send_stream(final_report + "\n")
        self.send_stream(f"Report: {report.markdown_report}\n")
        follow_up_questions = "\n".join(report.follow_up_questions)
        self.send_stream(f"Follow up questions: {follow_up_questions}\n")
        return report.markdown_report

    async def _plan_searches(self, messages: list) -> WebSearchPlan:
        """
        Plan the searches based on the provided messages.

        :param messages: List of messages to analyze for planning.
        :return: WebSearchPlan: The plan containing search items.
        """
        self.send_stream("Planning searches...\n")
        agent = get_planner_agent(
            window=self.window,
            preset=self.preset,
            tools=self.tools,
            config=self.planner_config,
        )
        kwargs = {
            "input": messages,
        }
        result = await Runner.run(
            agent,
            **kwargs
        )
        self.send_stream(f"Will perform {len(result.final_output.searches)} searches\n")
        return result.final_output_as(WebSearchPlan)

    async def _perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """
        Perform the searches based on the search plan.

        :param search_plan: WebSearchPlan: The plan containing search items.
        :return: list[str]: A list of search results.
        """
        with custom_span("Search the web"):
            self.send_stream("Searching the web...\n")
            num_completed = 0
            tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches]
            results = []
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
                num_completed += 1
                self.send_stream(f"Searching... {num_completed}/{len(tasks)} completed\n")
            return results

    async def _search(self, item: WebSearchItem) -> str | None:
        """
        Perform a web search based on the provided search item.

        :param item: WebSearchItem: The item containing the search query and reason.
        :return: str | None: The search result as a string, or None if the search failed.
        """
        input = f"Search term: {item.query}\nReason for searching: {item.reason}"
        agent = get_search_agent(
            window=self.window,
            preset=self.preset,
            tools=self.tools,
            config=self.search_config,
        )
        kwargs = {
            "input": input,
        }
        try:
            result = await Runner.run(
                agent,
                **kwargs
            )
            return str(result.final_output)
        except Exception:
            return None

    async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
        """
        Write a report based on the original query and summarized search results.

        :param query: str: The original query to be reported on.
        :param search_results: list[str]: The summarized search results to include in the report.
        :return: ReportData: The final report data containing the markdown report and follow-up questions.
        """
        self.send_stream("Thinking about report...\n")
        input = f"Original query: {query}\nSummarized search results: {search_results}"
        agent = get_writer_agent(
            window=self.window,
            preset=self.preset,
            tools=self.tools,
            config=self.writer_config,
        )
        kwargs = {
            "input": input,
        }
        result = Runner.run_streamed(
            agent,
            **kwargs,
        )
        update_messages = [
            "Thinking about report...",
            "Planning report structure...",
            "Writing outline...",
            "Creating sections...",
            "Cleaning up formatting...",
            "Finalizing report...",
            "Finishing report...",
        ]
        last_update = time.time()
        next_message = 0
        async for _ in result.stream_events():
            if time.time() - last_update > 5 and next_message < len(update_messages):
                self.send_stream(update_messages[next_message] + "\n")
                next_message += 1
                last_update = time.time()

        return result.final_output_as(ReportData)
