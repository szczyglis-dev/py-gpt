#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.12 19:00:00                  #
# ================================================== #

import tiktoken


def num_tokens_from_string(string, model="gpt-4"):
    """
    Returns number of tokens from string

    :param string: string
    :param model: model name
    :return: number of tokens
    """

    if string is None or string == "":
        return 0

    try:
        if model is not None:
            encoding = tiktoken.encoding_for_model(model)
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    try:
        return len(encoding.encode(str(string)))
    except Exception as e:
        print("Tokens calc exception", e)
        return 0


def num_tokens_extra(model="gpt-4"):
    """
    Returns number of extra tokens

    :param model: model name
    :return: number of tokens
    """
    return 3


def num_tokens_prompt(text, input_name, model="gpt-4"):
    """
    Returns number of tokens from prompt

    :param text: prompt text
    :param input_name: input name
    :param model: model name
    :return: number of tokens
    """
    model, tokens_per_message, tokens_per_name = get_tokens_values(model)
    num_tokens = 0

    try:
        num_tokens += num_tokens_from_string(text, model)
    except Exception as e:
        print("Tokens calc exception", e)

    if input_name is not None and input_name != "":
        num_tokens += tokens_per_message + tokens_per_name
    else:
        num_tokens += tokens_per_message

    return num_tokens


def num_tokens_completion(text, model="gpt-4"):
    """
    Returns number of tokens from prompt

    :param text: prompt text
    :param model: model name
    :return: number of tokens
    """
    model, tokens_per_message, tokens_per_name = get_tokens_values(model)
    num_tokens = 0

    if text is None or text != "":
        return 0

    try:
        num_tokens += num_tokens_from_string(text, model)
    except Exception as e:
        print("Tokens calc exception", e)

    return num_tokens


def num_tokens_only(text, model="gpt-4"):
    """
    Returns number of tokens from prompt

    :param text: prompt text
    :param model: model name
    :return: number of tokens
    """
    model, tokens_per_message, tokens_per_name = get_tokens_values(model)
    num_tokens = 0

    if text is None or text != "":
        return 0

    try:
        num_tokens += num_tokens_from_string(text, model)
    except Exception as e:
        print("Tokens calc exception", e)

    return num_tokens


def num_tokens_from_messages(messages, model="gpt-4"):
    """
    Returns number of tokens from prompt

    :param messages: messages
    :param model: model name
    :return: number of tokens
    """
    model, tokens_per_message, tokens_per_name = get_tokens_values(model)
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += num_tokens_from_string(value)
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def num_tokens_from_context_item(item, mode="chat", model="gpt-4"):
    """
    Returns number of tokens from context item

    :param item: context item
    :param mode: mode
    :param model: model name
    :return: number of tokens
    """
    model, tokens_per_message, tokens_per_name = get_tokens_values(model)
    num_tokens = 0

    if mode == "chat" or mode == "vision" or mode == "langchain" or mode == "assistant":
        # input message
        try:
            num_tokens += num_tokens_from_string(str(item.input), model)
        except Exception as e:
            print("Tokens calc exception", e)

        # output message
        try:
            num_tokens += num_tokens_from_string(str(item.output), model)
        except Exception as e:
            print("Tokens calc exception", e)
        # fixed tokens
        num_tokens += tokens_per_message * 2  # input + output
        num_tokens += tokens_per_name * 2  # input + output
        try:
            num_tokens += num_tokens_from_string("system", model) * 2  # input + output
        except Exception as e:
            print("Tokens calc exception", e)

        # input name
        if item.input_name is not None and item.input_name != "":
            tmp_name = item.input_name
        else:
            tmp_name = "user"
        try:
            num_tokens += num_tokens_from_string(tmp_name, model)
        except Exception as e:
            print("Tokens calc exception", e)

        # output name
        if item.output_name is not None and item.output_name != "":
            tmp_name = item.output_name
        else:
            tmp_name = "assistant"
        try:
            num_tokens += num_tokens_from_string(tmp_name, model)
        except Exception as e:
            print("Tokens calc exception", e)

    # build tmp message if completion
    elif mode == "completion":
        message = ""
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
        try:
            num_tokens += num_tokens_from_string(message, model)
        except Exception as e:
            print("Tokens calc exception", e)

    return num_tokens


def get_tokens_values(model):
    """
    Returns tokens values

    :param model:
    :return: model, tokens_per_message, tokens_per_name
    """
    tokens_per_message = 4  # message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = -1

    if model is not None:
        if model in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        }:
            tokens_per_message = 3
            tokens_per_name = 1
        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-3.5-turbo" in model:
            return get_tokens_values(model="gpt-3.5-turbo-0613")
        elif "gpt-4" in model:
            return get_tokens_values(model="gpt-4-0613")
        elif model.startswith("text-davinci"):
            tokens_per_message = 1
            tokens_per_name = 0

    return model, tokens_per_message, tokens_per_name
