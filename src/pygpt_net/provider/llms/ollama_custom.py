import json
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

from ollama import AsyncClient, Client

from llama_index.core.base.llms.generic_utils import (
    achat_to_completion_decorator,
    astream_chat_to_completion_decorator,
    chat_to_completion_decorator,
    stream_chat_to_completion_decorator,
)
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    ImageBlock,
    LLMMetadata,
    MessageRole,
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
)
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW, DEFAULT_NUM_OUTPUTS
from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.llms.llm import ToolSelection, Model
from llama_index.core.program.utils import process_streaming_objects, FlexibleModel
from llama_index.core.prompts import PromptTemplate
from llama_index.core.types import PydanticProgramMode

if TYPE_CHECKING:
    from llama_index.core.tools.types import BaseTool

DEFAULT_REQUEST_TIMEOUT = 30.0
dispatcher = get_dispatcher(__name__)


def get_additional_kwargs(
    response: Dict[str, Any], exclude: Tuple[str, ...]
) -> Dict[str, Any]:
    return {k: v for k, v in response.items() if k not in exclude}


def force_single_tool_call(response: ChatResponse) -> None:
    """Keep only one tool call when the agent disables parallel calls."""
    blocks = [b for b in response.message.blocks if isinstance(b, ToolCallBlock)]
    if len(blocks) <= 1:
        return
    response.message.blocks = [
        b for b in response.message.blocks if not isinstance(b, ToolCallBlock)
    ] + [blocks[0]]


def _plain_dict(value: Any) -> Dict[str, Any]:
    """Normalize Ollama SDK Pydantic/dict objects without depending on SDK version."""
    if isinstance(value, dict):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=True)
    try:
        return dict(value)
    except Exception:
        return {}


def _tool_call_dict(value: Any) -> Dict[str, Any]:
    item = _plain_dict(value)
    fn = item.get("function")
    if fn is not None and not isinstance(fn, dict):
        item["function"] = _plain_dict(fn)
    return item


class Ollama(FunctionCallingLLM):
    """
    Ollama LLM.

    Visit https://ollama.com/ to download and install Ollama.

    Run `ollama serve` to start a server.

    Run `ollama pull <name>` to download a model to run.

    Examples:
        `pip install llama-index-llms-ollama`

        ```python
        from llama_index.llms.ollama import Ollama

        llm = Ollama(model="llama2", request_timeout=60.0)

        response = llm.complete("What is the capital of France?")
        print(response)
        ```

    """

    base_url: str = Field(
        default="http://localhost:11434",
        description="Base url the model is hosted under.",
    )
    model: str = Field(description="The Ollama model to use.")
    temperature: Optional[float] = Field(
        default=None,
        description="The temperature to use for sampling.",
    )
    context_window: int = Field(
        default=-1,
        description="The maximum number of context tokens for the model.",
    )
    request_timeout: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT,
        description="The timeout for making http request to Ollama API server",
    )
    prompt_key: str = Field(
        default="prompt", description="The key to use for the prompt in API calls."
    )
    json_mode: bool = Field(
        default=False,
        description="Whether to use JSON mode for the Ollama API.",
    )
    additional_kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional model parameters for the Ollama API.",
    )
    is_function_calling_model: bool = Field(
        default=True,
        description="Whether the model is a function calling model.",
    )
    keep_alive: Optional[Union[float, str]] = Field(
        default="5m",
        description="controls how long the model will stay loaded into memory following the request(default: 5m)",
    )

    _client: Optional[Client] = PrivateAttr()
    _async_client: Optional[AsyncClient] = PrivateAttr()

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        temperature: Optional[float] = None,
        context_window: int = -1,
        request_timeout: Optional[float] = DEFAULT_REQUEST_TIMEOUT,
        prompt_key: str = "prompt",
        json_mode: bool = False,
        additional_kwargs: Optional[Dict[str, Any]] = None,
        client: Optional[Client] = None,
        async_client: Optional[AsyncClient] = None,
        is_function_calling_model: bool = True,
        keep_alive: Optional[Union[float, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            model=model,
            base_url=base_url,
            temperature=temperature,
            context_window=context_window,
            request_timeout=request_timeout,
            prompt_key=prompt_key,
            json_mode=json_mode,
            additional_kwargs=additional_kwargs or {},
            is_function_calling_model=is_function_calling_model,
            keep_alive=keep_alive,
            **kwargs,
        )

        self._client = client
        self._async_client = async_client

    @classmethod
    def class_name(cls) -> str:
        return "Ollama_llm"

    @property
    def metadata(self) -> LLMMetadata:
        """LLM metadata."""
        return LLMMetadata(
            context_window=self.get_context_window(),
            num_output=DEFAULT_NUM_OUTPUTS,
            model_name=self.model,
            is_chat_model=True,  # Ollama supports chat API for all models
            # TODO: Detect if selected model is a function calling model?
            is_function_calling_model=self.is_function_calling_model,
        )

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = Client(host=self.base_url, timeout=self.request_timeout)
        return self._client

    @property
    def async_client(self) -> AsyncClient:
        if self._async_client is None:
            self._async_client = AsyncClient(
                host=self.base_url, timeout=self.request_timeout
            )
        return self._async_client

    @property
    def _model_kwargs(self) -> Dict[str, Any]:
        base_kwargs = {
            "temperature": self.temperature,
            "num_ctx": self.get_context_window(),
        }
        return {
            **base_kwargs,
            **self.additional_kwargs,
        }

    def get_context_window(self) -> int:
        if self.context_window == -1:
            # Try to get the context window from the model info if not set
            info = self.client.show(self.model).modelinfo
            for key, value in info.items():
                if "context_length" in key:
                    self.context_window = int(value)
                    break

        # If the context window is still -1, use the default context window
        return self.context_window if self.context_window != -1 else DEFAULT_CONTEXT_WINDOW

    def _convert_to_ollama_messages(self, messages: Sequence[ChatMessage]) -> List[Dict[str, Any]]:
        """Convert LlamaIndex chat messages to Ollama native /api/chat messages.

        FunctionAgent 0.14.23 stores tool results as ``role=tool`` with only
        ``tool_call_id``.  For the native Ollama protocol the corresponding
        function name is carried as ``tool_name``.  This adapter deliberately
        uses the tool name as the tool id (see get_tool_calls_from_response),
        so the mapping is lossless and does not rely on OpenAI-compatible ids.
        """
        ollama_messages: List[Dict[str, Any]] = []
        for message in messages:
            role = message.role.value if hasattr(message.role, "value") else str(message.role)
            cur: Dict[str, Any] = {"role": role, "content": ""}
            tool_calls: List[Dict[str, Any]] = []

            for block in message.blocks:
                if isinstance(block, TextBlock):
                    cur["content"] += block.text or ""
                elif isinstance(block, ImageBlock):
                    cur.setdefault("images", []).append(
                        block.resolve_image(as_base64=True).read().decode("utf-8")
                    )
                elif isinstance(block, ThinkingBlock):
                    if block.content:
                        cur["thinking"] = block.content
                elif isinstance(block, ToolCallBlock):
                    kwargs = block.tool_kwargs
                    if isinstance(kwargs, str):
                        try:
                            kwargs = json.loads(kwargs)
                        except Exception:
                            kwargs = {}
                    tool_calls.append({
                        "function": {
                            "name": block.tool_name,
                            "arguments": kwargs or {},
                        }
                    })

            # Backward compatibility with LlamaIndex messages that keep tool calls
            # only in additional_kwargs.
            for raw_call in message.additional_kwargs.get("tool_calls", []) or []:
                call = _tool_call_dict(raw_call)
                fn = call.get("function") or {}
                name = str(fn.get("name") or call.get("name") or "")
                args = fn.get("arguments", call.get("arguments", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if name:
                    key = (name, json.dumps(args or {}, sort_keys=True, default=str))
                    existing = {
                        (str((x.get("function") or {}).get("name") or ""),
                         json.dumps((x.get("function") or {}).get("arguments") or {}, sort_keys=True, default=str))
                        for x in tool_calls
                    }
                    if key not in existing:
                        tool_calls.append({"function": {"name": name, "arguments": args or {}}})

            if tool_calls:
                cur["tool_calls"] = tool_calls

            if role == MessageRole.TOOL.value:
                tool_name = (
                    message.additional_kwargs.get("tool_name")
                    or message.additional_kwargs.get("name")
                    or message.additional_kwargs.get("tool_call_id")
                )
                if tool_name:
                    cur["tool_name"] = str(tool_name)

            ollama_messages.append(cur)
        return ollama_messages

    def _get_response_token_counts(self, raw_response: dict) -> dict:
        """Get the token usage reported by the response."""
        try:
            prompt_tokens = raw_response["prompt_eval_count"]
            completion_tokens = raw_response["eval_count"]
            total_tokens = prompt_tokens + completion_tokens
        except KeyError:
            return {}
        except TypeError:
            return {}
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _prepare_chat_with_tools(
        self,
        tools: List["BaseTool"],
        user_msg: Optional[Union[str, ChatMessage]] = None,
        chat_history: Optional[List[ChatMessage]] = None,
        verbose: bool = False,
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        tool_specs = [
            tool.metadata.to_openai_tool(skip_length_check=True) for tool in tools
        ]

        if isinstance(user_msg, str):
            user_msg = ChatMessage(role=MessageRole.USER, content=user_msg)

        messages = list(chat_history or [])
        if user_msg:
            messages.append(user_msg)

        return {
            "messages": messages,
            "tools": tool_specs or None,
        }

    def _validate_chat_with_tools_response(
        self,
        response: ChatResponse,
        tools: List["BaseTool"],
        allow_parallel_tool_calls: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Validate the response from chat_with_tools."""
        if not allow_parallel_tool_calls:
            force_single_tool_call(response)
        return response

    def get_tool_calls_from_response(
        self,
        response: "ChatResponse",
        error_on_no_tool_call: bool = True,
    ) -> List[ToolSelection]:
        """Extract native Ollama tool calls for LlamaIndex FunctionAgent."""
        blocks = [b for b in response.message.blocks if isinstance(b, ToolCallBlock)]
        if not blocks:
            # Compatibility with older response objects.
            for raw_call in response.message.additional_kwargs.get("tool_calls", []) or []:
                call = _tool_call_dict(raw_call)
                fn = call.get("function") or {}
                name = str(fn.get("name") or call.get("name") or "")
                args = fn.get("arguments", call.get("arguments", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if name:
                    blocks.append(ToolCallBlock(tool_name=name, tool_kwargs=args or {}))

        if not blocks:
            if error_on_no_tool_call:
                raise ValueError("Expected at least one tool call, but got 0 tool calls.")
            return []

        out: List[ToolSelection] = []
        for call in blocks:
            kwargs = call.tool_kwargs
            if isinstance(kwargs, str):
                try:
                    kwargs = json.loads(kwargs)
                except Exception:
                    kwargs = {}
            name = str(call.tool_name or "")
            if not name:
                continue
            # Ollama native messages identify the tool result by tool_name rather
            # than an OpenAI tool_call_id.  Reusing the name as the LlamaIndex id
            # lets FunctionAgent's role=tool scratchpad map back to tool_name.
            out.append(ToolSelection(
                tool_id=name,
                tool_name=name,
                tool_kwargs=cast(Dict[str, Any], kwargs or {}),
            ))
        return out

    @staticmethod
    def _blocks_from_native_message(message: Dict[str, Any], cumulative_text: Optional[str] = None, cumulative_thinking: Optional[str] = None, cumulative_calls: Optional[List[Dict[str, Any]]] = None):
        blocks = []
        thinking = cumulative_thinking if cumulative_thinking is not None else (message.get("thinking") or "")
        text = cumulative_text if cumulative_text is not None else (message.get("content") or "")
        calls = cumulative_calls if cumulative_calls is not None else [
            _tool_call_dict(x) for x in (message.get("tool_calls") or [])
        ]
        if thinking:
            blocks.append(ThinkingBlock(content=str(thinking)))
        blocks.append(TextBlock(text=str(text or "")))
        for call in calls:
            fn = call.get("function") or {}
            name = str(fn.get("name") or call.get("name") or "")
            kwargs = fn.get("arguments", call.get("arguments", {}))
            if isinstance(kwargs, str):
                try:
                    kwargs = json.loads(kwargs)
                except Exception:
                    kwargs = {}
            if name:
                blocks.append(ToolCallBlock(tool_name=name, tool_kwargs=kwargs or {}))
        return blocks

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        ollama_messages = self._convert_to_ollama_messages(messages)
        tools = kwargs.pop("tools", None)
        format_value = kwargs.pop("format", "json" if self.json_mode else None)
        response = self.client.chat(
            model=self.model,
            messages=ollama_messages,
            stream=False,
            format=format_value,
            tools=tools,
            options=self._model_kwargs,
            keep_alive=self.keep_alive,
        )
        raw = _plain_dict(response)
        message = _plain_dict(raw.get("message") or {})
        token_counts = self._get_response_token_counts(raw)
        if token_counts:
            raw["usage"] = token_counts
        return ChatResponse(
            message=ChatMessage(
                blocks=self._blocks_from_native_message(message),
                role=message.get("role", MessageRole.ASSISTANT),
            ),
            raw=raw,
        )

    @llm_chat_callback()
    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        ollama_messages = self._convert_to_ollama_messages(messages)
        tools = kwargs.pop("tools", None)
        format_value = kwargs.pop("format", "json" if self.json_mode else None)

        def gen() -> ChatResponseGen:
            response = self.client.chat(
                model=self.model,
                messages=ollama_messages,
                stream=True,
                format=format_value,
                tools=tools,
                options=self._model_kwargs,
                keep_alive=self.keep_alive,
            )
            response_txt = ""
            thinking_txt = ""
            seen_tool_calls = set()
            all_tool_calls: List[Dict[str, Any]] = []
            for chunk in response:
                raw = _plain_dict(chunk)
                message = _plain_dict(raw.get("message") or {})
                delta = str(message.get("content") or "")
                thinking_delta = str(message.get("thinking") or "")
                new_calls = [_tool_call_dict(x) for x in (message.get("tool_calls") or [])]
                if not delta and not thinking_delta and not new_calls:
                    continue
                response_txt += delta
                thinking_txt += thinking_delta
                for call in new_calls:
                    fn = call.get("function") or {}
                    key = (
                        str(fn.get("name") or call.get("name") or ""),
                        json.dumps(fn.get("arguments", call.get("arguments", {})) or {}, sort_keys=True, default=str),
                    )
                    if key in seen_tool_calls:
                        continue
                    seen_tool_calls.add(key)
                    all_tool_calls.append(call)
                token_counts = self._get_response_token_counts(raw)
                if token_counts:
                    raw["usage"] = token_counts
                yield ChatResponse(
                    message=ChatMessage(
                        blocks=self._blocks_from_native_message(
                            message,
                            cumulative_text=response_txt,
                            cumulative_thinking=thinking_txt,
                            cumulative_calls=all_tool_calls,
                        ),
                        role=message.get("role", MessageRole.ASSISTANT),
                    ),
                    delta=delta,
                    raw=raw,
                    additional_kwargs={"thinking_delta": thinking_delta or None},
                )
        return gen()

    @llm_chat_callback()
    async def astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        ollama_messages = self._convert_to_ollama_messages(messages)
        tools = kwargs.pop("tools", None)
        format_value = kwargs.pop("format", "json" if self.json_mode else None)

        async def gen() -> ChatResponseAsyncGen:
            response = await self.async_client.chat(
                model=self.model,
                messages=ollama_messages,
                stream=True,
                format=format_value,
                tools=tools,
                options=self._model_kwargs,
                keep_alive=self.keep_alive,
            )
            response_txt = ""
            thinking_txt = ""
            seen_tool_calls = set()
            all_tool_calls: List[Dict[str, Any]] = []
            async for chunk in response:
                raw = _plain_dict(chunk)
                message = _plain_dict(raw.get("message") or {})
                delta = str(message.get("content") or "")
                thinking_delta = str(message.get("thinking") or "")
                new_calls = [_tool_call_dict(x) for x in (message.get("tool_calls") or [])]
                if not delta and not thinking_delta and not new_calls:
                    continue
                response_txt += delta
                thinking_txt += thinking_delta
                for call in new_calls:
                    fn = call.get("function") or {}
                    key = (
                        str(fn.get("name") or call.get("name") or ""),
                        json.dumps(fn.get("arguments", call.get("arguments", {})) or {}, sort_keys=True, default=str),
                    )
                    if key in seen_tool_calls:
                        continue
                    seen_tool_calls.add(key)
                    all_tool_calls.append(call)
                token_counts = self._get_response_token_counts(raw)
                if token_counts:
                    raw["usage"] = token_counts
                yield ChatResponse(
                    message=ChatMessage(
                        blocks=self._blocks_from_native_message(
                            message,
                            cumulative_text=response_txt,
                            cumulative_thinking=thinking_txt,
                            cumulative_calls=all_tool_calls,
                        ),
                        role=message.get("role", MessageRole.ASSISTANT),
                    ),
                    delta=delta,
                    raw=raw,
                    additional_kwargs={"thinking_delta": thinking_delta or None},
                )
        return gen()

    @llm_chat_callback()
    async def achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        ollama_messages = self._convert_to_ollama_messages(messages)
        tools = kwargs.pop("tools", None)
        format_value = kwargs.pop("format", "json" if self.json_mode else None)
        response = await self.async_client.chat(
            model=self.model,
            messages=ollama_messages,
            stream=False,
            format=format_value,
            tools=tools,
            options=self._model_kwargs,
            keep_alive=self.keep_alive,
        )
        raw = _plain_dict(response)
        message = _plain_dict(raw.get("message") or {})
        token_counts = self._get_response_token_counts(raw)
        if token_counts:
            raw["usage"] = token_counts
        return ChatResponse(
            message=ChatMessage(
                blocks=self._blocks_from_native_message(message),
                role=message.get("role", MessageRole.ASSISTANT),
            ),
            raw=raw,
        )

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        return chat_to_completion_decorator(self.chat)(prompt, **kwargs)

    @llm_completion_callback()
    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        return await achat_to_completion_decorator(self.achat)(prompt, **kwargs)

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        return stream_chat_to_completion_decorator(self.stream_chat)(prompt, **kwargs)

    @llm_completion_callback()
    async def astream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseAsyncGen:
        return await astream_chat_to_completion_decorator(self.astream_chat)(
            prompt, **kwargs
        )

    @dispatcher.span
    def structured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> Model:
        if self.pydantic_program_mode == PydanticProgramMode.DEFAULT:
            llm_kwargs = llm_kwargs or {}
            llm_kwargs["format"] = output_cls.model_json_schema()

            messages = prompt.format_messages(**prompt_args)
            response = self.chat(messages, **llm_kwargs)

            return output_cls.model_validate_json(response.message.content or "")
        else:
            return super().structured_predict(
                output_cls, prompt, llm_kwargs, **prompt_args
            )

    @dispatcher.span
    async def astructured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> Model:
        if self.pydantic_program_mode == PydanticProgramMode.DEFAULT:
            llm_kwargs = llm_kwargs or {}
            llm_kwargs["format"] = output_cls.model_json_schema()

            messages = prompt.format_messages(**prompt_args)
            response = await self.achat(messages, **llm_kwargs)

            return output_cls.model_validate_json(response.message.content or "")
        else:
            return await super().astructured_predict(
                output_cls, prompt, llm_kwargs, **prompt_args
            )

    @dispatcher.span
    def stream_structured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> Generator[Union[Model, FlexibleModel], None, None]:
        """
        Stream structured predictions as they are generated.

        Args:
            output_cls: The Pydantic class to parse responses into
            prompt: The prompt template to use
            llm_kwargs: Optional kwargs for the LLM
            **prompt_args: Args to format the prompt with

        Returns:
            Generator yielding partial objects as they are generated

        """
        if self.pydantic_program_mode == PydanticProgramMode.DEFAULT:

            def gen(
                output_cls: Type[Model],
                prompt: PromptTemplate,
                llm_kwargs: Dict[str, Any],
                prompt_args: Dict[str, Any],
            ) -> Generator[Union[Model, FlexibleModel], None, None]:
                llm_kwargs = llm_kwargs or {}
                llm_kwargs["format"] = output_cls.model_json_schema()

                messages = prompt.format_messages(**prompt_args)
                response_gen = self.stream_chat(messages, **llm_kwargs)

                cur_objects = None
                for response in response_gen:
                    try:
                        objects = process_streaming_objects(
                            response,
                            output_cls,
                            cur_objects=cur_objects,
                            allow_parallel_tool_calls=False,
                            flexible_mode=True,
                        )
                        cur_objects = (
                            objects if isinstance(objects, list) else [objects]
                        )
                        yield objects
                    except Exception:
                        continue

            return gen(output_cls, prompt, llm_kwargs, prompt_args)
        else:
            return super().stream_structured_predict(
                output_cls, prompt, llm_kwargs, **prompt_args
            )

    @dispatcher.span
    async def astream_structured_predict(
        self,
        output_cls: Type[Model],
        prompt: PromptTemplate,
        llm_kwargs: Optional[Dict[str, Any]] = None,
        **prompt_args: Any,
    ) -> AsyncGenerator[Union[Model, FlexibleModel], None]:
        """Async version of stream_structured_predict."""
        if self.pydantic_program_mode == PydanticProgramMode.DEFAULT:

            async def gen(
                output_cls: Type[Model],
                prompt: PromptTemplate,
                llm_kwargs: Dict[str, Any],
                prompt_args: Dict[str, Any],
            ) -> AsyncGenerator[Union[Model, FlexibleModel], None]:
                llm_kwargs = llm_kwargs or {}
                llm_kwargs["format"] = output_cls.model_json_schema()

                messages = prompt.format_messages(**prompt_args)
                response_gen = await self.astream_chat(messages, **llm_kwargs)

                cur_objects = None
                async for response in response_gen:
                    try:
                        objects = process_streaming_objects(
                            response,
                            output_cls,
                            cur_objects=cur_objects,
                            allow_parallel_tool_calls=False,
                            flexible_mode=True,
                        )
                        cur_objects = (
                            objects if isinstance(objects, list) else [objects]
                        )
                        yield objects
                    except Exception:
                        continue

            return gen(output_cls, prompt, llm_kwargs, prompt_args)
        else:
            # Fall back to non-streaming structured predict
            return await super().astream_structured_predict(
                output_cls, prompt, llm_kwargs, **prompt_args
            )
