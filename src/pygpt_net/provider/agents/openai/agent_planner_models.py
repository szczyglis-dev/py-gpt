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

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

class SubTask(BaseModel):
    name: str = Field(..., description="The name of the sub-task.")
    input: str = Field(..., description="The input prompt for the sub-task.")
    expected_output: str = Field(..., description="The expected output of the sub-task.")
    dependencies: List[str] = Field(
        ...,
        description="Names of sub-tasks that must be completed before this sub-task.",
    )

class Plan(BaseModel):
    sub_tasks: List[SubTask] = Field(..., description="The sub-tasks in the plan.")

class PlanRefinement(BaseModel):
    is_done: bool = Field(..., description="Whether the overall task is already satisfied.")
    reason: Optional[str] = Field(..., description="Why the plan is complete or needs an update.")
    plan: Optional[Plan] = Field(
        ...,
        description="Replacement for the remaining plan, or null when no update is required.",
    )
