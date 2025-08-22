#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.22 10:00:00                  #
# ================================================== #

from __future__ import annotations

import os
import shlex
import subprocess
import ftplib
import smtplib
import time
import stat as pystat

from email.message import EmailMessage
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Server plugin worker: SSH, SFTP, FTP, Telnet, SMTP.
    Credentials are fetched via self.get_server_config(server, port).
    When prefer_system_ssh is enabled, uses system ssh/scp/sftp and system keys.
    """

    # Global map SERVICE -> PORT (defaults)
    SERVICE_PORTS = {
        "ssh": 22,
        "sftp": 22,
        "ftp": 21,
        "telnet": 23,
        "smtp": 25,
        "smtps": 465,
        "submission": 587,
    }

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    # ---------------------- Runner ----------------------

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

                        # -------- Core FS / Exec --------
                        if item["cmd"] == "srv_exec":
                            response = self.cmd_srv_exec(item)
                        elif item["cmd"] == "srv_ls":
                            response = self.cmd_srv_ls(item)
                        elif item["cmd"] == "srv_get":
                            response = self.cmd_srv_get(item)
                        elif item["cmd"] == "srv_put":
                            response = self.cmd_srv_put(item)
                        elif item["cmd"] == "srv_rm":
                            response = self.cmd_srv_rm(item)
                        elif item["cmd"] == "srv_mkdir":
                            response = self.cmd_srv_mkdir(item)
                        elif item["cmd"] == "srv_stat":
                            response = self.cmd_srv_stat(item)

                        # -------- SMTP --------
                        elif item["cmd"] == "smtp_send":
                            response = self.cmd_smtp_send(item)

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

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("net_timeout") or 30)
        except Exception:
            return 30

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)

    def _prefer_system_ssh(self) -> bool:
        return bool(self.plugin.get_option_value("prefer_system_ssh") or False)

    def _ssh_bins(self) -> dict:
        return {
            "ssh": (self.plugin.get_option_value("ssh_binary") or "ssh").strip(),
            "scp": (self.plugin.get_option_value("scp_binary") or "scp").strip(),
            "sftp": (self.plugin.get_option_value("sftp_binary") or "sftp").strip(),
        }

    def _ssh_options(self) -> list[str]:
        # Always enforce BatchMode=yes to avoid hanging on password prompt
        extra = (self.plugin.get_option_value("ssh_options") or "").strip()
        opts = ["-o", "BatchMode=yes"]
        if extra:
            opts += shlex.split(extra)
        return opts

    def _ssh_auto_add_hostkey(self) -> bool:
        return bool(self.plugin.get_option_value("ssh_auto_add_hostkey") or True)

    def _ftp_use_tls_default(self) -> bool:
        return bool(self.plugin.get_option_value("ftp_use_tls_default") or False)

    def _ftp_passive_default(self) -> bool:
        return bool(self.plugin.get_option_value("ftp_passive_default") or True)

    def _smtp_defaults(self) -> dict:
        return {
            "use_tls": bool(self.plugin.get_option_value("smtp_use_tls_default") or True),
            "use_ssl": bool(self.plugin.get_option_value("smtp_use_ssl_default") or False),
            "from_addr": (self.plugin.get_option_value("smtp_from_default") or "").strip(),
        }

    def _ensure_paramiko(self):
        try:
            import paramiko  # noqa
        except Exception:
            raise RuntimeError("Paramiko not installed. Install: pip install paramiko")

    def _service_from_port(self, port: int) -> str:
        for k, v in self.SERVICE_PORTS.items():
            if int(v) == int(port):
                return k
        return "unknown"

    def _server_config(self, server: str, port: int) -> dict:
        cfg = self.get_server_config(server, int(port))  # raises RuntimeError with available server names if not found
        if not cfg.get("server") or not cfg.get("login"):
            raise RuntimeError("Server config incomplete (server/login).")
        # Never expose credentials
        return cfg

    def _shell_quote(self, s: str) -> str:
        return shlex.quote(str(s))

    def _build_remote_cmd(self, command: str, cwd: str | None = None, env: dict | None = None) -> str:
        parts = []
        if env:
            exports = " ".join([f'{k}={self._shell_quote(v)}' for k, v in env.items()])
            parts.append(f"export {exports}")
        if cwd:
            parts.append(f"cd {self._shell_quote(cwd)}")
        parts.append(command)
        joined = " && ".join(parts)
        # Use bash -lc to ensure login-like shell behaviors (PATH, etc.)
        return f"bash -lc {self._shell_quote(joined)}"

    def get_server_config(self, server: str, port: int) -> dict:
        """
        Get server configuration for given server and port.

        :param server: server name or host
        :param port: server port
        :return: dict with server configuration (server, login, password, port)
        """
        servers = self.plugin.get_option_value("servers")
        available_ids = []
        for srv in servers:
            if not srv.get("enabled"):
                continue
            available_ids.append(srv.get("name"))
        config = {}
        for srv in servers:
            if not srv.get("enabled"):
                continue
            if ((srv.get("name").lower() == server.lower()
                 or srv.get("host").lower() == server.lower())
                    and int(srv.get("port", 0)) == port):
                config = {
                    "server": srv.get("host"),
                    "login": srv.get("login"),
                    "password": srv.get("password"),
                    "port": srv.get("port"),
                }
                break
        if not config:
            raise RuntimeError(
                f"Server configuration not found for {server}:{port}. Available servers: {', '.join(available_ids)}")
        return config

    # ---------------------- SSH (system) ----------------------

    def _ssh_exec_system(self, host: str, port: int, user: str, command: str, cwd: str | None,
                         env: dict | None) -> dict:
        bins = self._ssh_bins()
        base = [bins["ssh"]] + self._ssh_options() + ["-p", str(port)]
        remote = f"{user}@{host}"
        rcmd = self._build_remote_cmd(command, cwd=cwd, env=env)
        try:
            r = subprocess.run(base + [remote, rcmd], capture_output=True, text=True, timeout=self._timeout())
            return {"rc": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"SSH timeout after {self._timeout()}s: {e}")
        except FileNotFoundError:
            raise RuntimeError("ssh binary not found.")

    def _scp_get_system(self, host: str, port: int, user: str, remote_path: str, local_path: str) -> dict:
        bins = self._ssh_bins()
        base = [bins["scp"]] + self._ssh_options() + ["-P", str(port)]
        remote = f"{user}@{host}:{remote_path}"
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        try:
            r = subprocess.run(base + [remote, local_path], capture_output=True, text=True, timeout=self._timeout())
            if r.returncode != 0:
                raise RuntimeError(f"SCP get failed: {r.stderr.strip()}")
            size = os.path.getsize(local_path) if os.path.exists(local_path) else None
            return {"saved_path": local_path, "size": size}
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"SCP timeout after {self._timeout()}s: {e}")
        except FileNotFoundError:
            raise RuntimeError("scp binary not found.")

    def _scp_put_system(self, host: str, port: int, user: str, local_path: str, remote_path: str) -> dict:
        bins = self._ssh_bins()
        base = [bins["scp"]] + self._ssh_options() + ["-P", str(port)]
        if not os.path.exists(local_path):
            raise RuntimeError(f"Local path not found: {local_path}")
        remote = f"{user}@{host}:{remote_path}"
        try:
            r = subprocess.run(base + [local_path, remote], capture_output=True, text=True, timeout=self._timeout())
            if r.returncode != 0:
                raise RuntimeError(f"SCP put failed: {r.stderr.strip()}")
            return {"uploaded": True, "source": local_path, "dest": remote_path}
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"SCP timeout after {self._timeout()}s: {e}")
        except FileNotFoundError:
            raise RuntimeError("scp binary not found.")

    def _ssh_ls_system(self, host: str, port: int, user: str, path: str | None) -> dict:
        # Best-effort parse of `ls -la`. Not perfect on all systems.
        p = path or "."
        cmd = f'ls -la {self._shell_quote(p)}'
        res = self._ssh_exec_system(host, port, user, cmd, cwd=None, env=None)
        if res["rc"] != 0:
            raise RuntimeError(f"ls failed: {res['stderr'].strip()}")
        entries = []
        for line in res["stdout"].splitlines():
            if not line or line.startswith("total "):
                continue
            parts = line.split(maxsplit=8)
            if len(parts) < 9:
                continue
            perms, _, owner, group, size, month, day, time_or_year, name = parts
            if name in [".", ".."]:
                continue
            ftype = "file"
            if perms.startswith("d"):
                ftype = "dir"
            elif perms.startswith("l"):
                ftype = "link"
            # size may fail to int if localized
            try:
                size_val = int(size)
            except Exception:
                size_val = None
            entries.append({"name": name, "type": ftype, "size": size_val, "raw": line})
        return {"entries": entries, "raw": res["stdout"]}

    # ---------------------- SSH / SFTP (paramiko) ----------------------

    def _ssh_exec_paramiko(self, host: str, port: int, user: str, password: str | None, command: str, cwd: str | None,
                           env: dict | None) -> dict:
        self._ensure_paramiko()
        import paramiko
        client = paramiko.SSHClient()
        if self._ssh_auto_add_hostkey():
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                host,
                port=port,
                username=user,
                password=password or None,
                timeout=self._timeout(),
                allow_agent=True,
                look_for_keys=True,
            )
            rcmd = self._build_remote_cmd(command, cwd=cwd, env=env)
            stdin, stdout, stderr = client.exec_command(rcmd, timeout=self._timeout())
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            return {"rc": rc, "stdout": out, "stderr": err}
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _sftp_opener(self, host: str, port: int, user: str, password: str | None):
        self._ensure_paramiko()
        import paramiko
        client = paramiko.SSHClient()
        if self._ssh_auto_add_hostkey():
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            port=port,
            username=user,
            password=password or None,
            timeout=self._timeout(),
            allow_agent=True,
            look_for_keys=True,
        )
        sftp = client.open_sftp()
        return client, sftp

    def _sftp_ls(self, host: str, port: int, user: str, password: str | None, path: str | None) -> dict:
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            p = path or "."
            attrs = sftp.listdir_attr(p)
            out = []
            for a in attrs:
                name = getattr(a, "filename", None)
                mode = a.st_mode if hasattr(a, "st_mode") else 0
                ftype = "file"
                if pystat.S_ISDIR(mode):
                    ftype = "dir"
                elif pystat.S_ISLNK(mode):
                    ftype = "link"
                out.append({
                    "name": name,
                    "type": ftype,
                    "size": getattr(a, "st_size", None),
                    "mtime": getattr(a, "st_mtime", None),
                    "mode": mode,
                })
            return {"entries": out}
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def _sftp_get(self, host: str, port: int, user: str, password: str | None, remote_path: str,
                  local_path: str) -> dict:
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            sftp.get(remote_path, local_path)
            size = os.path.getsize(local_path)
            return {"saved_path": local_path, "size": size}
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def _sftp_put(self, host: str, port: int, user: str, password: str | None, local_path: str, remote_path: str,
                  make_dirs: bool) -> dict:
        if not os.path.exists(local_path):
            raise RuntimeError(f"Local path not found: {local_path}")
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            if make_dirs:
                # naive mkdir -p
                dir_part = os.path.dirname(remote_path)
                if dir_part:
                    self._sftp_mkdirs(sftp, dir_part)
            sftp.put(local_path, remote_path)
            return {"uploaded": True, "source": local_path, "dest": remote_path}
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def _sftp_mkdirs(self, sftp, remote_dir: str):
        parts = []
        while True:
            head, tail = os.path.split(remote_dir)
            if tail:
                parts.append(tail)
                remote_dir = head
            else:
                if head:
                    parts.append(head)
                break
        parts = list(reversed([p for p in parts if p not in ["", "/"]]))
        cur = ""
        for p in parts:
            if cur == "":
                if remote_dir.startswith("/"):
                    cur = f"/{p}"
                else:
                    cur = p
            else:
                cur = f"{cur}/{p}"
            try:
                sftp.stat(cur)
            except Exception:
                try:
                    sftp.mkdir(cur)
                except Exception:
                    pass

    def _sftp_rm(self, host: str, port: int, user: str, password: str | None, remote_path: str) -> dict:
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            st = sftp.stat(remote_path)
            if pystat.S_ISDIR(st.st_mode):
                # Non-recursive rmdir
                sftp.rmdir(remote_path)
                return {"removed": True, "path": remote_path, "type": "dir"}
            else:
                sftp.remove(remote_path)
                return {"removed": True, "path": remote_path, "type": "file"}
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def _sftp_mkdir(self, host: str, port: int, user: str, password: str | None, remote_path: str,
                    exist_ok: bool) -> dict:
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            try:
                sftp.mkdir(remote_path)
            except IOError:
                if not exist_ok:
                    raise
            return {"mkdir": True, "path": remote_path}
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    def _sftp_stat(self, host: str, port: int, user: str, password: str | None, remote_path: str) -> dict:
        client, sftp = self._sftp_opener(host, port, user, password)
        try:
            st = sftp.stat(remote_path)
            mode = st.st_mode
            ftype = "file"
            if pystat.S_ISDIR(mode):
                ftype = "dir"
            elif pystat.S_ISLNK(mode):
                ftype = "link"
            return {
                "path": remote_path,
                "type": ftype,
                "size": getattr(st, "st_size", None),
                "mtime": getattr(st, "st_mtime", None),
                "mode": mode,
            }
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                client.close()
            except Exception:
                pass

    # ---------------------- FTP / FTPS (stdlib) ----------------------

    def _ftp_connect(self, host: str, port: int, user: str, password: str | None, use_tls: bool, passive: bool):
        if use_tls:
            ftp = ftplib.FTP_TLS()
        else:
            ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=self._timeout())
        ftp.login(user=user, passwd=password or "")
        if use_tls:
            try:
                ftp.prot_p()  # secure data channel
            except Exception:
                pass
        ftp.set_pasv(passive)
        return ftp

    def _ftp_ls(self, host: str, port: int, user: str, password: str | None, path: str | None) -> dict:
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            p = path or "."
            entries = []
            # Prefer MLSD if supported
            try:
                for name, facts in ftp.mlsd(p):
                    ftype = facts.get("type", "file")
                    if ftype == "dir":
                        t = "dir"
                    elif ftype == "file":
                        t = "file"
                    else:
                        t = ftype
                    size = None
                    try:
                        size = int(facts.get("size")) if "size" in facts else None
                    except Exception:
                        pass
                    mtime = None
                    try:
                        # facts['modify'] like YYYYMMDDHHMMSS
                        mod = facts.get("modify")
                        if mod and len(mod) >= 14:
                            # convert to epoch best-effort
                            mtime = int(time.mktime(time.strptime(mod, "%Y%m%d%H%M%S")))
                    except Exception:
                        pass
                    entries.append({"name": name, "type": t, "size": size, "mtime": mtime})
            except Exception:
                # Fallback to NLST (names only)
                names = ftp.nlst(p)
                for name in names:
                    base = os.path.basename(name)
                    entries.append({"name": base, "type": "unknown"})
            return {"entries": entries}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    def _ftp_get(self, host: str, port: int, user: str, password: str | None, remote_path: str,
                 local_path: str) -> dict:
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            with open(local_path, "wb") as fh:
                ftp.retrbinary(f"RETR {remote_path}", fh.write)
            size = os.path.getsize(local_path)
            return {"saved_path": local_path, "size": size}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    def _ftp_put(self, host: str, port: int, user: str, password: str | None, local_path: str,
                 remote_path: str) -> dict:
        if not os.path.exists(local_path):
            raise RuntimeError(f"Local path not found: {local_path}")
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            with open(local_path, "rb") as fh:
                ftp.storbinary(f"STOR {remote_path}", fh)
            return {"uploaded": True, "source": local_path, "dest": remote_path}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    def _ftp_rm(self, host: str, port: int, user: str, password: str | None, remote_path: str) -> dict:
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            try:
                ftp.delete(remote_path)
                return {"removed": True, "path": remote_path, "type": "file"}
            except ftplib.error_perm:
                # maybe it's a dir (non-recursive)
                ftp.rmd(remote_path)
                return {"removed": True, "path": remote_path, "type": "dir"}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    def _ftp_mkdir(self, host: str, port: int, user: str, password: str | None, remote_path: str,
                   exist_ok: bool) -> dict:
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            try:
                ftp.mkd(remote_path)
            except ftplib.error_perm:
                if not exist_ok:
                    raise
            return {"mkdir": True, "path": remote_path}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    def _ftp_stat(self, host: str, port: int, user: str, password: str | None, remote_path: str) -> dict:
        use_tls = self._ftp_use_tls_default() or (int(port) in [990])
        passive = self._ftp_passive_default()
        ftp = self._ftp_connect(host, port, user, password, use_tls, passive)
        try:
            # Try MLST single path
            try:
                resp = []
                ftp.sendcmd("TYPE I")  # binary
                ftp.sendcmd(f"MLST {remote_path}")
                # ftplib doesn't parse MLST easily; use voidcmd and handle later is messy.
            except Exception:
                pass
            # Fallback: list parent and find entry
            parent = os.path.dirname(remote_path) or "."
            name = os.path.basename(remote_path)
            info = None
            try:
                for n, facts in ftp.mlsd(parent):
                    if n == name:
                        info = facts
                        break
            except Exception:
                pass
            if info:
                t = info.get("type", "file")
                ftype = "dir" if t == "dir" else ("file" if t == "file" else t)
                size = None
                try:
                    size = int(info.get("size")) if "size" in info else None
                except Exception:
                    pass
                mtime = None
                try:
                    mod = info.get("modify")
                    if mod and len(mod) >= 14:
                        mtime = int(time.mktime(time.strptime(mod, "%Y%m%d%H%M%S")))
                except Exception:
                    pass
                return {"path": remote_path, "type": ftype, "size": size, "mtime": mtime}
            # As last resort, try size cmd (files only)
            try:
                ftp.sendcmd("TYPE I")
                size = ftp.size(remote_path)
                return {"path": remote_path, "type": "file", "size": size}
            except Exception:
                pass
            # Unknown
            return {"path": remote_path, "type": "unknown"}
        finally:
            try:
                ftp.quit()
            except Exception:
                pass

    # ---------------------- Telnet (stdlib, best-effort) ----------------------

    def _telnet_exec(self, host: str, port: int, user: str, password: str | None, command: str, login_prompt: str,
                     password_prompt: str, prompt: str) -> dict:
        try:
            import telnetlib  # deprecated in newer Python, but still available in many
        except Exception:
            raise RuntimeError("telnetlib not available. Use SSH instead.")
        timeout = self._timeout()
        tn = telnetlib.Telnet(host, port, timeout=timeout)
        try:
            if login_prompt:
                tn.read_until(login_prompt.encode("utf-8"), timeout=timeout)
                tn.write((user + "\n").encode("utf-8"))
            if password_prompt is not None:
                tn.read_until(password_prompt.encode("utf-8"), timeout=timeout)
                tn.write(((password or "") + "\n").encode("utf-8"))
            if prompt:
                tn.read_until(prompt.encode("utf-8"), timeout=timeout)
            tn.write((command + "\n").encode("utf-8"))
            out = tn.read_until(prompt.encode("utf-8"), timeout=timeout)
            # crude strip
            text = out.decode("utf-8", errors="replace")
            return {"rc": 0, "stdout": text, "stderr": ""}
        finally:
            try:
                tn.close()
            except Exception:
                pass

    # ---------------------- SMTP (stdlib) ----------------------

    def _smtp_send_mail(self, host: str, port: int, user: str, password: str | None, mail: dict) -> dict:
        defaults = self._smtp_defaults()
        use_tls = bool(mail.get("use_tls", defaults["use_tls"]))
        use_ssl = bool(mail.get("use_ssl", defaults["use_ssl"]))
        from_addr = (mail.get("from_addr") or defaults["from_addr"] or user).strip()
        to = mail.get("to")
        if isinstance(to, str):
            to = [to]
        cc = mail.get("cc") or []
        bcc = mail.get("bcc") or []
        subject = mail.get("subject") or ""
        body = mail.get("body") or ""
        html = bool(mail.get("html") or False)

        if not to:
            raise RuntimeError("Param 'to' required for smtp_send.")

        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        if html:
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        # Attachments (local files)
        for apath in (mail.get("attachments") or []):
            lp = self.prepare_path(apath)
            if not os.path.exists(lp):
                raise RuntimeError(f"Attachment not found: {lp}")
            with open(lp, "rb") as f:
                data = f.read()
            maintype, subtype = "application", "octet-stream"
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(lp))

        if use_ssl or int(port) in [465]:
            smtp = smtplib.SMTP_SSL(host, int(port), timeout=self._timeout())
        else:
            smtp = smtplib.SMTP(host, int(port), timeout=self._timeout())
        try:
            smtp.ehlo()
            if use_tls and not use_ssl:
                smtp.starttls()
                smtp.ehlo()
            if user:
                smtp.login(user, password or "")
            rcpt = to + (cc if isinstance(cc, list) else []) + (bcc if isinstance(bcc, list) else [])
            smtp.send_message(msg, from_addr=from_addr, to_addrs=rcpt)
            return {"sent": True, "to": rcpt}
        finally:
            try:
                smtp.quit()
            except Exception:
                pass

    # ---------------------- Commands ----------------------

    def cmd_srv_exec(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        command = p.get("command")
        cwd = p.get("cwd")
        env = p.get("env") or {}
        if not (server and port and command):
            return self.make_response(item, "Params 'server', 'port' and 'command' required.")

        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")

        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                res = self._ssh_exec_system(host, port, user, command, cwd=cwd, env=env)
                return self.make_response(item, res)
            else:
                res = self._ssh_exec_paramiko(host, port, user, password, command, cwd=cwd, env=env)
                return self.make_response(item, res)
        elif svc == "telnet" or int(port) == 23:
            login_prompt = (self.plugin.get_option_value("telnet_login_prompt") or "login:").strip()
            password_prompt = (self.plugin.get_option_value("telnet_password_prompt") or "Password:").strip()
            prompt = (self.plugin.get_option_value("telnet_prompt") or "$ ").strip()
            res = self._telnet_exec(host, port, user, password, command, login_prompt, password_prompt, prompt)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_exec not supported for port {port} ({svc}).")

    def cmd_srv_ls(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        path = p.get("path") or "."
        if not (server and port):
            return self.make_response(item, "Params 'server' and 'port' required.")
        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                res = self._ssh_ls_system(host, port, user, path)
                return self.make_response(item, res)
            else:
                res = self._sftp_ls(host, port, user, password, path)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_ls(host, port, user, password, path)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_ls not supported for port {port} ({svc}).")

    def cmd_srv_get(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        remote_path = p.get("remote_path")
        local_path = p.get("local_path")
        overwrite = bool(p.get("overwrite", True))
        if not (server and port and remote_path):
            return self.make_response(item, "Params 'server', 'port' and 'remote_path' required.")
        if not local_path:
            local_path = self.prepare_path(os.path.basename(remote_path))
        else:
            local_path = self.prepare_path(local_path)
        if os.path.exists(local_path) and not overwrite:
            return self.make_response(item, f"Local path exists and overwrite=False: {local_path}")

        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                res = self._scp_get_system(host, port, user, remote_path, local_path)
                return self.make_response(item, res)
            else:
                res = self._sftp_get(host, port, user, password, remote_path, local_path)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_get(host, port, user, password, remote_path, local_path)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_get not supported for port {port} ({svc}).")

    def cmd_srv_put(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        local_path = p.get("local_path")
        remote_path = p.get("remote_path")
        make_dirs = bool(p.get("make_dirs", True))
        if not (server and port and local_path):
            return self.make_response(item, "Params 'server', 'port' and 'local_path' required.")
        lp = self.prepare_path(local_path)
        if not os.path.exists(lp):
            return self.make_response(item, f"Local path not found: {lp}")
        if not remote_path:
            remote_path = os.path.basename(lp)

        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                # System scp cannot create remote dirs automatically; rely on user setting up path
                res = self._scp_put_system(host, port, user, lp, remote_path)
                return self.make_response(item, res)
            else:
                res = self._sftp_put(host, port, user, password, lp, remote_path, make_dirs=make_dirs)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_put(host, port, user, password, lp, remote_path)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_put not supported for port {port} ({svc}).")

    def cmd_srv_rm(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        remote_path = p.get("remote_path")
        if not (server and port and remote_path):
            return self.make_response(item, "Params 'server', 'port' and 'remote_path' required.")
        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                # Use rm/rmdir via SSH (non-recursive)
                cmd = f"if [ -d {self._shell_quote(remote_path)} ]; then rmdir {self._shell_quote(remote_path)}; else rm -f {self._shell_quote(remote_path)}; fi"
                res = self._ssh_exec_system(host, port, user, cmd, cwd=None, env=None)
                if res["rc"] != 0:
                    raise RuntimeError(f"remove failed: {res['stderr'].strip()}")
                return self.make_response(item, {"removed": True, "path": remote_path})
            else:
                res = self._sftp_rm(host, port, user, password, remote_path)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_rm(host, port, user, password, remote_path)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_rm not supported for port {port} ({svc}).")

    def cmd_srv_mkdir(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        remote_path = p.get("remote_path")
        exist_ok = bool(p.get("exist_ok", True))
        if not (server and port and remote_path):
            return self.make_response(item, "Params 'server', 'port' and 'remote_path' required.")
        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                cmd = f"mkdir {'-p ' if exist_ok else ''}{self._shell_quote(remote_path)}"
                res = self._ssh_exec_system(host, port, user, cmd, cwd=None, env=None)
                if res["rc"] != 0:
                    raise RuntimeError(f"mkdir failed: {res['stderr'].strip()}")
                return self.make_response(item, {"mkdir": True, "path": remote_path})
            else:
                res = self._sftp_mkdir(host, port, user, password, remote_path, exist_ok=exist_ok)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_mkdir(host, port, user, password, remote_path, exist_ok=exist_ok)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_mkdir not supported for port {port} ({svc}).")

    def cmd_srv_stat(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        remote_path = p.get("remote_path")
        if not (server and port and remote_path):
            return self.make_response(item, "Params 'server', 'port' and 'remote_path' required.")
        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")
        svc = self._service_from_port(port)
        if svc in ["ssh", "sftp", "unknown"] or int(port) == 22:
            if self._prefer_system_ssh():
                # Try 'stat' then fallback to test
                cmd = f"(stat -c '%F|%s|%Y' {self._shell_quote(remote_path)} 2>/dev/null) || echo 'UNKNOWN|||';"
                res = self._ssh_exec_system(host, port, user, cmd, cwd=None, env=None)
                if res["rc"] != 0:
                    raise RuntimeError(f"stat failed: {res['stderr'].strip()}")
                line = res["stdout"].strip().splitlines()[-1] if res["stdout"] else "UNKNOWN|||"
                kind, size, mtime = (line.split("|") + ["", "", ""])[:3]
                ftype = "file"
                if "directory" in kind.lower():
                    ftype = "dir"
                elif "link" in kind.lower():
                    ftype = "link"
                size_val = None
                try:
                    size_val = int(size) if size else None
                except Exception:
                    pass
                mtime_val = None
                try:
                    mtime_val = int(mtime) if mtime else None
                except Exception:
                    pass
                return self.make_response(item,
                                          {"path": remote_path, "type": ftype, "size": size_val, "mtime": mtime_val})
            else:
                res = self._sftp_stat(host, port, user, password, remote_path)
                return self.make_response(item, res)
        elif svc == "ftp" or int(port) in [21, 990]:
            res = self._ftp_stat(host, port, user, password, remote_path)
            return self.make_response(item, res)
        else:
            return self.make_response(item, f"srv_stat not supported for port {port} ({svc}).")

    def cmd_smtp_send(self, item: dict) -> dict:
        p = item.get("params", {}) or {}
        server = p.get("server")
        port = int(p.get("port") or 0)
        if not (server and port):
            return self.make_response(item, "Params 'server' and 'port' required.")
        cfg = self._server_config(server, port)
        host = cfg.get("server")
        user = cfg.get("login")
        password = cfg.get("password")

        mail = {
            "from_addr": p.get("from_addr"),
            "to": p.get("to"),
            "cc": p.get("cc"),
            "bcc": p.get("bcc"),
            "subject": p.get("subject"),
            "body": p.get("body"),
            "html": bool(p.get("html") or False),
            "attachments": p.get("attachments") or [],
            "use_tls": p.get("use_tls"),
            "use_ssl": p.get("use_ssl"),
        }
        res = self._smtp_send_mail(host, port, user, password, mail)
        return self.make_response(item, res)
