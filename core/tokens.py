#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import tiktoken


def num_tokens_from_string(string, model="gpt-3.5-turbo"):
    """
    Get number of tokens from string

    :param string: string
    :param model: model name
    :return: number of tokens
    """
    try:
        if model is not None:
            encoding = tiktoken.encoding_for_model(model)
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    try:
        return len(encoding.encode(string))
    except Exception as e:
        print(e)
        return 0


def num_tokens_extra(model="gpt-3.5-turbo"):
    """
    Get number of extra tokens

    :param model: model name
    :return: number of tokens
    """
    tokens = 5
    if model is not None and model.startswith("gpt-4"):
        tokens = 6
    elif model is not None and model.startswith("text-davinci"):
        tokens = 5
    return tokens


def num_tokens_prompt(text, input_name, model="gpt-3.5-turbo"):
    """
    Get number of tokens from prompt

    :param text: prompt text
    :param input_name: input name
    :param model: model name
    :return: number of tokens
    """
    try:
        if model is not None:
            encoding = tiktoken.encoding_for_model(model)
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0

    # tags required tokens
    tokens_per_message = 4  # message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = -1

    if model is not None and model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    elif model is not None and model.startswith("text-davinci"):
        tokens_per_message = 1
        tokens_per_name = 0

    try:
        num_tokens += num_tokens_from_string(text, model)
    except Exception as e:
        print(e)

    if input_name is not None and input_name != "":
        num_tokens += tokens_per_message + tokens_per_name
    else:
        num_tokens += tokens_per_message

    return num_tokens


def num_tokens_from_context_item(item, model="gpt-3.5-turbo"):
    """
    Get number of tokens from context item

    :param item: context item
    :param model: model name
    :return: number of tokens
    """
    try:
        if model is not None:
            encoding = tiktoken.encoding_for_model(model)
        else:
            encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # tags required tokens
    tokens_per_message = 4  # message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = -1
    multiply = 2
    if model is not None and model.startswith("gpt-4"):
        tokens_per_message = 3
        tokens_per_name = 1
    elif model is not None and model.startswith("text-davinci"):
        tokens_per_message = 1
        tokens_per_name = 0
        multiply = 1

    num_tokens = 0
    num_tokens += tokens_per_message * multiply  # input + output

    try:
        num_tokens += len(encoding.encode(item.input))
    except Exception as e:
        print(e)

    try:
        num_tokens += len(encoding.encode(item.output))
    except Exception as e:
        print(e)

    try:
        num_tokens += len(encoding.encode('user'))
    except Exception as e:
        print(e)

    try:
        num_tokens += len(encoding.encode('assistant'))
    except Exception as e:
        print(e)

    if item.input_name != "" and item.input_name is not None:
        num_tokens += tokens_per_name
        try:
            num_tokens += len(encoding.encode(item.input_name))
        except Exception as e:
            print(e)
    if item.output_name != "" and item.output_name is not None:
        num_tokens += tokens_per_name
        try:
            num_tokens += len(encoding.encode(item.output_name))
        except Exception as e:
            print(e)

    return num_tokens
