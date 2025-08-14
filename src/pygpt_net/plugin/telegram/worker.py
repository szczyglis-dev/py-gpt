#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 00:00:00                  #
# ================================================== #

from __future__ import annotations

import json
import mimetypes
import os
import threading
import requests

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Telegram plugin worker: Bot API (simple HTTP) and User mode (Telethon).
    Auto-login for user mode (sends code when possible), bot mode needs only bot_token.
    """

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None
        self._tl_client = None
        self._tl_lock = threading.Lock()

    # ---------------------- Core runner ----------------------

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                        # -------- Auth (user mode) --------
                        if item["cmd"] == "tg_login_begin":
                            response = self.cmd_tg_login_begin(item)
                        elif item["cmd"] == "tg_login_complete":
                            response = self.cmd_tg_login_complete(item)
                        elif item["cmd"] == "tg_logout":
                            response = self.cmd_tg_logout(item)

                        # -------- Info --------
                        elif item["cmd"] == "tg_mode":
                            response = self.cmd_tg_mode(item)
                        elif item["cmd"] == "tg_me":
                            response = self.cmd_tg_me(item)

                        # -------- Messaging --------
                        elif item["cmd"] == "tg_send_message":
                            response = self.cmd_tg_send_message(item)
                        elif item["cmd"] == "tg_send_photo":
                            response = self.cmd_tg_send_photo(item)
                        elif item["cmd"] == "tg_send_document":
                            response = self.cmd_tg_send_document(item)

                        # -------- Chats --------
                        elif item["cmd"] == "tg_get_chat":
                            response = self.cmd_tg_get_chat(item)

                        # -------- Updates / Files (bot) --------
                        elif item["cmd"] == "tg_get_updates":
                            response = self.cmd_tg_get_updates(item)
                        elif item["cmd"] == "tg_download_file":
                            response = self.cmd_tg_download_file(item)

                        # -------- Contacts / Dialogs / History (user) --------
                        elif item["cmd"] == "tg_contacts_list":
                            response = self.cmd_tg_contacts_list(item)
                        elif item["cmd"] == "tg_dialogs_list":
                            response = self.cmd_tg_dialogs_list(item)
                        elif item["cmd"] == "tg_messages_get":
                            response = self.cmd_tg_messages_get(item)

                        if response:
                            responses.append(response)

                except Exception as e:
                    responses.append(self.make_response(item, self.throw_error(e)))

            if responses:
                self.reply_more(responses)
            if self.msg is not None:
                self.status(self.msg)
        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    # ---------------------- Common helpers ----------------------

    def _mode(self) -> str:
        m = (self.plugin.get_option_value("mode") or "bot").strip().lower()
        return "user" if m == "user" else "bot"

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _api_base(self) -> str:
        return (self.plugin.get_option_value("api_base") or "https://api.telegram.org").rstrip("/")

    def _guess_mime(self, path: str) -> str:
        mt, _ = mimetypes.guess_type(path)
        return mt or "application/octet-stream"

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)

    # ---------------------- Bot API helpers ----------------------

    def _bot_token(self) -> str:
        tok = (self.plugin.get_option_value("bot_token") or "").strip()
        if not tok:
            raise RuntimeError("Telegram bot_token is missing (set it in options or switch mode to 'user').")
        return tok

    def _bot_url(self, method: str) -> str:
        return f"{self._api_base()}/bot{self._bot_token()}/{method}"

    def _bot_file_url(self, file_path: str) -> str:
        return f"{self._api_base()}/file/bot{self._bot_token()}/{file_path}"

    def _bot_handle(self, r: requests.Response) -> dict:
        try:
            data = r.json() if r.content else {}
        except Exception:
            data = {"raw": r.text}
        if r.status_code != 200 or not data.get("ok"):
            desc = (data.get("description") or r.text)
            raise RuntimeError(f"Telegram Bot API error {r.status_code}: {desc}")
        return data["result"]

    def _bot_get(self, method: str, params: dict = None) -> dict:
        r = requests.get(self._bot_url(method), params=params or {}, timeout=self._timeout())
        return self._bot_handle(r)

    def _bot_post(self, method: str, data: dict = None, files: dict | None = None) -> dict:
        r = requests.post(self._bot_url(method), data=data or {}, files=files, timeout=self._timeout())
        return self._bot_handle(r)

    # ---------------------- Telethon (user mode) ----------------------

    def _ensure_telethon(self):
        try:
            import telethon  # noqa
        except Exception:
            raise RuntimeError("Telethon not installed. Install: pip install telethon")

    def _tl_get_client(self, need_auth: bool = False):
        """
        Returns connected Telethon client (creates on demand).
        """
        self._ensure_telethon()
        from telethon.sessions import StringSession
        from telethon.sync import TelegramClient

        api_id = self.plugin.get_option_value("api_id")
        api_hash = self.plugin.get_option_value("api_hash")
        if not (api_id and api_hash):
            raise RuntimeError("api_id/api_hash required for user mode (set options).")

        session_str = (self.plugin.get_option_value("user_session") or "").strip()
        sess = StringSession(session_str or None)

        with self._tl_lock:
            if self._tl_client is None:
                self._tl_client = TelegramClient(sess, int(api_id), api_hash)
                self._tl_client.connect()
            else:
                if not self._tl_client.is_connected():
                    self._tl_client.connect()

            authed = bool(self._tl_client.is_user_authorized())
            if not authed and need_auth:
                # Optional auto-begin: send code when phone is available
                phone = (self.plugin.get_option_value("phone_number") or "").strip()
                if phone and bool(self.plugin.get_option_value("auto_login_begin") or True):
                    try:
                        self._tl_client.send_code_request(phone)
                        self.msg = f"Telegram (user): code sent to {phone}. Now run tg_login_complete with 'code'."
                    except Exception as e:
                        raise RuntimeError(f"Failed to send login code: {e}")
                raise RuntimeError("Not authorized in user mode. Run tg_login_begin then tg_login_complete.")
            return self._tl_client

    def _tl_save_session(self):
        # Save StringSession to options
        from telethon.sessions import StringSession
        s = self._tl_client.session.save()
        self.plugin.set_option_value("user_session", s)

    def _tl_resolve(self, client, chat: str | int):
        # Resolves @username, phone, or numeric id/entity
        if isinstance(chat, int):
            return chat
        chat = (chat or "").strip()
        if not chat:
            raise RuntimeError("Param 'chat' required.")
        return client.get_entity(chat)

    # ---------------------- Commands: Auth (user) ----------------------

    def cmd_tg_login_begin(self, item: dict) -> dict:
        self._ensure_telethon()
        p = item.get("params", {}) or {}
        phone = (p.get("phone") or self.plugin.get_option_value("phone_number") or "").strip()
        if not phone:
            return self.make_response(item, "Param 'phone' required or set 'phone_number' in options.")
        client = self._tl_get_client(need_auth=False)
        try:
            client.send_code_request(phone)
            return self.make_response(item, f"Code sent to {phone}. Next call tg_login_complete with 'code'.")
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    def cmd_tg_login_complete(self, item: dict) -> dict:
        self._ensure_telethon()
        from telethon.errors import SessionPasswordNeededError
        p = item.get("params", {}) or {}
        code = (p.get("code") or "").strip()
        phone = (p.get("phone") or self.plugin.get_option_value("phone_number") or "").strip()
        password = p.get("password")  # optional 2FA

        if not (phone and code):
            return self.make_response(item, "Params 'phone' and 'code' required (phone can be saved in options).")

        client = self._tl_get_client(need_auth=False)
        try:
            client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            if not password and not (self.plugin.get_option_value("password_2fa") or ""):
                return self.make_response(item, "2FA password required. Provide 'password' or set 'password_2fa' in options.")
            client.sign_in(password=password or self.plugin.get_option_value("password_2fa"))

        # Save session for reuse
        self._tl_save_session()

        # Cache identity
        me = client.get_me()
        data = {
            "id": me.id,
            "username": getattr(me, "username", None),
            "first_name": getattr(me, "first_name", None),
            "phone": getattr(me, "phone", None),
            "is_bot": bool(getattr(me, "bot", False)),
        }
        return self.make_response(item, {"authorized": True, "me": data})

    def cmd_tg_logout(self, item: dict) -> dict:
        self._ensure_telethon()
        client = self._tl_get_client(need_auth=False)
        try:
            client.log_out()
        except Exception:
            pass
        try:
            client.disconnect()
        except Exception:
            pass
        self._tl_client = None
        self.plugin.set_option_value("user_session", "")
        return self.make_response(item, {"authorized": False})

    # ---------------------- Commands: Info ----------------------

    def cmd_tg_mode(self, item: dict) -> dict:
        return self.make_response(item, {"mode": self._mode()})

    def cmd_tg_me(self, item: dict) -> dict:
        if self._mode() == "bot":
            res = self._bot_get("getMe")
            return self.make_response(item, res)
        else:
            client = self._tl_get_client(need_auth=True)
            me = client.get_me()
            data = {
                "id": me.id,
                "username": getattr(me, "username", None),
                "first_name": getattr(me, "first_name", None),
                "last_name": getattr(me, "last_name", None),
                "phone": getattr(me, "phone", None),
                "is_bot": bool(getattr(me, "bot", False)),
            }
            return self.make_response(item, data)

    # ---------------------- Commands: Messaging ----------------------

    def _default_send_flags(self, p: dict) -> dict:
        flags = {}
        if p.get("parse_mode") or self.plugin.get_option_value("default_parse_mode"):
            flags["parse_mode"] = p.get("parse_mode") or self.plugin.get_option_value("default_parse_mode")
        if p.get("disable_web_page_preview") is not None:
            flags["disable_web_page_preview"] = bool(p.get("disable_web_page_preview"))
        else:
            if self.plugin.get_option_value("default_disable_preview"):
                flags["disable_web_page_preview"] = True
        if p.get("disable_notification") is not None:
            flags["disable_notification"] = bool(p.get("disable_notification"))
        else:
            if self.plugin.get_option_value("default_disable_notification"):
                flags["disable_notification"] = True
        if p.get("protect_content") is not None:
            flags["protect_content"] = bool(p.get("protect_content"))
        else:
            if self.plugin.get_option_value("default_protect_content"):
                flags["protect_content"] = True
        if p.get("reply_to_message_id"):
            flags["reply_to_message_id"] = int(p.get("reply_to_message_id"))
        return flags

    def cmd_tg_send_message(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        chat = p.get("chat")
        text = p.get("text", "")
        if not (chat and text):
            return self.make_response(item, "Params 'chat' and 'text' required.")

        if self._mode() == "bot":
            data = {"chat_id": chat, "text": text}
            data.update(self._default_send_flags(p))
            res = self._bot_post("sendMessage", data=data)
            return self.make_response(item, res)
        else:
            client = self._tl_get_client(need_auth=True)
            entity = self._tl_resolve(client, chat)
            parse_mode = (p.get("parse_mode") or self.plugin.get_option_value("default_parse_mode") or None)
            # Telethon accepts "html" or "markdown"
            if parse_mode and parse_mode.upper() == "MARKDOWNV2":
                parse_mode = "markdown"
            msg = client.send_message(entity, text, parse_mode=(parse_mode.lower() if parse_mode else None), link_preview=not bool(p.get("disable_web_page_preview") or self.plugin.get_option_value("default_disable_preview")))
            return self.make_response(item, {"id": msg.id, "date": msg.date.isoformat()})

    def cmd_tg_send_photo(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        chat = p.get("chat")
        photo = p.get("photo") or p.get("path")
        caption = p.get("caption", "")
        if not (chat and photo):
            return self.make_response(item, "Params 'chat' and 'photo' (or 'path') required.")

        if self._mode() == "bot":
            data = {"chat_id": chat, "caption": caption}
            data.update(self._default_send_flags(p))
            files = None
            # Accept local path, URL or file_id
            if os.path.exists(self.prepare_path(photo)):
                local = self.prepare_path(photo)
                files = {"photo": (os.path.basename(local), open(local, "rb"), self._guess_mime(local))}
            else:
                data["photo"] = photo
            res = self._bot_post("sendPhoto", data=data, files=files)
            return self.make_response(item, res)
        else:
            client = self._tl_get_client(need_auth=True)
            entity = self._tl_resolve(client, chat)
            local = self.prepare_path(photo) if not photo.lower().startswith("http") else photo
            msg = client.send_file(entity, local, caption=caption)
            return self.make_response(item, {"id": msg.id, "date": msg.date.isoformat()})

    def cmd_tg_send_document(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        chat = p.get("chat")
        doc = p.get("document") or p.get("path")
        caption = p.get("caption", "")
        if not (chat and doc):
            return self.make_response(item, "Params 'chat' and 'document' (or 'path') required.")

        if self._mode() == "bot":
            data = {"chat_id": chat, "caption": caption}
            data.update(self._default_send_flags(p))
            files = None
            if os.path.exists(self.prepare_path(doc)):
                local = self.prepare_path(doc)
                files = {"document": (os.path.basename(local), open(local, "rb"), self._guess_mime(local))}
            else:
                data["document"] = doc
            res = self._bot_post("sendDocument", data=data, files=files)
            return self.make_response(item, res)
        else:
            client = self._tl_get_client(need_auth=True)
            entity = self._tl_resolve(client, chat)
            local = self.prepare_path(doc) if not str(doc).lower().startswith("http") else doc
            msg = client.send_file(entity, local, caption=caption, force_document=True)
            return self.make_response(item, {"id": msg.id, "date": msg.date.isoformat()})

    # ---------------------- Commands: Chats ----------------------

    def cmd_tg_get_chat(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        chat = p.get("chat")
        if not chat:
            return self.make_response(item, "Param 'chat' required (id or @username).")

        if self._mode() == "bot":
            res = self._bot_get("getChat", params={"chat_id": chat})
            return self.make_response(item, res)
        else:
            client = self._tl_get_client(need_auth=True)
            ent = self._tl_resolve(client, chat)
            data = {
                "id": getattr(ent, "id", None),
                "title": getattr(ent, "title", None) or f"{getattr(ent, 'first_name', '')} {getattr(ent, 'last_name', '')}".strip(),
                "username": getattr(ent, "username", None),
                "is_channel": getattr(ent, "__class__", type("x",(object,),{})).__name__.lower().find("channel") >= 0,
            }
            return self.make_response(item, data)

    # ---------------------- Commands: Updates / Files (bot) ----------------------

    def cmd_tg_get_updates(self, item: dict) -> dict:
        if self._mode() != "bot":
            return self.make_response(item, "tg_get_updates is available in bot mode only.")
        p = item.get("params", {}) or {}
        offset = p.get("offset")
        if offset is None:
            # continue from last stored
            last = self.plugin.get_option_value("last_update_id")
            if last:
                try:
                    offset = int(last) + 1
                except Exception:
                    offset = None
        params = {
            "timeout": int(p.get("timeout") or 0),
        }
        if offset is not None:
            params["offset"] = int(offset)
        if p.get("allowed_updates"):
            params["allowed_updates"] = json.dumps(p.get("allowed_updates"))
        res = self._bot_get("getUpdates", params=params)
        if res:
            max_id = max(u.get("update_id", 0) for u in res)
            self.plugin.set_option_value("last_update_id", str(max_id))
        return self.make_response(item, res or [])

    def cmd_tg_download_file(self, item: dict) -> dict:
        if self._mode() != "bot":
            return self.make_response(item, "tg_download_file is available in bot mode only.")
        p = item.get("params", {}) or {}
        file_id = p.get("file_id")
        save_as = p.get("save_as")  # relative to data dir if not absolute
        if not file_id:
            return self.make_response(item, "Param 'file_id' required.")
        info = self._bot_post("getFile", data={"file_id": file_id})
        file_path = info.get("file_path")
        if not file_path:
            return self.make_response(item, "No file_path returned by getFile.")
        url = self._bot_file_url(file_path)
        r = requests.get(url, timeout=self._timeout())
        if r.status_code != 200:
            return self.make_response(item, f"Download error: HTTP {r.status_code}")
        local = self.prepare_path(save_as or os.path.basename(file_path))
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as fh:
            fh.write(r.content)
        return self.make_response(item, {"saved_path": local, "size": len(r.content)})

    # ---------------------- Commands: Contacts / Dialogs / Messages (user) ----------------------

    def cmd_tg_contacts_list(self, item: dict) -> dict:
        if self._mode() != "user":
            return self.make_response(item, "tg_contacts_list is available in user mode only.")
        client = self._tl_get_client(need_auth=True)
        contacts = client.get_contacts()
        out = []
        for u in contacts:
            out.append({
                "id": u.id,
                "first_name": getattr(u, "first_name", None),
                "last_name": getattr(u, "last_name", None),
                "username": getattr(u, "username", None),
                "phone": getattr(u, "phone", None),
            })
        return self.make_response(item, {"count": len(out), "contacts": out})

    def cmd_tg_dialogs_list(self, item: dict) -> dict:
        if self._mode() != "user":
            return self.make_response(item, "tg_dialogs_list is available in user mode only.")
        p = item.get("params", {}) or {}
        limit = int(p.get("limit") or 20)
        client = self._tl_get_client(need_auth=True)
        dialogs = client.get_dialogs(limit=limit)
        out = []
        for d in dialogs:
            ent = d.entity
            title = getattr(ent, "title", None) or f"{getattr(ent, 'first_name', '')} {getattr(ent, 'last_name', '')}".strip()
            out.append({
                "id": getattr(ent, "id", None),
                "title": title,
                "username": getattr(ent, "username", None),
                "unread_count": getattr(d, "unread_count", 0),
                "is_channel": "Channel" in ent.__class__.__name__,
            })
        return self.make_response(item, {"count": len(out), "dialogs": out})

    def cmd_tg_messages_get(self, item: dict) -> dict:
        if self._mode() != "user":
            return self.make_response(item, "tg_messages_get is available in user mode only.")
        p = item.get("params", {}) or {}
        chat = p.get("chat")
        limit = int(p.get("limit") or 30)
        if not chat:
            return self.make_response(item, "Param 'chat' required.")
        client = self._tl_get_client(need_auth=True)
        ent = self._tl_resolve(client, chat)

        kwargs = {}
        if p.get("offset_id"):
            kwargs["offset_id"] = int(p["offset_id"])
        if p.get("min_id"):
            kwargs["min_id"] = int(p["min_id"])
        if p.get("max_id"):
            kwargs["max_id"] = int(p["max_id"])
        if p.get("search"):
            kwargs["search"] = p.get("search")

        msgs = client.get_messages(ent, limit=limit, **kwargs)
        out = []
        for m in msgs:
            out.append({
                "id": m.id,
                "date": m.date.isoformat() if m.date else None,
                "text": m.message or "",
                "sender_id": getattr(m, "sender_id", None),
                "reply_to": getattr(m, "reply_to_msg_id", None),
                "media": bool(m.media),
            })
        return self.make_response(item, {"count": len(out), "messages": out})