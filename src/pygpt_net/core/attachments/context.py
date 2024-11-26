#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 04:00:00                  #
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
        self.last_used_item = None
        self.last_used_content = None
        self.last_used_context = None
        self.last_files = []
        self.last_urls = []
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
                if ("type" not in file
                        or file["type"] not in ["local_file", "url"]):
                    continue
                file_id = file["uuid"]
                file_idx_path = os.path.join(meta_path, file_id)
                text_path = os.path.join(file_idx_path, file_id + ".txt")
                store_path = file["path"]
                if "real_path" in file:
                    store_path = file["real_path"]
                if filename:
                    if file["type"] == "url":
                        context += "URL: {}\n".format(file["path"]) + "\n"
                    else:
                        context += "Filename: {}\n".format(file["name"]) + "\n"

                # store used files and URLs in ctx
                if file["type"] == "url":
                    self.last_urls.append(store_path)
                else:
                    self.last_files.append(store_path)

                if os.path.exists(text_path):
                    try:
                        with open(text_path, "r", encoding="utf-8") as f:
                            context += f.read() + "\n\n"
                    except Exception as e:
                        print("Attachments: read error: {}".format(e))

        self.last_used_content = context
        self.last_used_context = context
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

        indexed = False
        # index files if not indexed by auto_index
        for i, file in enumerate(meta.additional_ctx):
            if "indexed" not in file or not file["indexed"]:
                file_id = file["uuid"]
                file_idx_path = os.path.join(meta_path, file_id)
                file_path = os.path.join(file_idx_path, file["name"])
                type = AttachmentItem.TYPE_FILE
                source = file_path
                if "type" in file:
                    if file["type"] == "url":
                        type = AttachmentItem.TYPE_URL
                        source = file["path"] # URL
                doc_ids = self.index_attachment(type, source, idx_path)
                if self.is_verbose():
                    print("Attachments: indexed. Doc IDs: {}".format(doc_ids))
                file["indexed"] = True
                file["doc_ids"] = doc_ids
                indexed = True

        if indexed:
            # update ctx in DB
            self.window.core.ctx.replace(meta)
            self.window.core.ctx.save(meta.id)

        model = None  # no model, retrieval is used
        result = self.window.core.idx.chat.query_attachment(query, idx_path, model)
        self.last_used_context = result

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

        content = self.get_context_text(ctx, filename=True)
        prompt = self.summary_prompt.format(
            query=str(query).strip(),
            content=str(content).strip(),
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
        self.last_used_context = response
        if self.is_verbose():
            print("Attachments: summary received: {}".format(response))
        return response

    def upload(
            self,
            meta: CtxMeta,
            attachment: AttachmentItem,
            prompt: str,
            auto_index: bool = False,
            real_path: str = None
    ) -> dict:
        """
        Upload attachment for context

        :param meta: CtxMeta instance
        :param attachment: AttachmentItem instance
        :param prompt: user input prompt
        :param auto_index: auto index
        :param real_path: real path
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
            if auto_index:
                print("Attachments: vector index path: {}".format(index_path))

        # store content to read
        src_file = self.store_content(attachment, file_idx_path)

        # extract text content using data loader
        content = self.read_content(attachment, src_file, prompt)
        if content:
            text_path = os.path.join(file_idx_path, file_id + ".txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(content)
            if self.is_verbose():
                print("Attachments: read text content: {}".format(content))

        tokens = 0
        if content:
            tokens = self.window.core.tokens.from_str(content)

        type = "local_file"
        size = 0
        if attachment.type == AttachmentItem.TYPE_FILE:
            size = os.path.getsize(attachment.path)
        elif attachment.type == AttachmentItem.TYPE_URL:
            size = os.path.getsize(src_file)
            type = "url"  # extra ctx type

        # index file to ctx index
        doc_ids = []
        if auto_index:
            source = src_file
            if attachment.type == AttachmentItem.TYPE_URL:
                source = attachment.path  # URL
            doc_ids = self.index_attachment(attachment.type, source, index_path)
            if self.is_verbose():
                print("Attachments: indexed. Doc IDs: {}".format(doc_ids))

        result = {
            "name": name,
            "path": attachment.path,
            "type": type,
            "uuid": str(file_id),
            "content_type": "text",
            "size": size,
            "length": len(content),
            "tokens": tokens,
            "indexed": False,
        }
        if auto_index:
            result["indexed"] = True
            result["doc_ids"] = doc_ids

        if real_path:
            result["real_path"] = real_path

        if self.is_verbose():
            print("Attachments: uploaded: {}".format(result))

        return result

    def read_content(self, attachment: AttachmentItem, path: str, prompt: str) -> str:
        """
        Read content from attachment

        :param attachment: AttachmentItem instance
        :param path: source file path
        :param prompt: user input prompt
        :return: content
        """
        content = ""
        if attachment.type == AttachmentItem.TYPE_FILE:
            loader_kwargs = {
                "prompt": prompt,
            }  # extra loader kwargs
            content = self.window.core.idx.indexing.read_text_content(
                path=path,
                loader_kwargs=loader_kwargs,
            )
        elif attachment.type == AttachmentItem.TYPE_URL:
            # directly from path
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()  # already crawled

        return content

    def store_content(self, attachment: AttachmentItem, dir: str) -> str:
        """
        Prepare content for attachment

        :param attachment: AttachmentItem instance
        :param dir: directory to save content
        :return: content
        """
        path = None
        if attachment.type == AttachmentItem.TYPE_FILE:
            # copy raw file
            name = os.path.basename(attachment.path)
            path = os.path.join(dir, name)
            if os.path.exists(path):
                os.remove(path)
            copyfile(attachment.path, path)
        elif attachment.type == AttachmentItem.TYPE_URL:
            web_type = self.window.core.idx.indexing.get_webtype(attachment.path)
            content = self.window.core.idx.indexing.read_web_content(
                url=attachment.path,
                type=web_type,  # webpage, default, TODO: add more types
                extra_args={},
            )
            # src file save
            name = "url.txt"
            path = os.path.join(dir, name)
            if os.path.exists(path):
                os.remove(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        return path

    def index_attachment(self, type: str, source: str, idx_path: str, documents: list = None) -> list:
        """
        Index attachment

        :param type: attachment type
        :param source: source file or URL
        :param idx_path: index path
        :param documents: list of documents (optional)
        :return: list of doc IDs
        """
        model = None
        doc_ids = []
        if type == AttachmentItem.TYPE_FILE:
            doc_ids = self.window.core.idx.indexing.index_attachment(source, idx_path, model, documents)
        elif type == AttachmentItem.TYPE_URL:
            doc_ids = self.window.core.idx.indexing.index_attachment_web(source, idx_path, model, documents)
        if self.is_verbose():
            print("Attachments: indexed. Doc IDs: {}".format(doc_ids))
        return doc_ids

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

    def reset(self):
        """Reset context info"""
        self.last_used_item = None
        self.last_used_content = None
        self.last_used_context = None
        self.last_files = []
        self.last_urls = []

    def get_used_files(self) -> list:
        """
        Get last used files

        :return: list of files
        """
        return self.last_files

    def get_used_urls(self) -> list:
        """
        Get last used URLs

        :return: list of URLs
        """
        return self.last_urls

    def is_verbose(self) -> bool:
        """
        Check if verbose mode is enabled

        :return: True if verbose mode is enabled
        """
        return self.window.core.config.get("ctx.attachment.verbose", False)
