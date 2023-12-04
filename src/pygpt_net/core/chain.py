import os
from .context import ContextItem

from langchain.llms import OpenAI, HuggingFaceHub
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
# from langchain.prompts.chat import ChatPromptTemplate


class Chain:
    def __init__(self, config, context):
        """
        Langchain Wrapper

        :param config: Config object
        """
        self.config = config
        self.context = context

        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.input_tokens = 0
        self.attachments = {}

        if not self.config.initialized:
            self.config.init()

    def build_chat_messages(self, prompt, system_prompt=None):
        """
        Builds chat messages dict

        :param prompt: Prompt
        :param system_prompt: System prompt (optional)
        :return: Messages dict
        """
        messages = []

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append(SystemMessage(content=system_prompt))
        else:
            if self.system_prompt is not None and self.system_prompt != "":
                messages.append(SystemMessage(content=self.system_prompt))

        # append messages from context (memory)
        if self.config.data['use_context']:
            items = self.context.get_all_items()
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append(HumanMessage(content=item.input))
                # output
                if item.output is not None and item.output != "":
                    messages.append(AIMessage(content=item.output))

        # append current prompt
        messages.append(HumanMessage(content=str(prompt)))
        return messages

    def build_completion(self, prompt):
        """
        Builds completion string

        :param prompt: Prompt (current)
        :return: Message string (parsed with context)
        """
        message = ""

        if self.system_prompt is not None and self.system_prompt != "":
            message += self.system_prompt

        if self.config.data['use_context']:
            items = self.context.get_all_items()
            for item in items:
                if item.input_name is not None \
                        and item.output_name is not None \
                        and item.input_name != "" \
                        and item.output_name != "":
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input_name + ": " + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output_name + ": " + item.output
                else:
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output

        # append names
        if self.user_name is not None \
                and self.ai_name is not None \
                and self.user_name != "" \
                and self.ai_name != "":
            message += "\n" + self.user_name + ": " + str(prompt)
            message += "\n" + self.ai_name + ":"
        else:
            message += "\n" + str(prompt)

        return message

    def chat(self, text, stream_mode=False):
        """
        Chat with LLM

        :param text:
        :param stream_mode:
        :return: LLM response
        """
        llm = None
        cfg = self.config.get_model_cfg(self.config.data['model'])
        if 'langchain' in cfg:
            if cfg['langchain']['llm'] == 'openai':
                os.environ['OPENAI_API_TOKEN'] = self.config.data["api_key"]
                llm = ChatOpenAI(model_name=self.config.data['model'])
            elif cfg['langchain']['llm'] == 'huggingface':
                os.environ['HUGGINGFACEHUB_API_TOKEN'] = cfg['langchain']['api_key']
                llm = HuggingFaceHub(
                    repo_id=self.config.data['model'], #  google/flan-t5-xl
                    # model_kwargs={'temperature': 1e-10}
                )

        # if no LLM here then raise exception
        if llm is None:
            raise Exception("Invalid LLM")

        messages = self.build_chat_messages(text)
        if stream_mode:
            return llm.stream(messages)
        else:
            return llm.invoke(messages)

    def completion(self, text, stream_mode=False):
        """
        Chat with LLM

        :param text:
        :param stream_mode:
        :return: LLM response
        """
        llm = None
        cfg = self.config.get_model_cfg(self.config.data['model'])
        if 'langchain' in cfg:
            if cfg['langchain']['llm'] == 'openai':
                os.environ['OPENAI_API_TOKEN'] = self.config.data["api_key"]
                llm = OpenAI(model_name=self.config.data['model'])
            elif cfg['langchain']['llm'] == 'huggingface':
                os.environ['HUGGINGFACEHUB_API_TOKEN'] = cfg['langchain']['api_key']
                llm = HuggingFaceHub(
                    repo_id=self.config.data['model'], #  google/flan-t5-xl
                    # model_kwargs={'temperature': 1e-10}
                )
        if llm is None:
            raise Exception("Invalid LLM")

        message = self.build_completion(text)
        if stream_mode:
            return llm.stream(message)
        else:
            return llm.invoke(message)

    def call(self, text, ctx, stream_mode=False):
        """
        Call LLM

        :param text: Input text
        :param ctx: Context (memory)
        :param stream_mode: Stream mode
        :return: LLM response
        """
        cfg = self.config.get_model_cfg(self.config.data['model'])
        response = None
        mode = 'chat'

        # get available modes
        if 'langchain' in cfg:
            if 'chat' in cfg['langchain']['mode']:
                mode = 'chat'
            elif 'completion' in cfg['langchain']['mode']:
                mode = 'completion'
        try:
            if mode == 'chat':
                response = self.chat(text, stream_mode)
            elif mode == 'completion':
                response = self.completion(text, stream_mode)

        except Exception as e:
            print("Error: " + str(e))
            raise e  # re-raise to window

        # async mode (stream)
        if stream_mode:
            # store context (memory)
            if ctx is None:
                ctx = ContextItem(self.config.data['mode'])
                ctx.set_input(text, self.user_name)

            ctx.stream = response
            ctx.set_output("", self.ai_name)
            self.context.add(ctx)
            return ctx

        if response is None:
            return None

        # get output
        output = None
        if mode == 'chat':
            output = response.content
        elif mode == 'completion':
            output = response

        # store context (memory)
        if ctx is None:
            ctx = ContextItem(self.config.data['mode'])
            ctx.set_input(text, self.user_name)

        ctx.set_output(output, self.ai_name)
        self.context.add(ctx)

        return ctx
