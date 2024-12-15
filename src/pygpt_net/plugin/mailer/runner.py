#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 04:00:00                  #
# ================================================== #

import datetime
import smtplib
import poplib

from email.parser import BytesParser
from typing import Any
from bs4 import BeautifulSoup

from pygpt_net.item.ctx import CtxItem


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self.signals = None

    def attach_signals(self, signals):
        """
        Attach signals

        :param signals: signals
        """
        self.signals = signals

    def parse_email(self, msg, as_text: bool = True) -> str:
        """
        Parse email message

        :param msg: email message
        :param as_text: return as text
        :return: parsed email
        """
        body = ""
        is_html = False
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    body = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                elif content_type == 'text/html' and 'attachment' not in content_disposition:
                    body = part.get_payload(decode=True).decode(part.get_content_charset('utf-8'))
                    is_html = True
        else:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset('utf-8'))
        if is_html and as_text:
            body = BeautifulSoup(body, 'html.parser').get_text()
        return body

    def smtp_get_email_body(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Receive emails from mailbox

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        server = self.plugin.get_option_value("smtp_host")
        port = self.plugin.get_option_value("smtp_port_inbox")
        id = item["params"].get("id", "")
        username = self.plugin.get_option_value("smtp_user")
        password = self.plugin.get_option_value("smtp_password")
        msg = "Receiving email from: {}".format(server)
        format = "text"
        as_text = True
        if "format" in item["params"]:
            format = item["params"]["format"].lower()
        if format == "html":
            as_text = False
        self.log(msg)
        try:
            if port in [995]:
                pop3 = poplib.POP3_SSL(server, port)
            else:
                pop3 = poplib.POP3(server, port)

            msg = pop3.getwelcome().decode('utf-8')
            self.log(msg)
            pop3.user(username)
            pop3.pass_(password)
            response, lines, octets = pop3.retr(id)
            msg_content = b'\r\n'.join(lines)
            msg = BytesParser().parsebytes(msg_content)
            result = {
                "ID": id,
                "From": msg["From"],
                "Subject": msg["Subject"],
                "Date": msg["Date"],
                "Message": self.parse_email(msg, as_text)
            }
            pop3.quit()
        except Exception as e:
            self.error(e)
            result = "Error: {}".format(str(e))
        return {
            "request": request,
            "result": str(result)
        }

    def smtp_receive_emails(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Receive emails from mailbox

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        server = self.plugin.get_option_value("smtp_host")
        port = self.plugin.get_option_value("smtp_port_inbox")
        limit = item["params"].get("limit", 10)
        offset = item["params"].get("offset", 0)
        username = self.plugin.get_option_value("smtp_user")
        password = self.plugin.get_option_value("smtp_password")
        msg = "Receiving emails from: {}".format(server)
        order = "desc"
        if "order" in item["params"]:
            tmp_order = item["params"]["order"].lower()
            if tmp_order in ["asc", "desc"]:
                order = tmp_order
        self.log(msg)

        messages = []
        try:
            if port in [995]:
                pop3 = poplib.POP3_SSL(server, port)
            else:
                pop3 = poplib.POP3(server, port)

            msg = pop3.getwelcome().decode('utf-8')
            self.log(msg)
            pop3.user(username)
            pop3.pass_(password)

            message_count, mailbox_size = pop3.stat()
            total = message_count
            print(f'Num of messages: {message_count}, Inbox size: {mailbox_size} bytes')

            if order == "desc":
                if offset > 0:
                    message_count -= offset
                if message_count < limit:
                    limit = message_count
                range_max = message_count - limit
                if limit == 0:
                    range_max = 0
                for i in range(message_count, range_max, -1):
                    response, lines, octets = pop3.top(i, 0)
                    msg_content = b'\r\n'.join(lines)
                    msg = BytesParser().parsebytes(msg_content)
                    msg_body = {
                        "ID": i,
                        "From": msg["From"],
                        "Subject": msg["Subject"],
                        "Date": msg["Date"],
                    }
                    messages.append(msg_body)
            else:
                if limit == 0:
                    limit = message_count
                else:
                    limit += offset
                if limit > message_count:
                    limit = message_count
                for i in range(offset + 1, limit + 1):
                    response, lines, octets = pop3.top(i, 0)
                    msg_content = b'\r\n'.join(lines)
                    msg = BytesParser().parsebytes(msg_content)
                    msg_body = {
                        "ID": i,
                        "From": msg["From"],
                        "Subject": msg["Subject"],
                        "Date": msg["Date"],
                    }
                    messages.append(msg_body)

            pop3.quit()
            result = {
                "total": total,
                "messages": messages,
            }
        except Exception as e:
            self.error(e)
            result = "Error: {}".format(str(e))
        return {
            "request": request,
            "result": str(result)
        }

    def smtp_send_email(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command on host

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Sending email to: {}".format(item["params"]['recipient'])
        self.log(msg)
        try:
            email_to = item["params"]['recipient']
            message = item["params"]['message']
            subject = item["params"]['subject']
            from_addr = self.plugin.get_option_value("from_email")
            host = self.plugin.get_option_value("smtp_host")
            port = self.plugin.get_option_value("smtp_port_outbox")
            user = self.plugin.get_option_value("smtp_user")
            password = self.plugin.get_option_value("smtp_password")
            date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            body = """From: {sender}\nTo: {to}\nDate: {date}\nSubject: {subject}\n\n{msg}
                    """.format(sender=from_addr, to=email_to, date=date, subject=subject, msg=message)
            if port in [465]:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
            server.ehlo()
            if port in [587]:
                server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, email_to, body)
            server.close()
            result = "OK"
        except Exception as e:
            self.error(e)
            result = "Error: {}".format(str(e))
        return {
            "request": request,
            "result": str(result)
        }

    def error(self, err: Any):
        """
        Log error message

        :param err: exception or error message
        """
        if self.signals is not None:
            self.signals.error.emit(err)

    def status(self, msg: str):
        """
        Send status message

        :param msg: status message
        """
        if self.signals is not None:
            self.signals.status.emit(msg)

    def debug(self, msg: Any):
        """
        Log debug message

        :param msg: message to log
        """
        if self.signals is not None:
            self.signals.debug.emit(msg)

    def log(self, msg, sandbox: bool = False):
        """
        Log message to console

        :param msg: message to log
        :param sandbox: is sandbox mode
        """
        full_msg = '[SMTP]' + ' ' + str(msg)
        if self.signals is not None:
            self.signals.log.emit(full_msg)
