#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 20:00:00                  #
# ================================================== #

from __future__ import annotations

import json
import time
import hmac
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    Tuya Smart Home plugin worker: Auth (token), Devices, Status, Control, Sensors.
    Uses Tuya Cloud API (v1.0) with proper "new signature" HMAC-SHA256 signing.
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

                        # -------- Auth --------
                        if item["cmd"] == "tuya_set_keys":
                            response = self.cmd_tuya_set_keys(item)
                        elif item["cmd"] == "tuya_set_uid":
                            response = self.cmd_tuya_set_uid(item)
                        elif item["cmd"] == "tuya_token_get":
                            response = self.cmd_tuya_token_get(item)

                        # -------- Devices / Info --------
                        elif item["cmd"] == "tuya_devices_list":
                            response = self.cmd_tuya_devices_list(item)
                        elif item["cmd"] == "tuya_device_get":
                            response = self.cmd_tuya_device_get(item)
                        elif item["cmd"] == "tuya_device_status":
                            response = self.cmd_tuya_device_status(item)
                        elif item["cmd"] == "tuya_device_functions":
                            response = self.cmd_tuya_device_functions(item)
                        elif item["cmd"] == "tuya_find_device":
                            response = self.cmd_tuya_find_device(item)

                        # -------- Control --------
                        elif item["cmd"] == "tuya_device_set":
                            response = self.cmd_tuya_device_set(item)
                        elif item["cmd"] == "tuya_device_send":
                            response = self.cmd_tuya_device_send(item)
                        elif item["cmd"] == "tuya_device_on":
                            response = self.cmd_tuya_device_on(item)
                        elif item["cmd"] == "tuya_device_off":
                            response = self.cmd_tuya_device_off(item)
                        elif item["cmd"] == "tuya_device_toggle":
                            response = self.cmd_tuya_device_toggle(item)

                        # -------- Sensors --------
                        elif item["cmd"] == "tuya_sensors_read":
                            response = self.cmd_tuya_sensors_read(item)

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

    # ---------------------- HTTP / Sign helpers ----------------------

    def _api_base(self) -> str:
        return (self.plugin.get_option_value("api_base") or "https://openapi.tuyaeu.com").rstrip("/")

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _lang(self) -> str:
        return (self.plugin.get_option_value("lang") or "en").strip() or "en"

    def _client(self) -> Tuple[str, str]:
        cid = (self.plugin.get_option_value("tuya_client_id") or "").strip()
        sec = (self.plugin.get_option_value("tuya_client_secret") or "").strip()
        if not cid or not sec:
            raise RuntimeError("Set Tuya Client ID and Client Secret first.")
        return cid, sec

    def _now_ms_str(self) -> str:
        return str(int(time.time() * 1000))

    def _hmac_sha256_upper(self, key: str, msg: str) -> str:
        return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    def _sha256_hex(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _json_canonical(self, body: Union[dict, list, None]) -> str:
        # Canonical JSON to ensure hash matches the actual sent body
        if body is None:
            return ""
        return json.dumps(body, separators=(",", ":"), sort_keys=True, ensure_ascii=False)

    def _sorted_params_list(self, params: Optional[dict | List[Tuple[str, Any]]]) -> List[Tuple[str, str]]:
        if not params:
            return []
        if isinstance(params, list):
            # Convert values to str, preserve provided order
            return [(k, str(v)) for (k, v) in params]
        out: List[Tuple[str, str]] = []
        for k in sorted(params.keys()):
            v = params[k]
            if isinstance(v, list):
                for vv in v:
                    out.append((k, str(vv)))
            else:
                out.append((k, str(v)))
        return out

    def _canonical_qs(self, params: Optional[dict | List[Tuple[str, Any]]]) -> str:
        items = self._sorted_params_list(params)
        if not items:
            return ""
        return urlencode(items, doseq=True)

    def _token_cached(self) -> Tuple[Optional[str], int]:
        tok = (self.plugin.get_option_value("tuya_access_token") or "").strip()
        exp_at = 0
        try:
            exp_at = int(self.plugin.get_option_value("tuya_token_expire_at") or 0)
        except Exception:
            exp_at = 0
        return (tok if tok else None), exp_at

    def _token_valid(self) -> bool:
        tok, exp_at = self._token_cached()
        if not tok:
            return False
        return int(time.time()) < exp_at

    def _ensure_token(self):
        if not self._token_valid():
            self._token_get()

    def _build_string_to_sign(self, method: str, path: str, params: Optional[dict | List[Tuple[str, Any]]], body_str: str) -> str:
        # signature: stringToSign = method + "\n" + contentSHA256 + "\n" + headersStr + "\n" + urlPathWithQuery
        method = (method or "GET").upper()
        content_sha256 = self._sha256_hex(body_str or "")
        headers_str = ""  # We don't sign headers (optional feature)
        qs = self._canonical_qs(params)
        url_part = path if path.startswith("/") else "/" + path
        if qs:
            url_part = f"{url_part}?{qs}"
        return "\n".join([method, content_sha256, headers_str, url_part])

    def _headers(
        self,
        method: str,
        path: str,
        params: Optional[dict | List[Tuple[str, Any]]] = None,
        body_str: str = "",
    ) -> Dict[str, str]:
        cid, sec = self._client()
        t = self._now_ms_str()
        tok, _ = self._token_cached()
        # Do not include token in sign for /v1.0/token
        include_token = bool(tok) and not path.startswith("/v1.0/token")

        string_to_sign = self._build_string_to_sign(method, path, params, body_str)
        sign_src = cid + (tok if include_token else "") + t + string_to_sign
        sign = self._hmac_sha256_upper(sec, sign_src)

        hdrs = {
            "client_id": cid,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json; charset=utf-8",
            "lang": self._lang(),
        }
        if include_token:
            hdrs["access_token"] = tok
        return hdrs

    def _handle_tuya_response(self, r: requests.Response) -> dict:
        try:
            payload = r.json() if r.content else {}
        except Exception:
            raise RuntimeError(f"HTTP {r.status_code}: Non-JSON response: {r.text}")

        if r.status_code < 200 or r.status_code >= 300:
            raise RuntimeError(json.dumps({"status": r.status_code, "error": payload}, ensure_ascii=False))

        if payload.get("success") is False:
            code = payload.get("code")
            msg = payload.get("msg") or payload.get("message")
            # Common sign error codes often: 1010, "sign invalid"
            raise RuntimeError(json.dumps({
                "status": r.status_code,
                "success": False,
                "code": code,
                "error": msg,
                "detail": payload
            }, ensure_ascii=False))

        return payload

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict | List[Tuple[str, Any]]] = None,
        body: Optional[dict | list] = None,
        require_token: bool = True,
    ) -> dict:
        if not path.startswith("/"):
            path = "/" + path

        # Don't fetch token for token endpoint
        if require_token and not path.startswith("/v1.0/token"):
            self._ensure_token()

        url = f"{self._api_base()}{path}"
        params_items = self._sorted_params_list(params)

        body_str = self._json_canonical(body) if method.upper() in ("POST", "PUT", "PATCH") else ""
        headers = self._headers(method, path, params_items, body_str)

        # Use data=body_str to ensure the signed body equals the sent body
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, params=params_items, timeout=self._timeout())
        elif method.upper() == "POST":
            r = requests.post(url, headers=headers, params=params_items, data=body_str, timeout=self._timeout())
        elif method.upper() == "DELETE":
            r = requests.delete(url, headers=headers, params=params_items, data=body_str, timeout=self._timeout())
        elif method.upper() == "PUT":
            r = requests.put(url, headers=headers, params=params_items, data=body_str, timeout=self._timeout())
        elif method.upper() == "PATCH":
            r = requests.patch(url, headers=headers, params=params_items, data=body_str, timeout=self._timeout())
        else:
            raise RuntimeError(f"Unsupported method: {method}")

        return self._handle_tuya_response(r)

    def _get(self, path: str, params: Optional[dict | List[Tuple[str, Any]]] = None) -> dict:
        return self._request("GET", path, params=params, body=None, require_token=not path.startswith("/v1.0/token"))

    def _post_json(self, path: str, payload: dict | list | None = None, params: Optional[dict | List[Tuple[str, Any]]] = None) -> dict:
        return self._request("POST", path, params=params, body=(payload or {}), require_token=not path.startswith("/v1.0/token"))

    # ---------------------- Token management ----------------------

    def _token_get(self) -> dict:
        # signature for GET /v1.0/token?grant_type=1 (no access_token in sign)
        res = self._request("GET", "/v1.0/token", params={"grant_type": "1"}, body=None, require_token=False)
        result = res.get("result") or {}
        access_token = (result.get("access_token") or "").strip()
        expire_time = int(result.get("expire_time") or 0)
        if not access_token:
            raise RuntimeError("Token retrieval failed: missing access_token.")

        exp_at = int(time.time()) + max(0, expire_time - 60)
        self.plugin.set_option_value("tuya_access_token", access_token)
        self.plugin.set_option_value("tuya_token_expires_in", str(expire_time))
        self.plugin.set_option_value("tuya_token_expire_at", str(exp_at))
        if result.get("refresh_token"):
            self.plugin.set_option_value("tuya_refresh_token", result["refresh_token"])
        return res

    # ---------------------- Device helpers ----------------------

    def _get_uid(self, p: dict) -> str:
        uid = (p.get("uid") or self.plugin.get_option_value("tuya_uid") or "").strip()
        if not uid:
            raise RuntimeError("Missing UID. Set 'tuya_uid' in options or pass 'uid' param.")
        return uid

    def _device_status(self, device_id: str) -> List[dict]:
        res = self._get(f"/v1.0/devices/{device_id}/status")
        return res.get("result") or res.get("data") or []

    def _device_info(self, device_id: str) -> dict:
        res = self._get(f"/v1.0/devices/{device_id}")
        return res.get("result") or res.get("data") or {}

    def _device_functions(self, device_id: str) -> List[dict]:
        res = self._get(f"/v1.0/devices/{device_id}/functions")
        data = res.get("result") or res.get("data") or {}
        funcs = data.get("functions") or data.get("result") or data
        if isinstance(funcs, dict):
            funcs = funcs.get("functions") or []
        if not isinstance(funcs, list):
            funcs = []
        return funcs

    def _guess_switch_code(self, device_id: str) -> str:
        candidates = [
            "switch", "switch_main", "switch_led", "power_switch",
            "switch_1", "switch_2", "switch_3", "switch_usb1", "on_off",
            "master_switch", "relay_switch", "socket1"
        ]
        try:
            funcs = self._device_functions(device_id)
            codes = [f.get("code") for f in funcs if isinstance(f, dict)]
            for c in candidates:
                if c in codes:
                    return c
        except Exception:
            pass
        try:
            status = self._device_status(device_id)
            codes = [s.get("code") for s in status if isinstance(s, dict) and isinstance(s.get("value"), bool)]
            for c in candidates:
                if c in codes:
                    return c
            if codes:
                return codes[0]
        except Exception:
            pass
        return "switch"

    def _build_commands(self, mapping: Dict[str, Any]) -> List[dict]:
        return [{"code": k, "value": v} for k, v in mapping.items()]

    def _device_send_commands(self, device_id: str, commands: List[dict]) -> dict:
        payload = {"commands": commands}
        res = self._post_json(f"/v1.0/devices/{device_id}/commands", payload=payload)
        return res

    def _toggle_state(self, device_id: str, code: Optional[str] = None) -> Tuple[str, Optional[bool]]:
        code = code or self._guess_switch_code(device_id)
        status = self._device_status(device_id)
        current = None
        for s in status:
            if s.get("code") == code and isinstance(s.get("value"), bool):
                current = bool(s["value"])
                break
        if current is None:
            for s in status:
                if isinstance(s.get("value"), bool):
                    code = s["code"]
                    current = bool(s["value"])
                    break
        return code, current

    def _normalize_sensors(self, status_list: List[dict]) -> dict:
        res = {"raw": status_list, "normalized": {}}
        idx = {s.get("code"): s.get("value") for s in status_list if isinstance(s, dict) and "code" in s}
        norm = {}

        def deki(v):
            try:
                if isinstance(v, (int, float)):
                    return round(v / 10.0, 1) if abs(v) < 1000 else v
            except Exception:
                pass
            return v

        for c in ["temp_current", "temperature", "temp_value", "va_temperature", "temp_cur"]:
            if c in idx:
                norm["temperature_c"] = deki(idx[c])
                break
        for c in ["humidity_value", "humidity", "va_humidity", "hum_value"]:
            if c in idx:
                norm["humidity_pct"] = deki(idx[c])
                break
        for c in ["co2", "co2_value"]:
            if c in idx:
                norm["co2_ppm"] = idx[c]
                break
        for c in ["pm25", "pm2p5", "pm2_5"]:
            if c in idx:
                norm["pm25_ugm3"] = idx[c]
                break
        for c in ["pm10", "pm_10"]:
            if c in idx:
                norm["pm10_ugm3"] = idx[c]
                break
        for c in ["illumination", "illumination_value", "lux", "bright_value"]:
            if c in idx:
                norm["illuminance_lux"] = idx[c]
                break
        for c in ["battery", "battery_percentage", "battery_state"]:
            if c in idx:
                norm["battery_pct_or_state"] = idx[c]
                break

        res["normalized"] = norm
        return res

    # ---------------------- Commands: Auth ----------------------

    def cmd_tuya_set_keys(self, item: dict) -> dict:
        p = item.get("params", {})
        cid = (p.get("client_id") or "").strip()
        sec = (p.get("client_secret") or "").strip()
        if not cid or not sec:
            return self.make_response(item, "Params 'client_id' and 'client_secret' required")
        self.plugin.set_option_value("tuya_client_id", cid)
        self.plugin.set_option_value("tuya_client_secret", sec)
        return self.make_response(item, {"ok": True})

    def cmd_tuya_set_uid(self, item: dict) -> dict:
        p = item.get("params", {})
        uid = (p.get("uid") or "").strip()
        if not uid:
            return self.make_response(item, "Param 'uid' required")
        self.plugin.set_option_value("tuya_uid", uid)
        return self.make_response(item, {"ok": True})

    def cmd_tuya_token_get(self, item: dict) -> dict:
        res = self._token_get()
        return self.make_response(item, res)

    # ---------------------- Commands: Devices / Info ----------------------

    def cmd_tuya_devices_list(self, item: dict) -> dict:
        p = item.get("params", {})
        uid = self._get_uid(p)
        page_no = int(p.get("page_no") or 1)
        page_size = int(p.get("page_size") or 100)
        params = {"page_no": page_no, "page_size": page_size}
        res = self._get(f"/v1.0/users/{uid}/devices", params=params)
        try:
            devices = (res.get("result") or {}).get("devices") or res.get("result") or []
            self.plugin.set_option_value("tuya_cached_devices", json.dumps(devices, ensure_ascii=False))
        except Exception:
            pass
        return self.make_response(item, res)

    def cmd_tuya_device_get(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        res = self._get(f"/v1.0/devices/{device_id}")
        return self.make_response(item, res)

    def cmd_tuya_device_status(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        res = self._get(f"/v1.0/devices/{device_id}/status")
        return self.make_response(item, res)

    def cmd_tuya_device_functions(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        res = self._get(f"/v1.0/devices/{device_id}/functions")
        return self.make_response(item, res)

    def cmd_tuya_find_device(self, item: dict) -> dict:
        p = item.get("params", {})
        name = (p.get("name") or "").strip().lower()
        if not name:
            return self.make_response(item, "Param 'name' required")
        try:
            cached = self.plugin.get_option_value("tuya_cached_devices") or "[]"
            devices = json.loads(cached)
        except Exception:
            devices = []
        found = []
        for d in devices:
            n = str(d.get("name") or "").lower()
            if name in n:
                found.append(d)
        return self.make_response(item, {"matches": found})

    # ---------------------- Commands: Control ----------------------

    def cmd_tuya_device_set(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        code = p.get("code")
        value = p.get("value")
        codes_map = p.get("codes")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")

        if codes_map and isinstance(codes_map, dict):
            cmds = self._build_commands(codes_map)
        elif code is not None:
            cmds = [{"code": code, "value": value}]
        else:
            return self.make_response(item, "Provide 'code'+'value' or 'codes' dict")

        res = self._device_send_commands(device_id, cmds)
        return self.make_response(item, res)

    def cmd_tuya_device_send(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        commands = p.get("commands")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        if not isinstance(commands, list) or not commands:
            return self.make_response(item, "Param 'commands' must be a non-empty list of {code,value}")
        res = self._device_send_commands(device_id, commands)
        return self.make_response(item, res)

    def cmd_tuya_device_on(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        code = p.get("code")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        code = code or self._guess_switch_code(device_id)
        res = self._device_send_commands(device_id, [{"code": code, "value": True}])
        return self.make_response(item, res)

    def cmd_tuya_device_off(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        code = p.get("code")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        code = code or self._guess_switch_code(device_id)
        res = self._device_send_commands(device_id, [{"code": code, "value": False}])
        return self.make_response(item, res)

    def cmd_tuya_device_toggle(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        code = p.get("code")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        code, current = self._toggle_state(device_id, code=code)
        if current is None:
            return self.make_response(item, f"Unable to determine current state for device '{device_id}'. Provide 'code' or use tuya_device_on/off.")
        res = self._device_send_commands(device_id, [{"code": code, "value": not current}])
        return self.make_response(item, {"toggled": True, "code": code, "from": current, "to": not current, "result": res})

    # ---------------------- Commands: Sensors ----------------------

    def cmd_tuya_sensors_read(self, item: dict) -> dict:
        p = item.get("params", {})
        device_id = p.get("device_id")
        if not device_id:
            return self.make_response(item, "Param 'device_id' required")
        status = self._device_status(device_id)
        norm = self._normalize_sensors(status)
        return self.make_response(item, norm)