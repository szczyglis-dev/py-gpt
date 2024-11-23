#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 21:00:00                  #
# ================================================== #

import copy
import os
import shutil
import uuid

from shutil import copyfile

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxMeta, CtxItem


class Context:
    def __init__(self, window=None):
        """
        Context attachment core

        :param window: Window instance
        """
        self.window = window
        self.dir_index = "index"
        self.summary_prompt = """
        Summarize the text below by extracting the most important information, 
        especially those that may help answer the question: 

        `{query}`. 

        If the answer to the question is not in the text to summarize, 
        simply return a summary of the entire content. 
        Do not include anything other than the summary itself in your response. 
        The response should not contain any phrases other than the summary of the content itself:        

        # Example of a bad response:        

        `According to the text you sent, item X is located at place Y.`        

        # Example of a correct response:        

        `[filename] Item X is located at place Y.`        

        # Content to summarize:

        `{content}`
        """

    def get_all(self, meta: CtxMeta) -> list:
        """
        Get all attachments for meta

        :param meta: CtxMeta instance
        :return: list of attachments
        """
        return meta.additional_ctx

    def get_dir(self, meta: CtxMeta) -> str:
        """
        Get directory for meta

        :param meta: CtxMeta instance
        :return: directory path
        """
        meta_uuid = str(meta.uuid)
        return os.path.join(self.window.core.config.get_user_dir("ctx_idx"), meta_uuid)

    def get_context_text(self, ctx: CtxItem, filename: bool = False) -> str:
        """
        Get raw text context for meta

        :param ctx: CtxItem instance
        :param filename: append filename
        :return: raw context
        """
        meta = ctx.meta
        meta_path = self.get_dir(meta)
        context = ""
        if os.path.exists(meta_path) and os.path.isdir(meta_path):
            for file in meta.additional_ctx:
                if "type" not in file or file["type"] != "local_file":
                    continue
                file_id = file["uuid"]
                file_idx_path = os.path.join(meta_path, file_id)
                text_path = os.path.join(file_idx_path, file_id + ".txt")
                if filename:
                    context += "Filename: {}\n".format(file["name"]) + "\n"
                if os.path.exists(text_path):
                    with open(text_path, "r") as f:
                        context += f.read() + "\n\n"
        return context

    def query_context(self, meta: CtxMeta, query: str) -> str:
        """
        Query the index for context

        :param meta : CtxMeta instance
        :param query: query string
        :return: query result
        """
        meta_path = self.get_dir(meta)
        if not os.path.exists(meta_path) or not os.path.isdir(meta_path):
            return ""
        idx_path = os.path.join(self.get_dir(meta), self.dir_index)
        model = None
        result = self.window.core.idx.chat.query_attachment(query, idx_path, model)

        if self.is_verbose():
            print("Attachments: query result: {}".format(result))

        return result

    def summary_context(self, ctx: CtxItem, query: str) -> str:
        """
        Get summary of the context

        :param ctx: CtxItem instance
        :param query: query string
        :return: query result
        """
        model_item = None
        model = self.window.core.config.get("ctx.attachment.summary.model", "gpt-4o-mini")
        if model:
            model_item = self.window.core.models.get(model)

        if model_item is None:
            raise Exception("Attachments: summary model not found: {}".format(model))

        if self.is_verbose():
            print("Attachments: using summary model: {}".format(model))

        prompt = self.summary_prompt.format(
            query=str(query).strip(),
            content=str(self.get_context_text(ctx, filename=True)).strip(),
        )
        if self.is_verbose():
            print("Attachments: summary prompt: {}".format(prompt))

        ctx = CtxItem()
        bridge_context = BridgeContext(
            ctx=ctx,
            prompt=prompt,
            stream=False,
            model=model_item,
        )
        event = KernelEvent(KernelEvent.CALL, {
            'context': bridge_context,
            'extra': {},
        })
        self.window.dispatch(event)
        response = event.data.get("response")
        if self.is_verbose():
            print("Attachments: summary received: {}".format(response))
        return response

    def upload(self, meta: CtxMeta, attachment: AttachmentItem, prompt: str) -> dict:
        """
        Upload attachment for context

        :param meta: CtxMeta instance
        :param attachment: AttachmentItem instance
        :param prompt: user input prompt
        :return: Dict with attachment data
        """
        if self.is_verbose():
            print("Uploading for meta ID: {}".format(meta.id))

        # prepare idx dir
        name = os.path.basename(attachment.path)
        file_id = str(uuid.uuid4())
        meta_path = self.get_dir(meta)
        file_idx_path = os.path.join(meta_path, file_id)
        index_path = os.path.join(meta_path, self.dir_index)
        os.makedirs(meta_path, exist_ok=True)
        os.makedirs(file_idx_path, exist_ok=True)

        if self.is_verbose():
            print("Attachments: created path: {}".format(meta_path))
            print("Attachments: vector index path: {}".format(index_path))

        # copy raw file
        raw_path = os.path.join(file_idx_path, name)
        if os.path.exists(raw_path):
            os.remove(raw_path)
        copyfile(attachment.path, raw_path)

        # extract text content using data loader
        loader_kwargs = {
            "prompt": prompt,
        }  # extra loader kwargs
        text = self.window.core.idx.indexing.read_text_content(
            path=raw_path,
            loader_kwargs=loader_kwargs,
        )
        if text:
            text_path = os.path.join(file_idx_path, file_id + ".txt")
            with open(text_path, "w") as f:
                f.write(text)

            if self.is_verbose():
                print("Attachments: read text content {}".format(text))

        tokens = 0
        if text:
            tokens = self.window.core.tokens.from_str(text)

        # index file to ctx index
        model = None
        doc_ids = self.window.core.idx.indexing.index_attachment(attachment.path, index_path, model)

        if self.is_verbose():
            print("Attachments: indexed. Doc IDs: {}".format(doc_ids))

        result = {
            "name": name,
            "path": attachment.path,
            "type": "local_file",
            "uuid": str(file_id),
            "doc_ids": doc_ids,
            "indexed": True,
            "content_type": "text",
            "size": os.path.getsize(attachment.path),
            "length": len(text),
            "tokens": tokens,
        }

        if self.is_verbose():
            print("Attachments: uploaded: {}".format(result))

        return result

    def duplicate(self, from_meta_id: int, to_meta_id: int) -> bool:
        """
        Duplicate attachments from one meta to another

        :param from_meta_id: From meta id
        :param to_meta_id: To meta id
        :return
        """
        from_meta = self.window.core.ctx.get_meta_by_id(from_meta_id)
        to_meta = self.window.core.ctx.get_meta_by_id(to_meta_id)

        if from_meta is None or to_meta is None:
            return False
        for item in from_meta.additional_ctx:
            to_meta.additional_ctx.append(copy.deepcopy(item))
        self.window.core.ctx.save(to_meta.id)

        # copy index directory
        from_meta_path = self.get_dir(from_meta)
        to_meta_path = self.get_dir(to_meta)
        if os.path.exists(from_meta_path) and os.path.isdir(from_meta_path):
            shutil.copytree(from_meta_path, to_meta_path)
            if self.is_verbose():
                print("Attachments copied from {} to: {}".
                                           format(from_meta_path, to_meta_path))
        return True

    def count(self, meta: CtxMeta) -> int:
        """
        Count attachments for meta

        :param meta: CtxMeta instance
        :return: number of attachments
        """
        return len(meta.additional_ctx)

    def delete(self, meta: CtxMeta, item: dict, delete_files: bool = False):
        """
        Delete attachment

        :param meta: CtxMeta instance
        :param item: AttachmentItem instance
        :param delete_files: delete files
        """
        meta.additional_ctx.remove(item)
        self.window.core.ctx.save(meta.id)
        if delete_files:
            self.delete_local(meta, item)
        if len(meta.additional_ctx) == 0:
            self.delete_index(meta)

    def delete_by_meta(self, meta: CtxMeta):
        """
        Delete all attachments for meta

        :param meta: CtxMeta instance
        """
        self.delete_index(meta)

    def delete_by_meta_id(self, meta_id: int):
        """
        Delete all attachments for meta by id

        :param meta_id: Meta id
        """
        meta = self.window.core.ctx.get_meta_by_id(meta_id)
        if meta is not None:
            self.delete_index(meta)

    def reset_by_meta_id(self, meta_id: int, delete_files: bool = False):
        """
        Delete all attachments for meta by id

        :param meta_id: Meta id
        :param delete_files: delete files
        """
        meta = self.window.core.ctx.get_meta_by_id(meta_id)
        if meta is not None:
            self.reset_by_meta(meta, delete_files)

    def reset_by_meta(self, meta: CtxMeta, delete_files: bool = False):
        """
        Delete all attachments for meta

        :param meta: CtxMeta instance
        :param delete_files: delete files
        """
        meta.additional_ctx = []
        self.window.core.ctx.save(meta.id)
        if delete_files:
            self.delete_index(meta)

    def clear(self, meta: CtxMeta, delete_files: bool = False):
        """
        Clear all attachments by ctx meta

        :param meta: CtxMeta instance
        :param delete_files: delete files
        """
        meta.additional_ctx = []
        self.window.core.ctx.save(meta.id)
        if delete_files:
            self.delete_index(meta)

    def delete_index(self, meta: CtxMeta):
        """
        Delete index by ctx meta

        :param meta: CtxMeta instance
        """
        meta_path = self.get_dir(meta)
        if os.path.exists(meta_path) and os.path.isdir(meta_path):
            shutil.rmtree(meta_path)
            if self.is_verbose():
                print("Attachment deleted dir: {}".format(meta_path))

    def delete_local(self, meta: CtxMeta, item: dict):
        """
        Delete local attachment

        :param meta: CtxMeta instance
        :param item: additional context item
        """
        file_id = item["uuid"]
        meta_path = self.get_dir(meta)
        index_path = os.path.join(meta_path, self.dir_index)
        file_idx_path = os.path.join(meta_path, file_id)
        if item["type"] == "local_file":
            if os.path.exists(file_idx_path):
                for f in os.listdir(file_idx_path):
                    os.remove(os.path.join(file_idx_path, f))
                    if self.is_verbose():
                        print("Attachment deleted: {}".format(f))
                os.rmdir(file_idx_path)

        # delete from index
        if "doc_ids" in item and isinstance(item["doc_ids"], list):
            for doc_id in item["doc_ids"]:
                self.window.core.idx.indexing.remove_attachment(index_path, doc_id)
                if self.is_verbose():
                    print("Attachment deleted doc ID: {}".format(doc_id))

    def truncate(self):
        """Truncate all attachments"""
        try:
            idx_path = self.window.core.config.get_user_dir("ctx_idx")
            if os.path.exists(idx_path) and os.path.isdir(idx_path):
                shutil.rmtree(idx_path)
            os.makedirs(idx_path, exist_ok=True)
        except Exception as e:
            self.window.core.debug.error("Attachment.truncate", e)

    def is_verbose(self) -> bool:
        """
        Check if verbose mode is enabled

        :return: True if verbose mode is enabled
        """
        return self.window.core.config.get("ctx.attachment.verbose", False)
