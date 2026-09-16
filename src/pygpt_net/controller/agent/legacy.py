#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 11:30:00
# ================================================== #

import re

from typing import Optional, List, Dict, Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    PERSIST_HIDDEN_TOOL_CALLS,
)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.plugin.agent.prompts import (
    AUTONOMOUS_INSTRUCTION as DEFAULT_AUTONOMOUS_INSTRUCTION,
    CONTINUE_PROMPT as DEFAULT_CONTINUE_PROMPT,
    CONTINUE_ALWAYS_PROMPT as DEFAULT_CONTINUE_ALWAYS_PROMPT,
    PROMPT_GOAL_LEGACY as DEFAULT_PROMPT_GOAL_LEGACY,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Legacy:
    """Controller for the simple/legacy autonomous Agent mode.

    The provider/API request path is intentionally shared with ordinary chat.
    What makes this mode autonomous is only the small continuation loop below.
    Every user request owns one durable ``CtxItem``; later autonomous model
    messages and all tool round-trips are folded into partials/tasks of that item.
    """

    LEGACY_PROMPT_MARKERS = (
        "self-dialogue mode",
        "Any input that begins with 'user: '",
    )
    LEGACY_GOAL_PROMPT_MARKERS = (
        "## STATUS UPDATE:",
        "## ON GOAL FINISH:",
        "Attach this special command to response text",
    )

    RUN_ID_KEY = "_agent_run_id"

    # Defensive compatibility fallback. Some models occasionally print a native
    # function-looking call as plain assistant text instead of invoking the tool.
    # Only standalone lines at the END of the response are accepted so ordinary
    # discussion/code examples containing goal_update are never treated as control.
    TEXT_CONTROL_RE = re.compile(
        r'^\s*goal_update\s*\(\s*status\s*=\s*[\"\']?'
        r'(finished|pause|failed|wait)[\"\']?\s*\)\s*[.;]?\s*$',
        re.IGNORECASE,
    )

    AUTONOMOUS_INSTRUCTION = DEFAULT_AUTONOMOUS_INSTRUCTION

    AUTONOMOUS_INSTRUCTION_NO_CONTROL = """# AUTONOMOUS MODE

Execute the user's request as a multi-pass autonomous run. The original user request, its constraints, and requested deliverables define the scope and acceptance criterion. Treat the first plausible solution as provisional: unless the task is truly trivial/atomic or blocked on user input, do NOT consider the run complete after the first provider pass.

Rules:
- Preserve the original goal and constraints throughout the run. Do not invent user replies or widen the task into unrelated work.
- Work iteratively: make concrete progress, then deliberately re-examine the accumulated result from a different angle before deciding whether it is complete.
- After producing an initial solution, perform at least one distinct verification/refinement pass whenever the task has meaningful depth. Challenge assumptions, check requirement coverage, verify important claims/results, inspect edge cases and failure modes, look for inconsistencies, and improve robustness, precision, or usefulness where it materially helps the original request.
- Do not stop merely because the answer looks plausible or usable. Continue while there is a non-redundant in-scope avenue that can materially strengthen the result.
- Prefer a materially different next angle over repeating the same reasoning. Useful dimensions may include: unmet requirements, factual/technical verification, hidden assumptions, edge cases, failure modes, alternative approaches, trade-offs, consistency, robustness, precision, validation of tool/action results, and implications that directly affect the user's goal.
- Use available tools whenever they can materially improve correctness or are required to complete the task. Inspect actual tool results before deciding what follows; never assume success.
- Never present TODO-style suggestions such as "research X", "test Y", or "analyze Z" as if they were completed autonomous work. If an available tool can perform the check, perform it; otherwise do not fabricate results.
- For requested artifacts/actions, completion means the requested deliverable has actually been produced and, when practical, validated.
- Do not pad the run by restating, paraphrasing, or cosmetically expanding previous content. Every continuation should add new work, verification, correction, or a genuinely useful refinement.
- Always write user-facing output in the language of the original user request unless the user explicitly requests another language. Synthetic continuation instructions may be in English and must never change the response language.
- If missing information or a user decision is genuinely required, ask the minimum precise question needed. Do not guess.
- If a genuine blocker prevents further progress, explain it clearly instead of inventing progress.
- Completion gate: consider the substantive task complete only after it is done AND you have deliberately checked the accumulated result for additional material in-scope improvements from multiple distinct angles. For any non-trivial task, avoid treating the first pass as final.
- Auto-stop is disabled. Do not attempt to emit or imitate any autonomous run-control/status command; continuation and stopping are controlled by the application/user.
"""

    CONTINUE_PROMPT = DEFAULT_CONTINUE_PROMPT

    CONTINUE_PROMPT_NO_CONTROL = """This is an internal autonomous continuation of the SAME user request. Treat the accumulated answer as provisional, not as evidence that the task is already complete.

Re-read the original request and all work completed so far. Continue by selecting the highest-value DISTINCT in-scope angle that has not been adequately explored yet. Do real work on it now.

Prioritize, as applicable:
- an unmet requirement or incomplete requested deliverable,
- independent verification of an important claim, calculation, code path, action, or tool result,
- a hidden assumption that should be challenged,
- an edge case or failure mode that could change the result,
- an inconsistency, ambiguity, or weakly supported conclusion,
- a materially different in-scope approach or trade-off,
- a robustness, precision, correctness, or usability improvement that meaningfully strengthens the original result.

Do not finish simply because the previous pass looks good. For non-trivial tasks, there should normally be at least one deliberate post-solution verification/refinement pass beyond the initial answer, and often several different passes when useful. If one line of investigation is exhausted, switch to another relevant dimension rather than immediately concluding.

Use tools when they can verify or materially improve the work, and inspect their actual outputs. Do not invent pseudo-work, generic TODO lists, or speculative results. If genuine user input is required, ask the minimum precise question instead of guessing. If a blocker prevents useful progress, explain it clearly.

Auto-stop is disabled. Do not emit or imitate any autonomous run-control/status command. Continue according to the application's autonomous loop until the application or user stops it.

Output only concrete new/corrective material or a necessary consolidated replacement. Never repeat or paraphrase earlier text merely to consume an iteration. Always answer in the language of the original user request unless the user explicitly requested another language."""

    CONTINUE_ALWAYS_PROMPT = DEFAULT_CONTINUE_ALWAYS_PROMPT

    FINAL_PASS_PROMPT = """# FINAL AUTONOMOUS PASS
This is the last provider pass allowed by the configured iteration limit. Stay strictly within the original request. Do not introduce a new topic, new optional workstream, or a task that cannot be completed now. Resolve the most important remaining in-scope issue, correct any material error, complete any outstanding requested deliverable, and leave the result user-ready. If the request is already complete, add nothing merely for length; finish. Keep user-facing output in the language of the original user request unless explicitly requested otherwise."""

    ALWAYS_CONTINUE_STATUS_NOTE = """# ALWAYS CONTINUE OVERRIDE
Always continue is enabled. Do not voluntarily report completion and do not use the FINISHED state. Apparent completeness is a cue to choose another meaningful in-scope angle and continue deeper. Keep the run going indefinitely from the model's perspective. Only a genuine WAIT, PAUSE, or FAILED condition, or an external stop imposed by the application/user, may interrupt the run."""

    PREVIOUS_INSTRUCTION_DEFAULTS = (
        '# AUTONOMOUS MODE\n\nComplete the user\'s request; do not expand the topic merely because another iteration is available. The original user request, its constraints, and requested deliverables define the scope and the acceptance criterion for the entire run.\n\nRules:\n- Keep every action and every user-facing addition directly tied to the original request. Do not broaden into adjacent topics, generic audits, speculative optimizations, or optional categories unless they are required for correctness or clearly requested by the user.\n- Prefer correctness and completion over volume. More text is not progress. A continuation is justified only by a material omission, a real error/inconsistency, an important directly relevant clarification, an unfinished requested action/deliverable, or a concrete verification that materially affects the answer.\n- For simple informational or creative requests, answer the request to a normal high-quality standard and finish. Do not turn a simple request into an open-ended research, optimization, safety, business, sustainability, scaling, trend, or testing exercise unless that dimension is actually part of the user\'s goal.\n- Never present TODO-style suggestions such as "research X", "test Y", or "analyze Z" as autonomous progress when you have not actually performed them. If an available tool can perform a needed check, use it and inspect the real result. Otherwise do not invent pseudo-work.\n- Do not restate, paraphrase, or cosmetically expand previous content. Add only concrete new work that improves the result for the original request, or provide a corrected replacement when earlier content is materially wrong.\n- Preserve all original constraints. For requested artifacts/actions, completion means the requested result has actually been produced and, when practical, validated.\n- Always write user-facing output in the language of the original user request unless the user explicitly requests another language. Synthetic continuation instructions may be in English and must never change the response language.\n- If you need missing information or a decision from the user before you can continue, ask the minimum precise question needed and signal WAIT using the run-control mechanism described below. Do not guess.\n- Signal PAUSE only for a real intentional/temporary suspension with a concrete reason. Never use pause merely because the answer is complete, because no more useful ideas remain, or to escape an Always continue loop.\n- Signal FAILED only when the task cannot be completed in the current run because of a genuine failure/blocker.\n- When the original request is complete to a normal high-quality standard, signal FINISHED using the run-control mechanism described below. Do not keep searching for marginal extras.\n- Run-control signals are protocol actions, not user-facing prose. Never imitate a run-control call in visible assistant text. Follow the exact native/legacy run-control instructions supplied below.\n',
        '# AUTONOMOUS MODE\n\nComplete the user\'s request; do not expand the topic merely because another iteration is available. The original user request, its constraints, and requested deliverables define the scope and the acceptance criterion for the entire run.\n\nRules:\n- Keep every action and every user-facing addition directly tied to the original request. Do not broaden into adjacent topics, generic audits, speculative optimizations, or optional categories unless they are required for correctness or clearly requested by the user.\n- Prefer correctness and completion over volume. More text is not progress. A continuation is justified only by a material omission, a real error/inconsistency, an important directly relevant clarification, an unfinished requested action/deliverable, or a concrete verification that materially affects the answer.\n- For simple informational or creative requests, answer the request to a normal high-quality standard and finish. Do not turn a simple request into an open-ended research, optimization, safety, business, sustainability, scaling, trend, or testing exercise unless that dimension is actually part of the user\'s goal.\n- Never present TODO-style suggestions such as "research X", "test Y", or "analyze Z" as autonomous progress when you have not actually performed them. If an available tool can perform a needed check, use it and inspect the real result. Otherwise do not invent pseudo-work.\n- Do not restate, paraphrase, or cosmetically expand previous content. Add only concrete new work that improves the result for the original request, or provide a corrected replacement when earlier content is materially wrong.\n- Preserve all original constraints. For requested artifacts/actions, completion means the requested result has actually been produced and, when practical, validated.\n- Always write user-facing output in the language of the original user request unless the user explicitly requests another language. Synthetic continuation instructions may be in English and must never change the response language.\n- If you need missing information or a decision from the user before you can continue, ask the minimum precise question needed and call goal_update(status="wait") when available. Do not guess.\n- Use goal_update(status="pause") only for a real intentional/temporary suspension with a concrete reason. Never use pause merely because the answer is complete, because no more useful ideas remain, or to escape an Always continue loop.\n- Use goal_update(status="failed") only when the task cannot be completed in the current run because of a genuine failure/blocker.\n- When the original request is complete to a normal high-quality standard, call goal_update(status="finished") when available. Do not keep searching for marginal extras.\n- If you state that you are finished, waiting, pausing, or failed, you MUST send the matching goal_update status in the same turn when that control is available; prose alone does not control the run.\n',
        '# AUTONOMOUS MODE\n\nYou are executing one user task as a single autonomous run. The original user request, including its constraints and requested deliverables, is the acceptance criterion. Iterate until it is genuinely complete, paused, failed, or the configured iteration limit is reached.\n\nRules:\n- Preserve the original goal and constraints throughout the run. Do not simulate a conversation with yourself and do not invent user replies.\n- Always write user-facing responses in the language used by the original user request, unless the user explicitly asks for another language. Internal autonomous continuation instructions may be in English and must never change the response language.\n- Every iteration must add measurable value. Before acting, privately audit the accumulated work for unmet requirements, incorrect or unsupported claims, failed or unverified actions, missing edge cases, and material opportunities to improve correctness, robustness, precision, or usefulness. Do not expose this private audit or chain-of-thought.\n- Select the highest-value unresolved issue and work on it now. Do not merely describe what should be done next when you can actually do it.\n- Use available tools whenever they can materially improve correctness or are required to complete the task. Prefer native tool/function calls when the provider supports them. Inspect the actual tool result before deciding what to do next; never assume success.\n- For tasks that create or modify artifacts, completion means the requested deliverable has actually been produced and, when practical, validated. Describing a deliverable without creating it is not completion.\n- Do not pad the run by restating, paraphrasing, or cosmetically expanding earlier content. Add only new work, corrections, verification, or a necessary consolidated replacement when earlier material is materially wrong or inconsistent.\n- If the task cannot continue without information or a decision from the user, pause/wait instead of guessing.\n- Completion gate: finish only after checking that no material requirement, correction, verification, or clearly useful in-scope improvement remains. When complete, leave the accumulated result user-ready and signal completion with goal_update(status="finished") when that control is available.\n- Do not offer unrelated additional work after completion.\n',
        '# AUTONOMOUS MODE\n\nYou are executing one user task as a single autonomous run. The original user request, including its constraints and requested deliverables, is the acceptance criterion. Iterate until it is genuinely complete, paused, failed, or the configured iteration limit is reached.\n\nRules:\n- Preserve the original goal and constraints throughout the run. Do not simulate a conversation with yourself and do not invent user replies.\n- Every iteration must add measurable value. Before acting, privately audit the accumulated work for unmet requirements, incorrect or unsupported claims, failed or unverified actions, missing edge cases, and material opportunities to improve correctness, robustness, precision, or usefulness. Do not expose this private audit or chain-of-thought.\n- Select the highest-value unresolved issue and work on it now. Do not merely describe what should be done next when you can actually do it.\n- Use available tools whenever they can materially improve correctness or are required to complete the task. Prefer native tool/function calls when the provider supports them. Inspect the actual tool result before deciding what to do next; never assume success.\n- For tasks that create or modify artifacts, completion means the requested deliverable has actually been produced and, when practical, validated. Describing a deliverable without creating it is not completion.\n- Do not pad the run by restating, paraphrasing, or cosmetically expanding earlier content. Add only new work, corrections, verification, or a necessary consolidated replacement when earlier material is materially wrong or inconsistent.\n- If the task cannot continue without information or a decision from the user, pause/wait instead of guessing.\n- Completion gate: finish only after checking that no material requirement, correction, verification, or clearly useful in-scope improvement remains. When complete, leave the accumulated result user-ready and signal completion with goal_update(status="finished") when that control is available.\n- Do not offer unrelated additional work after completion.\n',
        "# AUTONOMOUS MODE\n\nYou are executing one user task autonomously. Work in a simple iterative loop until the task is complete, paused, failed, or the configured iteration limit is reached.\n\nRules:\n- Treat the original user message as the goal. Do not simulate a conversation with yourself or invent user replies.\n- On every iteration, perform the next useful action toward the goal and do not repeat previous text just to keep the loop running.\n- Use available tools whenever useful; prefer native tool/function calls when supported and verify every returned result.\n- If user input is required, pause/wait instead of guessing.\n- Keep intermediate output focused on useful progress; do not expose private chain-of-thought or artificial self-critique.\n- When complete, provide the final user-facing result and signal completion with goal_update(status=\"finished\") when available.",
        "# AUTONOMOUS MODE\n\nYou are executing one user task autonomously. Work in a simple iterative loop until the task is complete, paused, failed, or the configured iteration limit is reached.\n\nRules:\n- Treat the original user message as the goal. Do not simulate a conversation with yourself and do not invent user replies.\n- On every iteration, perform the next useful action toward the goal. Do not repeat previous text just to keep the loop running.\n- Use available tools whenever they are useful. Prefer native tool/function calls when the provider supports them; otherwise use the application's tool syntax.\n- After a tool result, inspect it and continue from the actual result. Do not assume a tool succeeded without checking its returned data.\n- You may use enabled tools without asking for permission unless a tool or safety policy explicitly requires user confirmation.\n- Keep intermediate assistant messages focused on useful progress/results; do not expose private chain-of-thought or artificial self-critique.\n- If the task cannot continue without information from the user, pause instead of guessing.\n- When the task is fully complete, provide the final user-facing result and signal completion with goal_update(status=\"finished\") when that control is available.\n- Do not offer unrelated additional work after completion.",
    )

    PREVIOUS_CONTINUE_DEFAULTS = (
        "This is an internal autonomous continuation of the SAME user request, not a new request and not permission to widen its scope.\n\nRe-read the original user request and the accumulated result. Then choose exactly one path:\n1. MATERIAL WORK REMAINS: perform the single highest-priority concrete action that is still required for the original request (missing requested content/deliverable, correction of a real error, directly relevant clarification, unfinished tool/action, or verification that can materially change the answer).\n2. USER INPUT IS REQUIRED: ask the minimum precise question needed, then signal WAIT using the run-control mechanism supplied in the system instructions.\n3. A REAL TEMPORARY SUSPENSION IS REQUIRED: explain the concrete reason briefly, then signal PAUSE using the run-control mechanism supplied in the system instructions.\n4. THE REQUEST IS COMPLETE: do not add filler or hunt for optional dimensions; signal FINISHED using the run-control mechanism supplied in the system instructions.\n\nA possible extra detail is NOT automatically a reason to continue. The threshold is material usefulness to the original request. Do not create generic checklists or drift into adjacent themes such as cost, sustainability, security, scaling, trends, process optimization, documentation, testing, or alternative use-cases unless the user's request makes them directly relevant. Never tell the user to research/test/analyze something as if that were completed work; either perform the needed action with available tools or omit it.\n\nOutput only concrete new/corrective material that directly advances the original request. Never repeat or paraphrase earlier text just to consume another iteration. Always answer in the language of the original user request unless the user explicitly requested another language.",
        'This is an internal autonomous continuation of the SAME user request, not a new request and not permission to widen its scope.\n\nRe-read the original user request and the accumulated result. Then choose exactly one path:\n1. MATERIAL WORK REMAINS: perform the single highest-priority concrete action that is still required for the original request (missing requested content/deliverable, correction of a real error, directly relevant clarification, unfinished tool/action, or verification that can materially change the answer).\n2. USER INPUT IS REQUIRED: ask the minimum precise question needed, then call goal_update(status="wait").\n3. A REAL TEMPORARY SUSPENSION IS REQUIRED: explain the concrete reason briefly, then call goal_update(status="pause").\n4. THE REQUEST IS COMPLETE: do not add filler or hunt for optional dimensions; call goal_update(status="finished").\n\nA possible extra detail is NOT automatically a reason to continue. The threshold is material usefulness to the original request. Do not create generic checklists or drift into adjacent themes such as cost, sustainability, security, scaling, trends, process optimization, documentation, testing, or alternative use-cases unless the user\'s request makes them directly relevant. Never tell the user to research/test/analyze something as if that were completed work; either perform the needed action with available tools or omit it.\n\nOutput only concrete new/corrective material that directly advances the original request. Never repeat or paraphrase earlier text just to consume another iteration. Always answer in the language of the original user request unless the user explicitly requested another language.',
        'Continue the same autonomous run. Re-evaluate the original user request against all work completed so far; do not assume the previous response is complete merely because it looks plausible.\n\nFor this pass:\n1. Identify the highest-value unresolved item: an unmet requirement or deliverable, an error or inconsistency, an unsupported assumption or claim, an unverified action/result, an important edge case, or a materially useful in-scope alternative/optimization.\n2. If such an item exists, work on it now. Use tools when they can verify or improve the result, and inspect their actual outputs.\n3. If no material improvement remains after that check, do not manufacture filler or repeat earlier text. Leave the accumulated answer as-is and finish the run with goal_update(status="finished") when available.\n\nOutput only genuinely new/corrective material or a necessary consolidated replacement. Do not paraphrase the previous answer just to keep the loop running. Always respond in the language of the original user request unless the user explicitly requested another language.',
        'Continue the same autonomous run. Re-evaluate the original user request against all work completed so far; do not assume the previous response is complete merely because it looks plausible.\n\nFor this pass:\n1. Identify the highest-value unresolved item: an unmet requirement or deliverable, an error or inconsistency, an unsupported assumption or claim, an unverified action/result, an important edge case, or a materially useful in-scope alternative/optimization.\n2. If such an item exists, work on it now. Use tools when they can verify or improve the result, and inspect their actual outputs.\n3. If no material improvement remains after that check, do not manufacture filler or repeat earlier text. Leave the accumulated answer as-is and finish the run with goal_update(status="finished") when available.\n\nOutput only genuinely new/corrective material or a necessary consolidated replacement. Do not paraphrase the previous answer just to keep the loop running.',
        "Continue the same autonomous run. Perform the next useful action toward the original goal, use and verify tools when needed, avoid repeating previous text, and when the task is fully complete provide the final result and finish with goal_update(status=\"finished\") when available.",
        "Continue the same autonomous run. Review the work already completed and the remaining goal, then perform the next useful action. Use tools if needed and verify their results. Do not repeat previous text. If the task is fully complete, give the final user-facing result and finish the run with goal_update(status=\"finished\") when available.",
        "Continue, or complete the run if the goal is fully achieved.",
    )

    PREVIOUS_ALWAYS_CONTINUE_DEFAULTS = (
        'This is an internal Always continue pass for the SAME user request. Always continue authorizes one more attempt to find a useful refinement; it does NOT authorize scope expansion.\n\nStay strictly inside the original user\'s goal. Prefer improving the CORE answer over inventing new categories. For this pass, perform at most one concrete refinement that materially improves the original result, such as correcting a factual/logic error, clarifying an ambiguity that matters to the request, verifying a key claim/result with an available tool, improving a core procedure/deliverable, resolving an inconsistency, or adding one major directly relevant caveat/alternative that was genuinely missing.\n\nDo NOT generate generic "further improvements" lists, meta-analysis, or adjacent-topic checklists. Do not branch into cost, sustainability, security, scaling, trends, industrialization, documentation, testing, organization, or other dimensions unless the original request explicitly requires them. Do not invent work by telling the user to research, test, compare, or analyze something you have not actually done.\n\nIf no concrete in-scope refinement remains, do not fabricate one and do not produce filler. Signal FINISHED using the run-control mechanism supplied in the system instructions, with no unnecessary user-facing text. The application may intentionally ignore finished while Always continue is enabled and request another pass. Never use wait or pause merely to escape that behavior; wait is only for missing user input, and pause is only for a genuine temporary suspension.\n\nAlways keep user-facing output in the language of the original user request unless the user explicitly requested another language.',
        'This is an internal Always continue pass for the SAME user request. Always continue authorizes one more attempt to find a useful refinement; it does NOT authorize scope expansion.\n\nStay strictly inside the original user\'s goal. Prefer improving the CORE answer over inventing new categories. For this pass, perform at most one concrete refinement that materially improves the original result, such as correcting a factual/logic error, clarifying an ambiguity that matters to the request, verifying a key claim/result with an available tool, improving a core procedure/deliverable, resolving an inconsistency, or adding one major directly relevant caveat/alternative that was genuinely missing.\n\nDo NOT generate generic "further improvements" lists, meta-analysis, or adjacent-topic checklists. Do not branch into cost, sustainability, security, scaling, trends, industrialization, documentation, testing, organization, or other dimensions unless the original request explicitly requires them. Do not invent work by telling the user to research, test, compare, or analyze something you have not actually done.\n\nIf no concrete in-scope refinement remains, do not fabricate one and do not produce filler. Call goal_update(status="finished") with no unnecessary text. The application may intentionally ignore finished while Always continue is enabled and request another pass. Never use wait or pause merely to escape that behavior; wait is only for missing user input, and pause is only for a genuine temporary suspension.\n\nAlways keep user-facing output in the language of the original user request unless the user explicitly requested another language.',
        'Continue the same autonomous run for another improvement pass even if the task already appears complete. Treat apparent completeness as a reason to deepen validation, not as a stop condition.\n\nFind and perform the highest-value new check or improvement that has not already been covered, for example: independently verify key claims or results, challenge assumptions, test edge cases/failure modes, improve robustness or precision, resolve inconsistencies, or evaluate a materially distinct in-scope alternative and its trade-offs. Use tools when useful and verify their actual outputs.\n\nDo not add filler, repeat a completion statement, or paraphrase earlier text. If one validation dimension finds nothing to improve, move to a different useful validation dimension. A normal goal_update(status="finished") is not a stop condition while Always continue is enabled; only the configured iteration limit or an explicit wait/pause/failed condition stops the run. Always keep user-facing output in the language of the original user request unless the user explicitly requested another language.',
        'Continue the same autonomous run for another improvement pass even if the task already appears complete. Treat apparent completeness as a reason to deepen validation, not as a stop condition.\n\nFind and perform the highest-value new check or improvement that has not already been covered, for example: independently verify key claims or results, challenge assumptions, test edge cases/failure modes, improve robustness or precision, resolve inconsistencies, or evaluate a materially distinct in-scope alternative and its trade-offs. Use tools when useful and verify their actual outputs.\n\nDo not add filler, repeat a completion statement, or paraphrase earlier text. If one validation dimension finds nothing to improve, move to a different useful validation dimension. A normal goal_update(status="finished") is not a stop condition while Always continue is enabled; only the configured iteration limit or an explicit wait/pause/failed condition stops the run.',
        "Continue the same autonomous run with the next useful action. Use and verify tools when needed, avoid repeating previous text, and continue until the configured iteration limit or a pause/failed/wait condition is reached.",
        "Continue the same autonomous run with the next useful action. Use tools if needed, verify results, and do not repeat previous text. Continue until the configured iteration limit or an explicit pause/failed/wait condition is reached.",
        "Continue reasoning...",
        "Continue reasoning",
    )

    PREVIOUS_GOAL_DEFAULTS = (
        '# AUTONOMOUS RUN CONTROL\nUse the special goal_update command for run state. Prose alone does not stop the loop. Emit the command at the end of the same response, for example:\n<tool>{"cmd":"goal_update","params":{"status":"wait"}}</tool>\n\nAllowed statuses:\n- finished: the ORIGINAL user request is complete to a normal high-quality standard; use this instead of pause when no material in-scope work remains.\n- wait: progress requires missing information or an explicit user decision; ask the minimum precise question first.\n- pause: a real intentional temporary suspension, not completion, repetition avoidance, or lack of new ideas.\n- failed: a genuine blocker/failure prevents completion in this run.\n\nIf you say or imply that the run is finished, waiting, paused, or failed, you MUST emit the matching goal_update command in that same turn. Do not emit goal_update for ordinary progress.\n',
        '# AUTONOMOUS RUN STATUS\nUse the special goal_update command only as a run-control signal. Put it at the end of the response in tool syntax, for example:\n<tool>{"cmd":"goal_update","params":{"status":"finished"}}</tool>\nAllowed statuses are: finished, wait, pause, failed.\nUse finished only when the task is fully complete. Use wait when user input is required, pause for an intentional pause, and failed when the task cannot be completed. Do not emit goal_update for ordinary progress updates.',
    )

    PROMPT_GOAL_NATIVE = """# AUTONOMOUS RUN CONTROL — NATIVE TOOL
The provider exposes `goal_update` as a real native tool/function. Run state MUST be sent by invoking that tool, never by printing tool syntax in the assistant text.

CRITICAL PROTOCOL RULES:
- Invoke the native `goal_update` tool/function when a run-control status is required.
- NEVER print a textual representation of the function call, its arguments, JSON, XML/tool markup, or any other imitation of a tool call in user-facing text.
- Do not mention the control call unless the user explicitly asks about internals.
- Prose such as "I am pausing" or "the task is finished" does not control the run by itself.

Statuses:
- finished: the ORIGINAL user request is complete to a normal high-quality standard. Use this instead of pause when there is simply no material in-scope work left.
- wait: progress requires missing information or an explicit decision from the user. Ask the minimum precise question needed, then invoke the tool with status=wait in the same turn.
- pause: intentionally suspend for a concrete temporary reason that is not task completion and does not merely mean "I have no more ideas".
- failed: a genuine blocker/failure prevents completion in this run.

If you say or imply that the run is finished, waiting, paused, or failed, invoke the native goal_update tool with the matching status in that same turn. Do not invoke it for ordinary progress.
"""

    PROMPT_GOAL_LEGACY = DEFAULT_PROMPT_GOAL_LEGACY


    def __init__(self, window=None):
        """
        Agent flow controller

        :param window: Window instance
        """
        self.window = window
        # Number of completed autonomous model steps in the current run. Tool
        # replies do not increment this counter.
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.finished = False
        self.terminal_status = None
        # Snapshot run-control options at USER_SEND so switching/focusing another
        # chat/mode while an async agent run is in progress cannot change its
        # termination semantics halfway through the task.
        self.run_active = False
        self.run_auto_stop = None
        self.run_always_continue = None
        # Autonomous callbacks can arrive after STOP because provider/stream
        # workers are asynchronous. A monotonically increasing run id isolates
        # those stale callbacks from a later manual user request.
        self.run_seq = 0
        self.run_id = None
        self.run_root = None
        self.allowed_cmds = [
            "goal_update",
        ]
        self.pause_status = ["pause", "failed", "wait"]
        self.prompt_goal_native = self.PROMPT_GOAL_NATIVE
        self.options = {
            "agent.iterations": {
                "type": "int",
                "slider": True,
                "label": "agent.iterations",
                "min": 0,
                "max": 100,
                "step": 1,
                "value": 3,
                "multiplier": 1,
            },
        }

    def setup(self):
        """Setup agent controller"""
        self.window.ui.add_hook("update.global.agent.iterations", self.hook_update)
        self.reload()

    def reload(self):
        """Reload agent toolbox options"""
        common = self.window.controller.agent.common
        common.normalize_stop_continue()
        common.sync_stop_continue_ui()

        self.window.controller.config.apply_value(
            parent_id="global",
            key="agent.iterations",
            option=self.options["agent.iterations"],
            value=self.window.core.config.get('agent.iterations'),
        )

    def update(self):
        """Update agent status"""
        iterations = "-"
        mode = self.window.core.config.get('mode')

        if self.get_always_continue():
            iterations_str = "∞"
        else:
            if mode in [
                MODE_AGENT,
                MODE_AGENT_LLAMA,
                MODE_AGENT_OPENAI,
            ]:
                iterations = int(self.window.core.config.get("agent.iterations"))
            elif self.is_inline():
                if self.window.controller.plugins.is_enabled("agent"):
                    iterations = int(self.window.core.plugins.get_option("agent", "iterations"))
            if iterations == 0:
                iterations_str = "∞"
            else:
                iterations_str = str(iterations)

        status = str(self.iteration) + " / " + iterations_str
        self.window.ui.nodes['status.agent'].setText(status)
        self.window.controller.agent.common.toggle_status()

    def get_auto_stop(self) -> bool:
        """Return auto-stop setting for global or inline autonomous mode."""
        if self.run_active and self.run_auto_stop is not None:
            return bool(self.run_auto_stop)
        if self.window.core.config.get('mode') == MODE_AGENT:
            return bool(self.window.core.config.get('agent.auto_stop'))
        if self.is_inline() and self.window.controller.plugins.is_enabled("agent"):
            try:
                return bool(self.window.core.plugins.get_option("agent", "auto_stop"))
            except Exception:
                return False
        return False

    def get_always_continue(self) -> bool:
        """Return whether the autonomous run should continue open-endedly."""
        if self.run_active and self.run_always_continue is not None:
            return bool(self.run_always_continue)
        if self.window.core.config.get('mode') == MODE_AGENT:
            return bool(self.window.core.config.get('agent.continue.always'))
        if self.is_inline() and self.window.controller.plugins.is_enabled("agent"):
            try:
                return bool(self.window.core.plugins.get_option("agent", "always_continue"))
            except Exception:
                return False
        return False

    def get_functions(self) -> List[Dict[str, Any]]:
        """Return the internal run-control function when Auto-stop is enabled.

        With Auto-stop disabled the model must not receive ``goal_update`` at
        all. Continuation/stopping is then controlled solely by the autonomous
        loop, its iteration budget, and explicit user/application stop actions.
        """
        if not self.get_auto_stop():
            return []

        if self.get_always_continue():
            instruction = (
                "NATIVE CONTROL TOOL: invoke this function only for a genuine wait, pause, or failed "
                "condition; never describe or imitate the call in assistant text. With Always continue "
                "enabled, do not use status=finished and do not voluntarily end the run because the "
                "current result appears complete. Keep working indefinitely from the model's perspective. "
                "wait, pause, and failed remain terminal and must be used only for their real meanings."
            )
        else:
            instruction = (
                "NATIVE CONTROL TOOL: invoke this function; never describe or imitate the call in assistant text. Use finished only when the original user request is "
                "complete, wait when missing user information/decision is required, pause for a real "
                "temporary suspension, and failed for a genuine blocker. If your response announces "
                "one of these states, call this function with the matching status in the same turn."
            )

        return [
            {
                "cmd": "goal_update",
                "instruction": instruction,
                "params": [
                    {
                        "name": "status",
                        "description": "autonomous run-control status; wait/pause/failed are always terminal",
                        "required": True,
                        "type": "str",
                        "enum": {
                            "status": ["finished", "pause", "failed", "wait"],
                        }
                    }
                ]
            }
        ]

    def normalize_instruction_prompt(self, prompt: Optional[str]) -> str:
        """Upgrade the historical self-dialogue default without overwriting custom prompts."""
        value = str(prompt or "").strip()
        if not value:
            return self.AUTONOMOUS_INSTRUCTION
        if all(marker in value for marker in self.LEGACY_PROMPT_MARKERS):
            return self.AUTONOMOUS_INSTRUCTION
        if self._matches_previous_default(value, self.PREVIOUS_INSTRUCTION_DEFAULTS):
            return self.AUTONOMOUS_INSTRUCTION
        return value

    def get_goal_prompt(self, auto_stop: Optional[bool] = None) -> str:
        """Return run-control instructions only when Auto-stop is enabled."""
        if auto_stop is None:
            auto_stop = self.get_auto_stop()
        if not auto_stop:
            return ""

        if self.window.core.command.is_native_enabled():
            value = self.PROMPT_GOAL_NATIVE
        else:
            value = str(self.window.core.prompt.get("agent.goal") or "").strip()
            if (not value
                    or all(marker in value for marker in self.LEGACY_GOAL_PROMPT_MARKERS)
                    or self._matches_previous_default(value, self.PREVIOUS_GOAL_DEFAULTS)):
                value = self.PROMPT_GOAL_LEGACY

        if self.get_always_continue():
            value += "\n\n" + self.ALWAYS_CONTINUE_STATUS_NOTE
        return value

    @staticmethod
    def _matches_previous_default(value: str, defaults) -> bool:
        """Return True only for known historical defaults; custom prompts stay untouched."""
        normalized = str(value or "").strip().casefold()
        return any(normalized == str(item).strip().casefold() for item in defaults)

    def get_continue_prompt(self) -> str:
        """Return the configured continuation prompt, upgrading known historical defaults."""
        core = self.window.core
        if self.get_always_continue():
            value = str(core.prompt.get("agent.continue.always") or "").strip()
            if not value or self._matches_previous_default(value, self.PREVIOUS_ALWAYS_CONTINUE_DEFAULTS):
                return self.CONTINUE_ALWAYS_PROMPT
            return value

        value = str(core.prompt.get("agent.continue") or "").strip()
        if not value or self._matches_previous_default(value, self.PREVIOUS_CONTINUE_DEFAULTS):
            if not self.get_auto_stop():
                return self.CONTINUE_PROMPT_NO_CONTROL
            return self.CONTINUE_PROMPT
        return value

    def apply_iteration_budget(self, prompt: str, iterations: int) -> str:
        """Add a final-pass guard when exactly one provider turn remains.

        Always-continue intentionally behaves as open-ended from the model's
        perspective. The application may still enforce an iteration budget, but
        the prompt must not encourage a voluntary finish on the last pass.
        """
        if self.get_always_continue():
            return prompt

        try:
            limit = max(0, int(iterations or 0))
        except (TypeError, ValueError):
            limit = 0
        if limit > 0 and self.iteration == limit - 1:
            return str(prompt or "").rstrip() + "\n\n" + self.FINAL_PASS_PROMPT
        return prompt

    def on_system_prompt(
            self,
            prompt: str,
            append_prompt: Optional[str] = "",
            auto_stop: bool = True,
    ) -> str:
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :param append_prompt: extra prompt (instruction)
        :param auto_stop: auto stop
        :return: updated prompt
        """
        prompt = str(prompt or "")
        if append_prompt is not None and str(append_prompt).strip() != "":
            instruction = self.normalize_instruction_prompt(append_prompt)
            # Do not expose the internal run-control protocol when Auto-stop is
            # disabled. Only replace the built-in/default autonomous prompt; a
            # user's custom prompt is preserved verbatim.
            if not auto_stop and instruction == self.AUTONOMOUS_INSTRUCTION:
                instruction = self.AUTONOMOUS_INSTRUCTION_NO_CONTROL
            prompt += "\n\n" + instruction

        if auto_stop:
            prompt += "\n\n" + self.get_goal_prompt(auto_stop=True)
        return prompt

    def on_input_before(self, prompt: str) -> str:
        """Keep real user input unchanged; API roles already distinguish user and assistant."""
        return prompt

    def _get_ctx_run_id(self, ctx: Optional[CtxItem]):
        """Return the autonomous run id inherited by a runtime context."""
        seen = set()
        current = ctx
        for _ in range(6):
            if current is None or id(current) in seen:
                break
            seen.add(id(current))
            extra = getattr(current, "extra", None)
            if isinstance(extra, dict) and self.RUN_ID_KEY in extra:
                return extra.get(self.RUN_ID_KEY)
            current = getattr(current, "turn_parent", None) or getattr(current, "prev_ctx", None)
        return None

    def bind_ctx_to_run(self, ctx: Optional[CtxItem]):
        """Tag a new provider context with its originating autonomous run."""
        if ctx is None:
            return None
        inherited = self._get_ctx_run_id(
            getattr(ctx, "turn_parent", None) or getattr(ctx, "prev_ctx", None)
        )
        run_id = inherited if inherited is not None else self.run_id
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        if run_id is not None:
            ctx.extra[self.RUN_ID_KEY] = run_id
        if (run_id == self.run_id
                and getattr(ctx, "turn_parent", None) is None
                and self.run_root is None):
            self.run_root = ctx
        return run_id

    def is_ctx_current_run(self, ctx: Optional[CtxItem], require_active: bool = True) -> bool:
        """Return True only when *ctx* belongs to the currently selected autonomous run."""
        if ctx is None or self.run_id is None:
            return False
        if require_active and not self.run_active:
            return False
        return self._get_ctx_run_id(ctx) == self.run_id

    def on_user_send(self, text: str):
        """Begin a new autonomous run and freeze its run-control options."""
        # Read the active configuration before setting run_active, otherwise the
        # getters would return the previous run's snapshot.
        self.run_active = False
        auto_stop = self.get_auto_stop()
        always_continue = self.get_always_continue()

        self.run_seq += 1
        self.run_id = self.run_seq
        self.run_root = None
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.finished = False
        self.terminal_status = None
        self.run_auto_stop = bool(auto_stop)
        self.run_always_continue = bool(always_continue)
        self.run_active = True
        self.window.controller.agent.legacy.update()

    def _queue_continue(self, ctx: CtxItem, prompt: str):
        """Queue one explicit autonomous continuation against the durable root turn."""
        if not prompt or self.stop or not self.is_ctx_current_run(ctx):
            return
        if self.window.controller.kernel.stack.waiting():
            return

        reply = ReplyContext()
        reply.type = ReplyContext.AGENT_CONTINUE
        reply.ctx = ctx
        reply.input = prompt

        context = BridgeContext()
        context.ctx = ctx
        context.reply_context = reply
        event = KernelEvent(KernelEvent.AGENT_CONTINUE, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def on_ctx_end(
            self,
            ctx: CtxItem,
            iterations: int = 0,
    ):
        """Advance the simple autonomous loop after a completed, tool-free step."""
        if ctx is None or ctx.sub_reply:
            return
        if not self.is_ctx_current_run(ctx):
            self.window.core.debug.info("[agent] Ignoring stale CTX_END from an older autonomous run.")
            return

        # A terminal goal signal is consumed before CTX_END. Count the response
        # that contained it, then finish without scheduling another provider call.
        if self.stop:
            return

        # A plain first assistant response normally has no partial yet. Persist
        # it now before scheduling the next autonomous provider turn; otherwise
        # creating the second partial would make the first response disappear
        # from the parent's composed output/history. Tool responses already
        # create their partial through record_tool_calls(), so ensure_part() is
        # intentionally idempotent here.
        self.window.core.ctx.ensure_part(
            ctx,
            name=getattr(ctx, "output_name", None),
        )

        self.iteration += 1
        self.window.controller.agent.legacy.update()

        if self.finished:
            self.on_stop(auto=True, preserve_finished=True)
            return

        # Always continue is truly open-ended. A configured iteration limit is
        # ignored in this mode; the run ends only on an explicit external stop
        # or a genuine wait/pause/failed control state.
        limit = 0 if self.get_always_continue() else max(0, int(iterations or 0))
        if limit > 0 and self.iteration >= limit:
            self.on_stop(auto=True)
            if self.window.core.config.get("agent.goal.notify"):
                self.window.ui.tray.show_msg(
                    trans("notify.agent.stop.title"),
                    trans("notify.agent.stop.content"),
                )
            return

        continue_prompt = self.prev_output or self.get_continue_prompt()
        continue_prompt = self.apply_iteration_budget(continue_prompt, limit)
        self._queue_continue(ctx, continue_prompt)

    def on_ctx_before(
            self,
            ctx: CtxItem,
            reverse_roles: bool = False,
    ):
        """Prepare one autonomous provider call."""
        self.bind_ctx_to_run(ctx)
        if not self.is_ctx_current_run(ctx):
            ctx.stopped = True
            return
        ctx.internal = True
        self.is_user = False
        if self.iteration == 0:
            ctx.first = True

        # Kept for the inline plugin compatibility option. Global Agent mode does
        # not request role reversal and therefore follows ordinary chat roles.
        if self.iteration > 0 \
                and self.iteration % 2 != 0 \
                and reverse_roles:
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name

    def on_ctx_after(self, ctx: CtxItem):
        """Prepare the next loop instruction; tool outputs remain in structured history."""
        if not self.is_ctx_current_run(ctx):
            return
        if self.stop or self.finished:
            self.prev_output = None
            return
        # Do not reuse ctx.extra_ctx here. It can contain a tool/plugin payload
        # already represented in the partial task graph and would feed the same
        # result back to the model a second time.
        self.prev_output = self.get_continue_prompt()

    def cmd(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
            cmds_raw: List[Dict[str, Any]] = None,
    ) -> bool:
        """Consume goal_update and return True if it terminates the current run."""
        if not self.is_ctx_current_run(ctx) or not self.get_auto_stop():
            return False
        my_commands = []
        for item in cmds or []:
            if isinstance(item, dict) and item.get("cmd") in self.allowed_cmds:
                my_commands.append(item)

        if cmds_raw:
            for item in cmds_raw:
                if (isinstance(item, dict)
                        and item.get("cmd") in self.allowed_cmds
                        and item not in my_commands):
                    my_commands.append(item)

        if not my_commands:
            return False

        for item in my_commands:
            try:
                params = item.get("params") if isinstance(item.get("params"), dict) else {}
                status = str(params.get("status") or "").strip().lower()
                if status not in ["finished", *self.pause_status]:
                    continue

                # ``goal_update`` is only advertised/executable while Auto-stop
                # is enabled. Always continue normally disables Auto-stop, but
                # keep this guard for defensive compatibility with stale state.
                if status == "finished" and self.get_always_continue():
                    self.window.core.debug.info(
                        "[agent] goal_update(finished) ignored because Always continue is enabled."
                    )
                    # Keep scanning: a provider may emit more than one control
                    # call and wait/pause/failed must remain terminal even when a
                    # preceding finished signal is intentionally ignored.
                    continue

                self.finished = True
                self.terminal_status = status
                self.prev_output = None
                if status == "finished":
                    self.window.update_status(trans('status.finished'))
                else:
                    self.window.update_status(trans('status.stopped'))

                if status == "finished" and self.window.core.config.get("agent.goal.notify"):
                    self.window.ui.tray.show_msg(
                        trans("notify.agent.goal.title"),
                        trans("notify.agent.goal.content"),
                    )
                return True
            except Exception as e:
                self.window.core.debug.error(e)
                return False
        return False

    def consume_text_control_fallback(self, ctx: CtxItem) -> bool:
        """Convert a trailing plain-text ``goal_update(...)`` pseudo-call to control.

        Native-capable models should call the function and legacy models should
        emit ``<tool>`` markup. This fallback exists only for provider/model
        non-compliance. It intentionally recognizes *only* standalone control
        lines forming the trailing block of the active response. Recognized lines
        are stripped from visible output and normalized into ``ctx.cmds_before``.
        """
        if ctx is None or not self.is_ctx_current_run(ctx) or not self.get_auto_stop():
            return False

        part = ctx.get_active_part()
        multi_part = part is not None and len(ctx.parts or []) > 1
        source = part.output if multi_part else ctx.output
        if not source or "goal_update" not in source:
            return False

        lines = str(source).splitlines(keepends=True)
        if not lines:
            return False

        idx = len(lines) - 1
        while idx >= 0 and not lines[idx].strip():
            idx -= 1

        statuses = []
        first_control = None
        while idx >= 0:
            match = self.TEXT_CONTROL_RE.match(lines[idx].strip())
            if not match:
                break
            statuses.append(match.group(1).lower())
            first_control = idx
            idx -= 1
            # Allow blank lines between repeated pseudo-calls at the tail.
            while idx >= 0 and not lines[idx].strip():
                idx -= 1

        if first_control is None:
            return False

        # Do not interpret a pseudo-call shown inside an unterminated Markdown
        # code fence as application control (e.g. a user asking for an example).
        if "".join(lines[:first_control]).count("```") % 2:
            return False

        statuses.reverse()
        cleaned = "".join(lines[:first_control]).rstrip()
        if multi_part:
            part.output = cleaned
            self.window.core.ctx.update_part(ctx, part, sync_item=True)
        else:
            ctx.output = cleaned

        recovered = [
            {"cmd": "goal_update", "params": {"status": status}}
            for status in statuses
        ]

        if self.window.core.command.is_native_enabled():
            # The provider did not create a native function call, so there is no
            # real call_id to acknowledge. Treat this model-compliance fallback
            # locally; synthesizing a function_call_output here would itself be
            # invalid for APIs such as OpenAI Responses.
            self.cmd(ctx, recovered, recovered)
            action = "local fallback"
        else:
            # Legacy/non-native command syntax has no provider call_id contract,
            # so route the recovered command through the regular tool lifecycle.
            existing = list(ctx.cmds_before or [])
            for cmd in recovered:
                if cmd not in existing:
                    existing.append(cmd)
            ctx.cmds_before = existing
            action = "tool fallback"

        self.window.core.debug.info(
            f"[agent] recovered plain-text goal_update pseudo-call as {action}: "
            + ", ".join(statuses)
        )
        return True

    def is_tool_enabled(self, cmd: str) -> bool:
        """Return whether ``cmd`` is an advertised autonomous control tool.

        The command still uses the regular chat tool lifecycle. This predicate is
        only used by the shared command filter so the internal tool is treated as
        executable even though it is not owned by a user-toggleable plugin.
        """
        if cmd not in self.allowed_cmds or not self.enabled():
            return False
        return any(item.get("cmd") == cmd for item in self.get_functions())

    def execute_tools(self, ctx: CtxItem, commands: List[Dict[str, Any]]) -> bool:
        """Execute autonomous control tools through the normal tool reply path.

        ``goal_update`` is advertised as a native/legacy function by this
        controller, but unlike ordinary tools it has no user-toggleable plugin
        owner. Execution therefore happens here while preserving the same
        protocol contract as plugin tools: the request is recorded as a task, a
        result is appended to ``ctx.results``/``ctx.extra['tool_output']``, and a
        REPLY_ADD is emitted so the provider receives a function_call_output with
        the original call_id before the conversation continues.
        """
        if ctx is None or not self.is_ctx_current_run(ctx):
            return False

        handled = []
        for item in commands or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("cmd") or "")
            if not self.is_tool_enabled(name):
                continue

            params = item.get("params") if isinstance(item.get("params"), dict) else {}
            status = str(params.get("status") or "").strip().lower()
            terminal = self.cmd(ctx, [item], [item])
            accepted = status in ["finished", *self.pause_status]
            result = {
                "ok": accepted,
                "status": status,
                "terminal": bool(terminal),
            }
            response = {
                "request": {
                    "cmd": name,
                    "params": dict(params),
                },
                "result": result,
            }
            handled.append(response)

            if (PERSIST_HIDDEN_TOOL_CALLS
                    or not self.window.core.command.is_tool_hidden(name)):
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra.setdefault("tool_output", []).append({
                    "cmd": name,
                    "result": result,
                })
            ctx.results.append(response)
            ctx.reply = True

        if not handled:
            return False

        context = BridgeContext()
        context.ctx = ctx
        self.window.dispatch(KernelEvent(KernelEvent.REPLY_ADD, {
            "context": context,
            "extra": {"response_type": "multiple" if len(handled) > 1 else "single"},
        }))
        return True

    def is_inline(self) -> bool:
        """Return True when the inline autonomous plugin is enabled."""
        return self.window.controller.plugins.is_type_enabled("agent")

    def enabled(self, check_inline=True) -> bool:
        """Return whether legacy/simple autonomous handling is active."""
        if not check_inline:
            return self.window.core.config.get('mode') == MODE_AGENT
        return self.window.core.config.get('mode') == MODE_AGENT or self.is_inline()

    def add_run(self):
        """Compatibility no-op: tool replies are not autonomous iterations."""
        self.update()

    def on_stop(self, auto: bool = False, preserve_finished: bool = False):
        """Stop the current autonomous loop without discarding its final counter."""
        self.window.controller.kernel.stack.lock()
        self.window.controller.chat.common.unlock_input()
        self.prev_output = None
        self.stop = True
        if not auto and self.run_root is not None:
            # Persist a per-context cancellation marker. kernel.halt is global and
            # gets cleared by the next manual send; without this marker an old
            # provider generator could wake up and continue after the new run starts.
            self.run_root.stopped = True
            if not isinstance(self.run_root.extra, dict):
                self.run_root.extra = {}
            self.run_root.extra["response_interrupted"] = True
            self.run_root.extra.pop("response_final", None)
            try:
                self.window.core.ctx.update_item(self.run_root)
            except Exception:
                pass
        self.run_active = False
        if not preserve_finished:
            self.finished = False
            self.terminal_status = None

        if auto:
            self.window.controller.idx.on_ctx_end(
                ctx=None,
                mode="agent",
            )

    def hook_update(self, key: str, value: Any, caller, *args, **kwargs):
        """Handle global agent toolbox option changes."""
        if self.window.core.config.get(key) == value:
            return
        if key == 'agent.iterations':
            self.window.core.config.set(key, int(value))
            self.window.core.config.save()
            self.update()
