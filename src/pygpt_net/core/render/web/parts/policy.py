#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Shared workflow rendering defaults."""

# ========================================
# Workflow status policy
# ========================================

WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_KEY = "agent.v2.single_status.live"
WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_KEY = "agent.v2.single_status.history"
WORKFLOW_SINGLE_STATUS_PER_PART_LIVE_DEFAULT = True
WORKFLOW_SINGLE_STATUS_PER_PART_HISTORY_DEFAULT = True

# ========================================
# Legacy agent identity
# ========================================

# UI-only actor label for legacy LlamaIndex Custom agents. The prefix is
# rendered from CtxItemPart.name and is never stored in part.output/ctx.output.
SHOW_LEGACY_AGENT_NAME_PREFIX = True
