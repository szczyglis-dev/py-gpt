"""Multi-agent strategies executed entirely through LlamaIndex workflows."""
import asyncio
import json
from typing import Literal

from pydantic import BaseModel, Field
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, step
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.core.agents.runners.llama_events import forward_handler
from pygpt_net.core.agents.runners.llama_session import result_text
from pygpt_net.core.agents.custom.llama_index.router_streamer import RealtimeRouterStreamerLI
from pygpt_net.core.agents_v2.utils import effective_iteration_limit
from .events import StepEvent


class Feedback(BaseModel):
    feedback: str
    score: Literal['pass', 'needs_improvement', 'fail']


class Choice(BaseModel):
    answer_number: int = Field(ge=1)


class Search(BaseModel):
    query: str
    reason: str = ''


class Searches(BaseModel):
    searches: list[Search] = Field(min_length=1)


class Task(BaseModel):
    name: str
    input: str
    expected_output: str = ''
    dependencies: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    sub_tasks: list[Task]


class Refinement(BaseModel):
    is_done: bool
    reason: str | None = ''
    plan: Plan | None = None


def parse_output(text, schema):
    """Validate control output; never silently accept an invalid routing decision."""
    raw = str(text).strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    value = json.loads(raw)
    if isinstance(value, dict) and 'response' in value and isinstance(value['response'], dict):
        value = value['response']
    return schema.model_validate(value)


class ModesWorkflow(Workflow):
    def __init__(self, provider, window, kwargs):
        super().__init__(timeout=None, verbose=bool(kwargs.get('verbose', False)))
        self.provider = provider
        self.window = window
        self.kwargs = kwargs
        self.strategy = provider.strategy
        self.limit = int(kwargs.get('max_iterations', 10))
        if self.limit < 0:
            raise ValueError("Agent iteration limit cannot be negative")
        self.memories = {}
        self.expert_lock = asyncio.Lock()
        self.initial_history = []
        self.memory_token_limit = 64000
        self.on_stop = None
        self.sequence = 0
        # Same runtime input builder used by planner/supervisor/custom legacy
        # workflows. It injects shared attachment context and native ImageBlocks.
        self.input_builder = kwargs.get('input_builder')

    def run(self, query=None, *, memory=None, on_stop=None, **kwargs):
        self.on_stop = on_stop
        return super().run(query=query or '', memory=memory, **kwargs)

    def check_stop(self):
        if self.on_stop and self.on_stop():
            raise WorkflowCancelledByUser()

    def announce(self, ctx, name):
        self.check_stop()
        self.sequence += 1
        ctx.write_event_to_stream(StepEvent(name='next', index=self.sequence,
                                          meta={'agent_name': name}))

    def text(self, ctx, name, text):
        if text:
            ctx.write_event_to_stream(AgentStream(delta=text, response=text,
                                      current_agent_name=name, tool_calls=[], raw={}))

    async def role(self, ctx, section, query, *, name=None, schema=None, role_id=None, expert=None):
        """All child runs share the ordered stream/tool/cancellation bridge."""
        name = name or section.capitalize()
        self.announce(ctx, name)
        agent = self.provider.build_role(self.window, self.kwargs, section, name, schema,
                                         workflow=self, ctx=ctx, expert=expert, query=query)
        from pygpt_net.core.agents.session_memory import role_memory
        # Display labels (task names, generation numbers, localized names) are
        # transient. Roles and expert UUIDs identify the same agent next turn.
        identity = role_id or (getattr(expert, 'uuid', None) if expert is not None else None) or section
        key = (section, str(identity))
        if key not in self.memories:
            self.memories[key] = role_memory(
                self.window, self.provider, self.kwargs.get('context'), json.dumps(key),
                history=self.initial_history, token_limit=self.memory_token_limit)
        user_msg = self.input_builder(query) if callable(self.input_builder) else query
        handler = agent.run(user_msg=user_msg, memory=self.memories[key],
                            max_iterations=effective_iteration_limit(self.limit))
        prose = RealtimeRouterStreamerLI(fields=('feedback', 'reason')) if schema else None
        result, streamed = await forward_handler(
            handler, ctx, lambda: bool(self.on_stop and self.on_stop()), name=name,
            emit_text=schema in (None, Feedback, Refinement),
            text_filter=prose.handle_delta if prose else None)
        text = result_text(result)
        if schema:
            parsed = parse_output(text, schema)
            readable = getattr(parsed, 'feedback', None) or getattr(parsed, 'reason', '')
            if readable and not streamed:
                self.text(ctx, name, readable)
            return parsed
        if not streamed:
            self.text(ctx, name, text)
        elif text.startswith(streamed) and len(text) > len(streamed):
            self.text(ctx, name, text[len(streamed):])
        return text

    def option(self, section, key, default=None):
        value = self.provider.get_option(self.kwargs['context'].preset, section, key)
        return default if value is None else value

    async def feedback(self, ctx, query, evolve=False):
        generation = 0
        prompt = query
        limit = int(self.option('base', 'max_generations', self.limit)) if evolve else self.limit
        if limit < 0:
            raise ValueError('Generation limit cannot be negative')
        answer = ''
        while not limit or generation < limit:
            self.check_stop()
            generation += 1
            if evolve:
                count = max(1, int(self.option('base', 'num_parents', 2)))
                candidates = []
                for index in range(count):
                    candidates.append(await self.role(ctx, 'base', prompt,
                        name=f'Generation {generation} · Candidate {index + 1}', role_id=f'candidate:{index + 1}'))
                choice = await self.role(ctx, 'chooser', query + '\n\n' + '\n\n'.join(
                    f'Answer {i + 1}:\n{text}' for i, text in enumerate(candidates)), schema=Choice)
                if choice.answer_number > len(candidates):
                    raise ValueError('Chooser selected a nonexistent candidate')
                answer = candidates[choice.answer_number - 1]
            else:
                answer = await self.role(ctx, 'base', prompt, name='Agent')
            review = await self.role(ctx, 'feedback', f'Task:\n{query}\n\nAnswer:\n{answer}',
                                     name='Evaluator', schema=Feedback)
            if review.score == 'pass':
                break
            prompt = f'Task:\n{query}\n\nPrevious answer:\n{answer}\n\nFeedback:\n{review.feedback}'
        else:
            self.text(ctx, 'Evaluator', '\nIteration limit reached; returning the last selected answer.\n')
        # The last streamed segment was the evaluator, not the user-facing answer.
        self.announce(ctx, 'Final answer')
        return answer

    async def b2b(self, ctx, query):
        turn = 0
        answer = query
        # Match Bot 2 Bot: runs until Stop; an optional round limit is available.
        limit = int(self.option('conversation', 'max_rounds', 0))
        if limit < 0:
            raise ValueError('Conversation round limit cannot be negative')
        while not limit or turn < limit:
            for section in ('bot_1', 'bot_2'):
                self.check_stop()
                answer = await self.role(ctx, section, answer,
                                         name=self.option(section, 'name', section))
            turn += 1
        return answer

    async def research(self, ctx, query):
        plan = await self.role(ctx, 'planner', query, schema=Searches)
        results = []
        for item in plan.searches:
            result = await self.role(ctx, 'search', f'{item.query}\n{item.reason}',
                                     name='Researcher')
            results.append(f'Query: {item.query}\n{result}')
        return await self.role(ctx, 'writer', f'Task:\n{query}\n\nResearch:\n' + '\n\n'.join(results),
                               name='Writer')

    async def planner(self, ctx, query):
        plan = await self.role(ctx, 'planner', query, schema=Plan)
        completed = {}
        steps = 0
        while plan.sub_tasks:
            self.check_stop()
            remaining = [task for task in plan.sub_tasks if task.name not in completed]
            if not remaining:
                break
            if self.limit and steps >= self.limit:
                raise RuntimeError('Planner reached the step limit before completing the plan')
            names = [task.name for task in remaining]
            if len(set(names)) != len(names):
                raise ValueError('Planner returned duplicate task names')
            ready = next((task for task in remaining if all(dep in completed for dep in task.dependencies)), None)
            if ready is None:
                raise ValueError('Planner returned cyclic or missing dependencies')
            self.text(ctx, 'Planner', f'\n\n{ready.name}: {ready.input}\n')
            context = '\n\n'.join(f'{name}:\n{answer}' for name, answer in completed.items())
            completed[ready.name] = await self.role(ctx, 'step',
                f'Task: {query}\nSubtask: {ready.input}\nExpected: {ready.expected_output}\nCompleted:\n{context}',
                name=ready.name)
            steps += 1
            if self.option('refine', 'after_each_subtask', True) or len(remaining) == 1:
                refinement = await self.role(ctx, 'refine', f'Task: {query}\nRemaining: {[t.model_dump() for t in remaining if t.name not in completed]}\nCompleted:\n' +
                    '\n\n'.join(f'{name}: {answer}' for name, answer in completed.items()), schema=Refinement)
                if refinement.is_done:
                    break
                if refinement.plan is not None:
                    plan = refinement.plan
        return await self.role(ctx, 'step', f'Give the final answer to: {query}\nResults:\n' +
                               '\n\n'.join(completed.values()), name='Final answer')

    @step
    async def execute(self, ctx: Context, ev: StartEvent) -> StopEvent:
        memory = ev.get('memory')
        if memory is not None:
            self.initial_history = list(await memory.aget_all())
            self.memory_token_limit = getattr(memory, "token_limit", None) or 64000
        query = ev.get('query', '')
        if self.strategy == 'b2b':
            answer = await self.b2b(ctx, query)
        elif self.strategy in ('feedback', 'experts_feedback', 'evolve'):
            answer = await self.feedback(ctx, query, evolve=self.strategy == 'evolve')
        elif self.strategy == 'researcher':
            answer = await self.research(ctx, query)
        elif self.strategy == 'planner':
            answer = await self.planner(ctx, query)
        else:
            answer = await self.role(ctx, 'base', query, name='Agent')
        self.check_stop()
        return StopEvent(result=answer)
