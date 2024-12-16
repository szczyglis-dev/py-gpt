#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

import copy
import os
import shutil
import uuid

from shutil import copyfile
from typing import Optional, List, Dict, Any, Tuple

from llama_index.core import Document

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

        `{query}`

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
        self.rag_prompt = """
        Prepare a question for the RAG engine (vector database) asking for additional context that can help obtain 
        extra information necessary to answer the user's question. The query should be brief and to the point, 
        so as to be processed as effectively as possible by the RAG engine. Below is the entire conversation 
        of the user with the AI assistant, and at the end the current user's question, for which you need to 
        prepare DIRECT query for the RAG engine for additional context, taking into account the content of the entire 
        discussion and its context. In your response, return only the DIRECT query for additional context, 
        do not return anything else besides it. The response should not contain any phrases other than the query itself:
        
        # Good RAG query example:
        
        `What is the capital of France?`
        
        # Bad RAG query example:
        
        `Can you tell me the capital of France?`

        # Full conversation:
        
        `{history}`
        
        # User question:
        
        `{query}`
        """

    def get_context(
            self,
            mode: str,
            ctx: CtxItem,
            history: List[CtxItem]
    ) -> str:
        """
        Get context for mode

        :param mode: Context mode
        :param ctx: CtxItem instance
        :param history: history
        :return: context
        """
        content = ""
        if mode == self.window.controller.chat.attachment.MODE_FULL_CONTEXT:
            content = self.get_context_text(ctx, filename=True)
        elif mode == self.window.controller.chat.attachment.MODE_QUERY_CONTEXT:
            content = self.query_context(ctx, history)
        elif mode == self.window.controller.chat.attachment.MODE_QUERY_CONTEXT_SUMMARY:
            content = self.summary_context(ctx, history)
        return content

    def get_context_text(
            self,
            ctx: CtxItem,
            filename: bool = False
    ) -> str:
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
            for file in meta.get_additional_ctx():
                if ("type" not in file
                        or file["type"] not in ["local_file", "url"]):
                    continue
                if not "uuid" in file:
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
                    if store_path not in self.last_urls:
                        self.last_urls.append(store_path)
                else:
                    if store_path not in self.last_files:
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

    def query_context(
            self,
            ctx: CtxItem,
            history: List[CtxItem]
    ) -> str:
        """
        Query the index for context

        :param ctx: CtxItem instance
        :param history: history
        :return: query result
        """
        meta = ctx.meta
        meta_path = self.get_dir(meta)
        query = str(ctx.input)
        if not os.path.exists(meta_path) or not os.path.isdir(meta_path):
            return ""
        idx_path = os.path.join(self.get_dir(meta), self.dir_index)

        indexed = False
        # index files if not indexed by auto_index
        for i, file in enumerate(meta.get_additional_ctx()):
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
                file["indexed"] = True
                file["doc_ids"] = doc_ids
                indexed = True

        if indexed:
            # update ctx in DB
            self.window.core.ctx.replace(meta)
            self.window.core.ctx.save(meta.id)

        history_data = self.prepare_context_history(history)
        model, model_item = self.get_selected_model("query")

        verbose = False
        if self.is_verbose():
            verbose = True
            print("Attachments: using query model: {}".format(model))

        result = self.window.core.idx.chat.query_attachment(
            query=query,
            path=idx_path,
            model=model_item,
            history=history_data,
            verbose=verbose,
        )
        self.last_used_context = result

        if self.is_verbose():
            print("Attachments: query result: {}".format(result))

        return result

    def summary_context(
            self,
            ctx: CtxItem,
            history: List[CtxItem]
    ) -> str:
        """
        Get summary of the context

        :param ctx: CtxItem instance
        :param history: history
        :return: query result
        """
        model, model_item = self.get_selected_model("summary")
        if model_item is None:
            raise Exception("Attachments: summary model not found: {}".format(model))

        if self.is_verbose():
            print("Attachments: using summary model: {}".format(model))

        query = str(ctx.input)
        content = self.get_context_text(ctx, filename=True)
        prompt = self.summary_prompt.format(
            query=str(query).strip(),
            content=str(content).strip(),
        )
        if self.is_verbose():
            print("Attachments: summary prompt: {}".format(prompt))

        history_data = self.prepare_context_history(history)
        ctx = CtxItem()
        bridge_context = BridgeContext(
            ctx=ctx,
            prompt=prompt,
            stream=False,
            model=model_item,
            history=history_data,
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

    def prepare_context_history(
            self,
            history: List[CtxItem]
    ) -> List[CtxItem]:
        """
        Prepare context history

        :param history: history
        :return: history data
        """
        use_history = self.window.core.config.get("ctx.attachment.rag.history", True)
        history_data = []
        if use_history:
            if self.is_verbose():
                print("Attachments: using history for query prepare...")

            # use only last X items from history
            num_items = self.window.core.config.get("ctx.attachment.rag.history.max_items", 3)
            history_data = []
            for item in history:
                history_data.append(item)

            # 0 = unlimited
            if num_items > 0:
                if self.is_verbose():
                    print("Attachments: using last {} items from history...".format(num_items))
                if len(history_data) < num_items:
                    num_items = len(history_data)
                history_data = history_data[-num_items:]

        return history_data

    def upload(
            self,
            meta: CtxMeta,
            attachment: AttachmentItem,
            prompt: str,
            auto_index: bool = False,
            real_path: Optional[str] = None
    ) -> Dict[str, Any]:
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
            if meta.group:
                print("Uploading for meta group ID: {}".format(meta.group.id))
            else:
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

        documents = None
        
        # store content to read, and get docs if type == web
        src_file, docs = self.store_content(attachment, file_idx_path)
        if attachment.type == AttachmentItem.TYPE_URL:
            documents = docs

        # extract text content using data loader, and get docs if type == file
        content, docs = self.read_content(attachment, src_file, prompt)
        if attachment.type == AttachmentItem.TYPE_FILE:
            documents = docs

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
            doc_ids = self.index_attachment(attachment.type, source, index_path, documents=documents)

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

    def read_content(
            self,
            attachment: AttachmentItem,
            path: str,
            prompt: str
    ) -> Tuple[str, List[Document]]:
        """
        Read content from attachment

        :param attachment: AttachmentItem instance
        :param path: source file path
        :param prompt: user input prompt
        :return: text content, list of documents
        """
        content = ""
        docs = []
        if attachment.type == AttachmentItem.TYPE_FILE:
            loader_kwargs = {
                "prompt": prompt,
            }  # extra loader kwargs
            content, docs = self.window.core.idx.indexing.read_text_content(
                path=path,
                loader_kwargs=loader_kwargs,
            )
        elif attachment.type == AttachmentItem.TYPE_URL:
            # directly from before stored path
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()  # data is already crawled in `store_content`
        return content, docs

    def store_content(
            self,
            attachment: AttachmentItem,
            dir: str
    ) -> Tuple[str, List[Document]]:
        """
        Prepare content for attachment

        :param attachment: AttachmentItem instance
        :param dir: directory to save content
        :return: path, list of documents
        """
        path = None
        docs = []
        if attachment.type == AttachmentItem.TYPE_FILE:
            # copy raw file only
            name = os.path.basename(attachment.path)
            path = os.path.join(dir, name)
            if os.path.exists(path):
                os.remove(path)
            copyfile(attachment.path, path)
        elif attachment.type == AttachmentItem.TYPE_URL:
            loader = attachment.extra.get("loader")
            input_params = attachment.extra.get("input_params")
            input_config = attachment.extra.get("input_config")
            self.window.core.idx.indexing.update_loader_args(loader, input_config)  # update config
            content, docs = self.window.core.idx.indexing.read_web_content(
                url="",
                type=loader,
                extra_args=input_params,
            )
            # src file save
            name = "url.txt"
            path = os.path.join(dir, name)
            if os.path.exists(path):
                os.remove(path)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        return path, docs

    def index_attachment(
            self,
            type: str,
            source: str,
            idx_path: str,
            documents: Optional[List[Document]] = None
    ) -> list:
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

    def get_all(self, meta: CtxMeta) -> list:
        """
        Get all attachments for meta

        :param meta: CtxMeta instance
        :return: list of attachments
        """
        return meta.get_additional_ctx()

    def get_dir(self, meta: CtxMeta) -> str:
        """
        Get directory for meta

        :param meta: CtxMeta instance
        :return: directory path
        """
        meta_uuid = str(meta.uuid)
        if meta.group:
            meta_uuid = str(meta.group.uuid)
        return os.path.join(self.window.core.config.get_user_dir("ctx_idx"), meta_uuid)

    def get_selected_model(self, mode: str = "summary"):
        """
        Get selected model for attachments

        :return: model name, model item
        """
        model_item = None
        model = None
        if mode == "summary":
            model = self.window.core.config.get("ctx.attachment.summary.model", "gpt-4o-mini")
        elif mode == "query":
            model = self.window.core.config.get("ctx.attachment.query.model", "gpt-4o-mini")
        if model:
            model_item = self.window.core.models.get(model)
        return model, model_item

    def duplicate(
            self,
            from_meta_id: int,
            to_meta_id: int
    ) -> bool:
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
        return len(meta.get_additional_ctx())

    def delete(
            self,
            meta: CtxMeta,
            item: Dict[str, Any],
            delete_files: bool = False
    ):
        """
        Delete attachment

        :param meta: CtxMeta instance
        :param item: Attachment item dict
        :param delete_files: delete files
        """
        meta.remove_additional_ctx(item)
        self.window.core.ctx.save(meta.id)
        if delete_files:
            self.delete_local(meta, item)
        if len(meta.get_additional_ctx()) == 0:
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

    def reset_by_meta(
            self,
            meta: CtxMeta,
            delete_files: bool = False
    ):
        """
        Delete all attachments for meta

        :param meta: CtxMeta instance
        :param delete_files: delete files
        """
        meta.reset_additional_ctx()
        self.window.core.ctx.save(meta.id)
        if delete_files:
            self.delete_index(meta)

    def reset_by_meta_id(
            self,
            meta_id: int,
            delete_files: bool = False
    ):
        """
        Delete all attachments for meta by id

        :param meta_id: Meta id
        :param delete_files: delete files
        """
        meta = self.window.core.ctx.get_meta_by_id(meta_id)
        if meta is not None:
            self.reset_by_meta(meta, delete_files)

    def clear(
            self,
            meta: CtxMeta,
            delete_files: bool = False
    ):
        """
        Clear all attachments by ctx meta

        :param meta: CtxMeta instance
        :param delete_files: delete files
        """
        meta.reset_additional_ctx()
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

    def delete_local(
            self,
            meta: CtxMeta,
            item: Dict[str, Any]
    ):
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

    def get_used_files(self) -> List[str]:
        """
        Get last used files

        :return: list of files
        """
        return self.last_files

    def get_used_urls(self) -> List[str]:
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
