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

import base64
import datetime as dt
import io
import json
import os
import re
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals

# Google libs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Optional libs
try:
    from youtube_transcript_api import YouTubeTranscriptApi  # unofficial fallback
except Exception:
    YouTubeTranscriptApi = None

try:
    import gkeepapi  # unofficial Keep fallback
except Exception:
    gkeepapi = None


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Google plugin worker: Gmail, Calendar, Keep, Drive, YouTube, Contacts.
    """
    # Request a broad-but-reasonable union of scopes once, to avoid re-prompt churn
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    CAL_SCOPES = ["https://www.googleapis.com/auth/calendar"]
    DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
    PEOPLE_SCOPES = ["https://www.googleapis.com/auth/contacts"]
    YT_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
    KEEP_SCOPES = [
        "https://www.googleapis.com/auth/keep",
        "https://www.googleapis.com/auth/keep.readonly",
    ]

    ALL_SCOPES = sorted(
        set(GMAIL_SCOPES + CAL_SCOPES + DRIVE_SCOPES + PEOPLE_SCOPES + YT_SCOPES)
    )
    ALL_SCOPES_WITH_KEEP = sorted(
        set(GMAIL_SCOPES + CAL_SCOPES + DRIVE_SCOPES + PEOPLE_SCOPES + YT_SCOPES + KEEP_SCOPES)
    )

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    # -------------- Core runner --------------

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

                        # Gmail
                        if item["cmd"] == "gmail_list_recent":
                            response = self.cmd_gmail_list_recent(item)
                        elif item["cmd"] == "gmail_list_all":
                            response = self.cmd_gmail_list_all(item)
                        elif item["cmd"] == "gmail_search":
                            response = self.cmd_gmail_search(item)
                        elif item["cmd"] == "gmail_get_by_id":
                            response = self.cmd_gmail_get_by_id(item)
                        elif item["cmd"] == "gmail_send":
                            response = self.cmd_gmail_send(item)

                        # Calendar
                        elif item["cmd"] == "calendar_events_recent":
                            response = self.cmd_calendar_events_recent(item)
                        elif item["cmd"] == "calendar_events_today":
                            response = self.cmd_calendar_events_today(item)
                        elif item["cmd"] == "calendar_events_tomorrow":
                            response = self.cmd_calendar_events_tomorrow(item)
                        elif item["cmd"] == "calendar_events_all":
                            response = self.cmd_calendar_events_all(item)
                        elif item["cmd"] == "calendar_events_by_date":
                            response = self.cmd_calendar_events_by_date(item)
                        elif item["cmd"] == "calendar_add_event":
                            response = self.cmd_calendar_add_event(item)
                        elif item["cmd"] == "calendar_delete_event":
                            response = self.cmd_calendar_delete_event(item)

                        # Keep
                        elif item["cmd"] == "keep_list_notes":
                            response = self.cmd_keep_list_notes(item)
                        elif item["cmd"] == "keep_add_note":
                            response = self.cmd_keep_add_note(item)

                        # Drive
                        elif item["cmd"] == "drive_list_files":
                            response = self.cmd_drive_list_files(item)
                        elif item["cmd"] == "drive_find_by_path":
                            response = self.cmd_drive_find_by_path(item)
                        elif item["cmd"] == "drive_download_file":
                            response = self.cmd_drive_download_file(item)
                        elif item["cmd"] == "drive_upload_file":
                            response = self.cmd_drive_upload_file(item)

                        # YouTube
                        elif item["cmd"] == "youtube_video_info":
                            response = self.cmd_youtube_video_info(item)
                        elif item["cmd"] == "youtube_transcript":
                            response = self.cmd_youtube_transcript(item)

                        # Contacts
                        elif item["cmd"] == "contacts_list":
                            response = self.cmd_contacts_list(item)
                        elif item["cmd"] == "contacts_add":
                            response = self.cmd_contacts_add(item)

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

    # -------------- Auth / service helpers --------------

    def _get_scopes(self) -> List[str]:
        """
        Determine scopes for the command based on its type.

        If unofficial Keep is allowed, return all scopes including Keep.

        :return: List of scopes
        """
        scopes_str = self.plugin.get_option_value("oauth_scopes") or ""
        if scopes_str:
            scopes = [s.strip() for s in scopes_str.split(" ") if s.strip()]
            if not scopes:
                raise RuntimeError("No valid scopes provided in 'oauth_scopes'")
            return sorted(scopes)
        return []

    def _get_credentials(self, scopes: List[str]) -> Credentials:
        """
        Resolve credentials from plugin config. Supports:
        - OAuth client secrets JSON (installed/web) + stored refresh token (oauth_token)
        - Service account JSON (for Workspace scenarios like Keep DWD)

        :param scopes: List of scopes to request
        :return: Credentials object
        """
        creds_json_text = self.plugin.get_option_value("credentials") or ""
        if not creds_json_text:
            raise RuntimeError("Missing credentials JSON in plugin option 'credentials'")
        creds_info = json.loads(creds_json_text)

        # Token store in plugin option to avoid filesystem coupling
        token_text = self.plugin.get_option_value("oauth_token") or None
        creds: Optional[Credentials] = None

        # If service account
        if isinstance(creds_info, dict) and creds_info.get("type") == "service_account":
            sa_scopes = list(set(scopes))
            creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=sa_scopes)

            # Optional: impersonation for Workspace (domain-wide delegation)
            subject = self.plugin.get_option_value("impersonate_user") or None
            if subject:
                creds = creds.with_subject(subject)
            return creds

        # OAuth installed/web
        # Try to reuse saved token first
        if token_text:
            try:
                creds = Credentials.from_authorized_user_info(json.loads(token_text), scopes=self._get_scopes())
            except Exception:
                creds = None

        # Refresh if needed
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # If no creds or missing refresh, run flow
        if not creds or not creds.valid:
            # Always request the union of scopes to minimize re-prompt later
            flow = InstalledAppFlow.from_client_config(creds_info, scopes=self._get_scopes())
            use_local_server = bool(self.plugin.get_option_value("oauth_local_server") or True)
            if use_local_server:
                creds = flow.run_local_server(port=int(self.plugin.get_option_value("oauth_local_port") or 0))
            else:
                creds = flow.run_console()

            # Persist token back into plugin options
            self.plugin.set_option_value("oauth_token", creds.to_json())

        return creds

    def _service(self, api: str, version: str, scopes: List[str] | None = None, api_key: Optional[str] = None):
        """
        Build google api service. If api_key is provided, use key-only (no OAuth).

        :param api: API name (e.g. 'gmail', 'calendar')
        :param version: API version (e.g. 'v1', 'v3')
        :param scopes: List of scopes to request (if OAuth)
        :param api_key: Optional API key for key-only access (no OAuth)
        :return: Google API service object
        """
        if api_key:
            return build(api, version, developerKey=api_key, cache_discovery=False)

        creds = self._get_credentials(scopes or self._get_scopes())
        return build(api, version, credentials=creds, cache_discovery=False)

    # -------------- Gmail --------------

    def _gmail_message_summary(self, svc, msg_id: str) -> Dict[str, Any]:
        msg = svc.users().messages().get(userId="me", id=msg_id, format="metadata",
                                         metadataHeaders=["From", "To", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "snippet": msg.get("snippet"),
            "internalDate": msg.get("internalDate"),
            "headers": headers,
        }

    def cmd_gmail_list_recent(self, item: dict) -> dict:
        params = item.get("params", {})
        n = int(params.get("n", 10))
        label_ids = params.get("labelIds") or ["INBOX"]
        q = params.get("q")  # optional search string

        svc = self._service("gmail", "v1", scopes=self.GMAIL_SCOPES)
        res = svc.users().messages().list(userId="me", maxResults=n, labelIds=label_ids, q=q).execute()
        ids = [m["id"] for m in res.get("messages", [])]
        out = [self._gmail_message_summary(svc, mid) for mid in ids]
        return self.make_response(item, out)

    def cmd_gmail_list_all(self, item: dict) -> dict:
        params = item.get("params", {})
        q = params.get("q")
        label_ids = params.get("labelIds") or None
        limit = params.get("limit")  # to protect from huge mailboxes
        limit = int(limit) if limit else None

        svc = self._service("gmail", "v1", scopes=self.GMAIL_SCOPES)
        all_ids: List[str] = []
        page_token = None
        while True:
            res = svc.users().messages().list(userId="me", pageToken=page_token, q=q, labelIds=label_ids,
                                              maxResults=500).execute()
            batch = [m["id"] for m in res.get("messages", [])]
            all_ids.extend(batch)
            if limit and len(all_ids) >= limit:
                all_ids = all_ids[:limit]
                break
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        svc_batch = [self._gmail_message_summary(svc, mid) for mid in all_ids]
        return self.make_response(item, svc_batch)

    def cmd_gmail_search(self, item: dict) -> dict:
        params = item.get("params", {})
        q = params.get("q")
        if not q:
            return self.make_response(item, "Query 'q' required")
        svc = self._service("gmail", "v1", scopes=self.GMAIL_SCOPES)
        res = svc.users().messages().list(userId="me", q=q, maxResults=int(params.get("max", 50))).execute()
        ids = [m["id"] for m in res.get("messages", [])]
        out = [self._gmail_message_summary(svc, mid) for mid in ids]
        return self.make_response(item, out)

    def _gmail_decode_parts(self, part, collected):
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            try:
                text = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
            except Exception:
                text = ""
            if mime_type == "text/plain":
                collected["text"] = (collected.get("text", "") + text).strip()
            elif mime_type == "text/html":
                collected["html"] = (collected.get("html", "") + text).strip()

        for p in part.get("parts", []) or []:
            self._gmail_decode_parts(p, collected)

    def cmd_gmail_get_by_id(self, item: dict) -> dict:
        params = item.get("params", {})
        mid = params.get("id")
        if not mid:
            return self.make_response(item, "Message 'id' required")
        svc = self._service("gmail", "v1", scopes=self.GMAIL_SCOPES)
        msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        content = {"text": "", "html": ""}
        self._gmail_decode_parts(msg.get("payload", {}), content)
        out = {
            "id": msg.get("id"),
            "threadId": msg.get("threadId"),
            "labelIds": msg.get("labelIds"),
            "snippet": msg.get("snippet"),
            "headers": headers,
            "content": content,
        }
        return self.make_response(item, out)

    def cmd_gmail_send(self, item: dict) -> dict:
        p = item.get("params", {})
        to = p.get("to")
        subject = p.get("subject", "")
        body = p.get("body", "")
        html = bool(p.get("html", False))
        cc = p.get("cc")
        bcc = p.get("bcc")
        attachments = p.get("attachments") or []  # list of local paths

        if not to:
            return self.make_response(item, "Recipient 'to' required")

        svc = self._service("gmail", "v1", scopes=self.GMAIL_SCOPES)

        if attachments:
            msg = MIMEMultipart()
            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            for apath in attachments:
                apath = self.prepare_path(apath)
                if not os.path.exists(apath):
                    continue
                with open(apath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(apath)}"')
                msg.attach(part)
        else:
            msg = EmailMessage()
            subtype = "html" if html else "plain"
            msg.set_content(body, subtype=subtype, charset="utf-8")

        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return self.make_response(item, {"id": sent.get("id"), "labelIds": sent.get("labelIds")})

    # -------------- Calendar --------------

    def _utc_iso(self, dt_obj: dt.datetime) -> str:
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
        return dt_obj.astimezone(dt.timezone.utc).isoformat()

    def _day_bounds_utc(self, days_from_today: int = 0) -> Tuple[str, str]:
        now = dt.datetime.utcnow()
        day = now.date() + dt.timedelta(days=days_from_today)
        start = dt.datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=dt.timezone.utc)
        end = start + dt.timedelta(days=1)
        return start.isoformat(), end.isoformat()

    def _calendar_list(self, svc, time_min: Optional[str], time_max: Optional[str], limit: int) -> List[Dict[str, Any]]:
        res = svc.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=limit,
        ).execute()
        return res.get("items", [])

    def cmd_calendar_events_recent(self, item: dict) -> dict:
        p = item.get("params", {})
        limit = int(p.get("limit", 10))
        now_iso = dt.datetime.utcnow().isoformat() + "Z"
        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        items = self._calendar_list(svc, now_iso, None, limit)
        return self.make_response(item, items)

    def cmd_calendar_events_today(self, item: dict) -> dict:
        start, end = self._day_bounds_utc(0)
        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        items = self._calendar_list(svc, start, end, 250)
        return self.make_response(item, items)

    def cmd_calendar_events_tomorrow(self, item: dict) -> dict:
        start, end = self._day_bounds_utc(1)
        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        items = self._calendar_list(svc, start, end, 250)
        return self.make_response(item, items)

    def cmd_calendar_events_all(self, item: dict) -> dict:
        p = item.get("params", {})
        # Sensible default: 1y back and 1y forward
        now = dt.datetime.utcnow()
        time_min = p.get("timeMin") or (now - dt.timedelta(days=365)).isoformat() + "Z"
        time_max = p.get("timeMax") or (now + dt.timedelta(days=365)).isoformat() + "Z"
        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        items = self._calendar_list(svc, time_min, time_max, 2500)
        return self.make_response(item, items)

    def cmd_calendar_events_by_date(self, item: dict) -> dict:
        p = item.get("params", {})
        date_str = p.get("date")  # YYYY-MM-DD or ISO range start|end
        if not date_str:
            return self.make_response(item, "Param 'date' (YYYY-MM-DD) or 'start'/'end' required")
        if "|" in date_str:
            start, end = date_str.split("|", 1)
        else:
            y, m, d = map(int, date_str.split("-"))
            start_dt = dt.datetime(y, m, d, 0, 0, tzinfo=dt.timezone.utc)
            end_dt = start_dt + dt.timedelta(days=1)
            start, end = start_dt.isoformat(), end_dt.isoformat()

        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        items = self._calendar_list(svc, start, end, 2500)
        return self.make_response(item, items)

    def cmd_calendar_add_event(self, item: dict) -> dict:
        p = item.get("params", {})
        summary = p.get("summary")
        start = p.get("start")  # RFC3339 or YYYY-MM-DDTHH:MM
        end = p.get("end")
        tz = p.get("timezone") or "UTC"
        description = p.get("description")
        location = p.get("location")
        attendees = p.get("attendees") or []  # list of emails

        if not (summary and start and end):
            return self.make_response(item, "Params 'summary', 'start', 'end' are required")

        def normalize(x: str) -> str:
            if "T" in x:
                if x.endswith("Z") or "+" in x:
                    return x
                return f"{x}:00"
            return f"{x}T00:00:00"

        body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": normalize(start), "timeZone": tz},
            "end": {"dateTime": normalize(end), "timeZone": tz},
        }
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]

        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        created = svc.events().insert(calendarId="primary", body=body).execute()
        return self.make_response(item, created)

    def cmd_calendar_delete_event(self, item: dict) -> dict:
        p = item.get("params", {})
        eid = p.get("event_id")
        if not eid:
            return self.make_response(item, "Param 'event_id' required")
        svc = self._service("calendar", "v3", scopes=self.CAL_SCOPES)
        svc.events().delete(calendarId="primary", eventId=eid).execute()
        return self.make_response(item, "OK")

    # -------------- Keep --------------

    def _keep_service(self):
        # Official Keep API (Workspace-focused)
        return self._service("keep", "v1", scopes=self.KEEP_SCOPES)

    def cmd_keep_list_notes(self, item: dict) -> dict:
        mode = (self.plugin.get_option_value("keep_mode") or "auto").lower()
        if mode in ("official", "auto"):
            try:
                svc = self._keep_service()
                # Official list
                res = svc.notes().list(pageSize=int(item.get("params", {}).get("limit", 50))).execute()
                return self.make_response(item, res.get("notes", []))
            except HttpError as e:
                if mode == "official":
                    return self.make_response(item, self.throw_error(e))
                # fallthrough to unofficial if allowed

        if (self.plugin.get_option_value("allow_unofficial_keep") or False) and gkeepapi:
            # Unofficial fallback (not endorsed by Google)
            email = self.plugin.get_option_value("keep_username")
            token = self.plugin.get_option_value("keep_master_token")
            if not (email and token):
                return self.make_response(item, "Missing keep_username/keep_master_token for unofficial mode")
            keep = gkeepapi.Keep()
            keep.authenticate(email, token)
            keep.sync()
            notes = [{"id": n.id, "title": n.title, "text": getattr(n, "text", "")} for n in keep.all()]
            return self.make_response(item, notes)
        return self.make_response(item, "Keep unavailable (official failed and unofficial disabled)")

    def cmd_keep_add_note(self, item: dict) -> dict:
        p = item.get("params", {})
        title = p.get("title", "")
        text = p.get("text", "")
        mode = (self.plugin.get_option_value("keep_mode") or "auto").lower()

        if mode in ("official", "auto"):
            try:
                svc = self._keep_service()
                body = {"title": title, "body": {"text": {"text": text}}}
                created = svc.notes().create(body=body).execute()
                return self.make_response(item, created)
            except HttpError as e:
                if mode == "official":
                    return self.make_response(item, self.throw_error(e))

        if (self.plugin.get_option_value("allow_unofficial_keep") or False) and gkeepapi:
            email = self.plugin.get_option_value("keep_username")
            token = self.plugin.get_option_value("keep_master_token")
            if not (email and token):
                return self.make_response(item, "Missing keep_username/keep_master_token for unofficial mode")
            keep = gkeepapi.Keep()
            keep.authenticate(email, token)
            note = keep.createNote(title, text)
            keep.sync()
            return self.make_response(item, {"id": note.id, "title": title, "text": text})

        return self.make_response(item, "Keep unavailable (official failed and unofficial disabled)")

    # -------------- Drive --------------

    def cmd_drive_list_files(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("q", "trashed=false")
        fields = p.get("fields", "nextPageToken, files(id, name, mimeType, parents)")
        page_size = int(p.get("page_size", 100))
        svc = self._service("drive", "v3", scopes=self.DRIVE_SCOPES)
        res = svc.files().list(q=q, pageSize=page_size, fields=fields).execute()
        return self.make_response(item, res.get("files", []))

    def _drive_find_by_path(self, svc, path: str) -> Optional[Dict[str, Any]]:
        # Simple path resolver: /Folder/Sub/file.ext in My Drive
        parts = [p for p in Path(path).parts if p not in ("/", "\\")]
        if not parts:
            return None
        parent = "root"
        node = None
        for i, name in enumerate(parts):
            is_last = i == len(parts) - 1
            mime_filter = "" if is_last else " and mimeType = 'application/vnd.google-apps.folder'"
            name_replaced = name.replace("'", "\\'")  # Escape single quotes for query
            q = f"name = '{name_replaced}' and '{parent}' in parents and trashed = false{mime_filter}"
            res = svc.files().list(q=q, fields="files(id, name, mimeType, parents)").execute()
            files = res.get("files", [])
            if not files:
                return None
            node = files[0]
            parent = node["id"]
        return node

    def cmd_drive_find_by_path(self, item: dict) -> dict:
        p = item.get("params", {})
        path = p.get("path")
        if not path:
            return self.make_response(item, "Param 'path' required")
        svc = self._service("drive", "v3", scopes=self.DRIVE_SCOPES)
        node = self._drive_find_by_path(svc, path)
        return self.make_response(item, node or {})

    def cmd_drive_download_file(self, item: dict) -> dict:
        p = item.get("params", {})
        file_id = p.get("file_id")
        path = p.get("path")
        out_path = self.prepare_path(p.get("out") or "")
        export_mime = p.get("export_mime")  # for Google Docs types

        svc = self._service("drive", "v3", scopes=self.DRIVE_SCOPES)

        if not file_id and path:
            node = self._drive_find_by_path(svc, path)
            if not node:
                return self.make_response(item, "File not found")
            file_id = node["id"]

        if not file_id:
            return self.make_response(item, "Param 'file_id' or 'path' required")

        meta = svc.files().get(fileId=file_id, fields="id, name, mimeType").execute()
        target = out_path or self.prepare_path(meta["name"])

        fh = io.FileIO(target, "wb")
        try:
            if meta["mimeType"].startswith("application/vnd.google-apps.") and export_mime:
                req = svc.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                req = svc.files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            return self.make_response(item, {"path": target, "id": meta["id"], "name": meta["name"]})
        finally:
            fh.close()

    def cmd_drive_upload_file(self, item: dict) -> dict:
        p = item.get("params", {})
        local = self.prepare_path(p.get("local"))
        remote_parent_path = p.get("remote_parent_path")  # optional folder path
        name = p.get("name") or os.path.basename(local)
        mime = p.get("mime")

        if not os.path.exists(local):
            return self.make_response(item, f"Local file not found: {local}")

        svc = self._service("drive", "v3", scopes=self.DRIVE_SCOPES)

        parents = None
        if remote_parent_path:
            node = self._drive_find_by_path(svc, remote_parent_path)
            if not node:
                return self.make_response(item, f"Remote parent path not found: {remote_parent_path}")
            parents = [node["id"]]

        media = MediaFileUpload(local, mimetype=mime, resumable=True)
        body = {"name": name}
        if parents:
            body["parents"] = parents

        file = svc.files().create(body=body, media_body=media, fields="id, name, mimeType, parents").execute()
        return self.make_response(item, file)

    # -------------- YouTube --------------

    def _extract_video_id(self, text: str) -> str:
        # Simple patterns for IDs/URLs
        m = re.search(r"(?:v=|/shorts/|/v/|youtu\.be/)([A-Za-z0-9_-]{11})", text)
        if m:
            return m.group(1)
        if re.match(r"^[A-Za-z0-9_-]{11}$", text):
            return text
        return ""

    def cmd_youtube_video_info(self, item: dict) -> dict:
        p = item.get("params", {})
        vid = self._extract_video_id(p.get("video", ""))
        if not vid:
            return self.make_response(item, "Param 'video' must be video ID or URL")

        api_key = self.plugin.get_option_value("youtube_api_key") or None
        svc = self._service("youtube", "v3", scopes=self.YT_SCOPES if not api_key else None, api_key=api_key)
        res = svc.videos().list(id=vid, part="snippet,contentDetails,statistics,status").execute()
        items = res.get("items", [])
        return self.make_response(item, items[0] if items else {})

    def cmd_youtube_transcript(self, item: dict) -> dict:
        p = item.get("params", {})
        vid = self._extract_video_id(p.get("video", ""))
        lang_pref = p.get("languages") or ["en"]
        official_only = bool(p.get("official_only", False))
        prefer_format = p.get("format") or "srt"

        # Try official API first (requires ownership/permission)
        try:
            svc = self._service("youtube", "v3", scopes=["https://www.googleapis.com/auth/youtube.force-ssl"])
            cap_list = svc.captions().list(part="id,snippet", videoId=vid).execute().get("items", [])
            if cap_list:
                cap_id = cap_list[0]["id"]
                # download returns binary; google client supports download_media
                req = svc.captions().download_media(id=cap_id, tfmt=prefer_format)
                # Execute media download into memory
                buf = io.BytesIO()
                downloader = MediaIoBaseDownload(buf, req)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                text = buf.getvalue().decode("utf-8", errors="ignore")
                return self.make_response(item, {"videoId": vid, "format": prefer_format, "text": text})
            if official_only:
                return self.make_response(item, "No official captions available or insufficient permissions")
        except HttpError as e:
            if official_only:
                return self.make_response(item, self.throw_error(e))

        # Fallback (unofficial) – explicit opt-in
        if not (self.plugin.get_option_value("allow_unofficial_youtube_transcript") or False):
            return self.make_response(item, "Unofficial transcript disabled (set allow_unofficial_youtube_transcript)")

        if YouTubeTranscriptApi is None:
            return self.make_response(item, "youtube-transcript-api not installed")

        transcripts = YouTubeTranscriptApi.list_transcripts(vid)
        # try preferred languages sequence
        for l in lang_pref:
            try:
                t = transcripts.find_transcript([l]).fetch()
                text = "\n".join([seg["text"] for seg in t])
                return self.make_response(item, {"videoId": vid, "language": l, "text": text})
            except Exception:
                continue
        # try generated
        try:
            t = transcripts.find_generated_transcript(lang_pref).fetch()
            text = "\n".join([seg["text"] for seg in t])
            return self.make_response(item, {"videoId": vid, "language": t.language_code, "text": text})
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    # -------------- Contacts (People API) --------------

    def cmd_contacts_list(self, item: dict) -> dict:
        p = item.get("params", {})
        page_size = int(p.get("page_size", 200))
        person_fields = p.get("person_fields", "names,emailAddresses,phoneNumbers")
        svc = self._service("people", "v1", scopes=self.PEOPLE_SCOPES)
        res = svc.people().connections().list(
            resourceName="people/me",
            pageSize=page_size,
            personFields=person_fields
        ).execute()
        return self.make_response(item, res.get("connections", []))

    def cmd_contacts_add(self, item: dict) -> dict:
        p = item.get("params", {})
        given = p.get("givenName")
        family = p.get("familyName")
        emails = p.get("emails") or []
        phones = p.get("phones") or []
        if not given and not family:
            return self.make_response(item, "Provide at least 'givenName' or 'familyName'")

        body = {}
        if given or family:
            body["names"] = [{"givenName": given, "familyName": family}]
        if emails:
            body["emailAddresses"] = [{"value": e} for e in emails]
        if phones:
            body["phoneNumbers"] = [{"value": ph} for ph in phones]

        svc = self._service("people", "v1", scopes=self.PEOPLE_SCOPES)
        created = svc.people().createContact(body=body).execute()
        return self.make_response(item, created)

    def prepare_path(self, path: str) -> str:
        """
        Prepare path

        :param path: path to prepare
        :return: prepared path
        """
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir('data')

        if self.is_absolute_path(path):
            return path
        else:
            return os.path.join(
                self.plugin.window.core.config.get_user_dir('data'),
                path,
            )

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute

        :param path: path to check
        :return: True if absolute
        """
        return os.path.isabs(path)