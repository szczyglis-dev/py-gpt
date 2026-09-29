#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 15:15:00                  #
# ================================================== #

DEFAULT_INITIAL_PLAN_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given a task and a set of tools, create a comprehensive, end-to-end plan to accomplish the task.
Keep in mind not every task needs to be decomposed into multiple sub-tasks if it is simple enough.
The plan should end with a sub-task that can achieve the overall task.

The tools available are:
{tools_str}

Overall Task: {task}
"""

DEFAULT_PLAN_REFINE_PROMPT = """\
You have the following prior context/memory (may be empty):
{memory_context}

Think step-by-step. Given an overall task, a set of tools, and completed sub-tasks, decide whether the overall task is already satisfied.
If not, update the remaining sub-tasks so that the overall task can still be completed.

Completion criteria (ALL must be true to set is_done=true):
- A final, user-facing answer that directly satisfies "Overall Task" already exists within "Completed Sub-Tasks + Outputs".
- The final answer matches any explicit format and language requested in "Overall Task".
- No critical transformation/summarization/finalization step remains among "Remaining Sub-Tasks" (e.g., steps like: provide/present/report/answer/summarize/finalize/deliver the result).
- The final answer does not rely on placeholders such as "will be provided later" or "see plan above".

If ANY of the above is false, set is_done=false.

Update policy:
- If the remaining sub-tasks are already reasonable and correctly ordered, do not propose changes: set is_done=false and omit "plan".
- Only propose a new "plan" if you need to REPLACE the "Remaining Sub-Tasks" (e.g., wrong order, missing critical steps, or new info from completed outputs).
- Do NOT repeat any completed sub-task. New sub-tasks must replace only the "Remaining Sub-Tasks".

Output schema:
- Return a JSON object matching the schema with fields: is_done (bool), reason (string), and optional plan (Plan).

The tools available are:
{tools_str}

Completed Sub-Tasks + Outputs:
{completed_outputs}

Remaining Sub-Tasks:
{remaining_sub_tasks}

Overall Task: {task}
"""

DEFAULT_EXECUTE_PROMPT = """\
You execute the given sub-task using the tools. Return concise outputs.
"""
