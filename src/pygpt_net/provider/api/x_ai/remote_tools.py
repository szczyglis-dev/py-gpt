#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 18:00:00                  #
# ================================================== #

from __future__ import annotations

import json
from typing import Optional, Dict, Any, List

from pygpt_net.item.model import ModelItem

# xAI server-side tools
try:
    from xai_sdk.tools import web_search as x_web_search
    from xai_sdk.tools import x_search as x_x_search
    from xai_sdk.tools import code_execution as x_code_execution
    from xai_sdk.tools import mcp as x_mcp
    from xai_sdk.tools import collections_search as x_collections_search
except Exception:
    x_web_search = None
    x_x_search = None
    x_code_execution = None
    x_mcp = None


class Remote:
    def __init__(self, window=None):
        """
        Live Search builder for xAI (old, grok-3):
        - Returns a dict with 'sdk' (X-only toggle) and 'http' (full search_parameters).
        - SDK path: native streaming (xai_sdk.chat.stream()) works only for basic X search (no advanced filters).
        - HTTP path: full Live Search (web/news/rss/X with filters), streaming via SSE.

        Server-side Tools builder for xAI (newer SDKs, Responses API):
        - Builds xAI SDK tool objects for web_search, x_search, code_execution, MCP.
        - Returns include flags, max_turns and use_encrypted_content settings.

        :param window: Window instance
        """
        self.window = window

    def build_for_chat(self, model: ModelItem = None, stream: bool = False) -> Dict[str, Any]:
        """
        Build server-side tools and options for Chat Responses.

        Returns:
            {
              "tools": [ ... xai_sdk.tools.* ... ],
              "include": [ ... ],
              "use_encrypted_content": bool,
              "max_turns": Optional[int],
            }
        """
        cfg = self.window.core.config
        include: List[str] = []
        tools: List[object] = []

        # global remote tools switch
        is_web_enabled = self.window.controller.chat.remote_tools.enabled(model, "web_search")
        is_x_enabled = bool(cfg.get("remote_tools.xai.x_search", False))
        is_code_enabled = bool(cfg.get("remote_tools.xai.code_execution", False))
        is_mcp_enabled = bool(cfg.get("remote_tools.xai.mcp", False))

        # include flags
        if stream:
            include.append("verbose_streaming")
        if bool(cfg.get("remote_tools.xai.inline_citations", True)):
            include.append("inline_citations")
        if bool(cfg.get("remote_tools.xai.include_code_output", True)):
            include.append("code_execution_call_output")

        # use_encrypted_content
        use_encrypted = bool(cfg.get("remote_tools.xai.use_encrypted_content", False))

        # optional max_turns
        max_turns = None
        try:
            mt = cfg.get("remote_tools.xai.max_turns")
            if isinstance(mt, int) and mt > 0:
                max_turns = int(mt)
        except Exception:
            pass

        # WEB SEARCH
        if is_web_enabled and x_web_search is not None:
            kwargs: Dict[str, Any] = {}
            enable_img = bool(cfg.get("remote_tools.xai.web.enable_image_understanding", False))
            '''
            allowed = self._as_list(cfg.get("remote_tools.xai.web.allowed_websites"), 5)
            excluded = self._as_list(cfg.get("remote_tools.xai.web.excluded_websites"), 5)
            if allowed and not excluded:
                kwargs["allowed_domains"] = allowed
            elif excluded and not allowed:
                kwargs["excluded_domains"] = excluded
            '''
            if enable_img:
                kwargs["enable_image_understanding"] = True
            try:
                tools.append(x_web_search(**kwargs))
            except Exception:
                tools.append(x_web_search())

        # X SEARCH
        if is_x_enabled and x_x_search is not None:
            kwargs: Dict[str, Any] = {}
            '''
            inc = self._as_list(cfg.get("remote_tools.xai.x.included_handles"), 10)
            exc = self._as_list(cfg.get("remote_tools.xai.x.excluded_handles"), 10)
            if inc and not exc:
                kwargs["allowed_x_handles"] = inc
            elif exc and not inc:
                kwargs["excluded_x_handles"] = exc
            '''
            # optional date range filters (YYYY-MM-DD)
            for k_in, k_out in (("remote_tools.xai.from_date", "from_date"),
                                ("remote_tools.xai.to_date", "to_date")):
                v = cfg.get(k_in)
                if isinstance(v, str) and v.strip():
                    kwargs[k_out] = v.strip()

            if bool(cfg.get("remote_tools.xai.x.enable_image_understanding", False)):
                kwargs["enable_image_understanding"] = True
            if bool(cfg.get("remote_tools.xai.x.enable_video_understanding", False)):
                kwargs["enable_video_understanding"] = True

            # optional favorites/views filters (supported by live search)
            try:
                favs = cfg.get("remote_tools.xai.x.min_favs")
                if isinstance(favs, int) and favs > 0:
                    kwargs["post_favorite_count"] = int(favs)
            except Exception:
                pass
            try:
                views = cfg.get("remote_tools.xai.x.min_views")
                if isinstance(views, int) and views > 0:
                    kwargs["post_view_count"] = int(views)
            except Exception:
                pass

            try:
                tools.append(x_x_search(**kwargs))
            except Exception:
                tools.append(x_x_search())

        # CODE EXECUTION
        if is_code_enabled and x_code_execution is not None:
            try:
                tools.append(x_code_execution())
            except Exception:
                pass

        # MCP
        if is_mcp_enabled and x_mcp is not None:
            kwargs = {}
            mcp_config = cfg.get("remote_tools.xai.mcp.args", "")
            if mcp_config:
                try:
                    kwargs = json.loads(mcp_config)
                except Exception:
                    pass
                try:
                    tools.append(x_mcp(**kwargs))
                except Exception:
                    pass

        # COLLECTIONS SEARCH
        is_collections_enabled = bool(cfg.get("remote_tools.xai.collections", False))
        ids = cfg.get("remote_tools.xai.collections.args", "")
        ids_list = []
        if ids:
            try:
                ids_list = [s.strip() for s in ids.split(",") if s.strip()]
            except Exception:
                pass
        if is_collections_enabled and ids_list:
            try:
                tools.append(x_collections_search(
                    collection_ids=ids_list
                ))
            except Exception:
                pass

        return {
            "tools": tools,
            "include": include,
            "use_encrypted_content": use_encrypted,
            "max_turns": max_turns,
        }

    def build_remote_tools(self, model: ModelItem = None) -> Dict[str, Any]:
        """
        Return live-search config for xAI:
        {
          "mode": ...,
          "sdk": {"enabled": bool},
          "http": Optional[dict],
          "reason": Optional[str],
        }

        :param model: ModelItem (optional, not used now)
        :return: Dict with 'sdk' and 'http' keys
        """
        return self.build(model)

    def build(self, model=None) -> Dict[str, Any]:
        """
        Build both SDK-capable toggle and HTTP search_parameters.
        Returns:
            {
              "mode": "auto"|"on"|"off",
              "sdk": {"enabled": bool},           # True if we can use native SDK stream (X-only no filters)
              "http": Optional[dict],             # search_parameters for Chat Completions (or None)
              "reason": Optional[str],            # diagnostic: why http is needed
            }

        :param model: ModelItem (not used now)
        :return: Dict with 'sdk' and 'http' keys
        """
        cfg = self.window.core.config
        is_web = self.window.controller.chat.remote_tools.enabled(model, "web_search")  # get global config
        mode = "on" if is_web else "off"

        # sources toggles
        s_web =  bool(cfg.get("remote_tools.xai.web_search", False))
        s_x   =  bool(cfg.get("remote_tools.xai.x_search", False))

        adv_x_incl        = self._has_list(cfg.get("remote_tools.xai.x.included_handles"))
        adv_x_excl        = self._has_list(cfg.get("remote_tools.xai.x.excluded_handles"))
        adv_x_favs        = self._has_int(cfg.get("remote_tools.xai.x.min_favs"))
        adv_x_views       = self._has_int(cfg.get("remote_tools.xai.x.min_views"))

        adv_from          = self._has_str(cfg.get("remote_tools.xai.from_date"))
        adv_to            = self._has_str(cfg.get("remote_tools.xai.to_date"))

        adv_max_results   = self._has_int(cfg.get("remote_tools.xai.max_results"))
        adv_return_cits   = cfg.get("remote_tools.xai.return_citations", True) is not True  # different than default?

        # SDK-capable if: mode!=off and ONLY X is enabled and no X filters/date/max_results customizations
        x_only = s_x and not s_web
        x_filters = any([adv_x_incl, adv_x_excl, adv_x_favs, adv_x_views])
        sdk_enabled = (mode != "off") and x_only and not any([
            x_filters, adv_from, adv_to, adv_max_results, adv_return_cits
        ])

        # Build HTTP search_parameters only when needed beyond X-only basic,
        # or when mode explicitly on/auto but SDK cannot represent flags.
        http_params: Optional[dict] = None
        http_reason: Optional[str] = None

        need_http = (mode != "off") and (
            not sdk_enabled or                # advanced X filters or other sources/date/results/citations
            s_web
        )
        if need_http:
            http_params = self._build_http_params(cfg, mode, s_web, s_x)
            http_reason = "advanced_sources_or_filters"

        return {
            "mode": mode,
            "sdk": {"enabled": sdk_enabled},
            "http": http_params,
            "reason": http_reason,
        }

    # ---------- helpers ----------

    def _build_http_params(
            self,
            cfg,
            mode: str,
            s_web: bool,
            s_x: bool,
    ) -> dict:
        """
        Build search_parameters for Chat Completions (HTTP).

        :param cfg: Config dict
        :param mode: "auto"|"on"|"off"
        :param s_web: Include web search
        :param s_x: Include X search
        :return: search_parameters dict
        """
        params: Dict[str, Any] = {"mode": mode}

        rc = cfg.get("remote_tools.xai.return_citations")
        if rc is None:
            rc = True
        params["return_citations"] = bool(rc)

        msr = cfg.get("remote_tools.xai.max_results")
        if isinstance(msr, int) and msr > 0:
            params["max_search_results"] = int(msr)

        for k_cfg, k_out in (("remote_tools.xai.from_date", "from_date"),
                             ("remote_tools.xai.to_date", "to_date")):
            val = cfg.get(k_cfg)
            if isinstance(val, str) and val.strip():
                params[k_out] = val.strip()

        sources: List[Dict[str, Any]] = []

        if s_web:
            web: Dict[str, Any] = {"type": "web"}
            country = cfg.get("remote_tools.xai.web.country")
            if isinstance(country, str) and len(country.strip()) == 2:
                web["country"] = country.strip().upper()
            allowed = self._as_list(cfg.get("remote_tools.xai.web.allowed_websites"), 5)
            excluded = self._as_list(cfg.get("remote_tools.xai.web.excluded_websites"), 5)
            if allowed:
                web["allowed_websites"] = allowed
            elif excluded:
                web["excluded_websites"] = excluded
            safe = cfg.get("remote_tools.xai.web.safe_search")
            if safe is not None:
                web["safe_search"] = bool(safe)
            sources.append(web)

        if s_x:
            xsrc: Dict[str, Any] = {"type": "x"}
            inc = self._as_list(cfg.get("remote_tools.xai.x.included_handles"), 10)
            exc = self._as_list(cfg.get("remote_tools.xai.x.excluded_handles"), 10)
            if inc and not exc:
                xsrc["included_x_handles"] = inc
            elif exc and not inc:
                xsrc["excluded_x_handles"] = exc
            favs = cfg.get("remote_tools.xai.x.min_favs")
            views = cfg.get("remote_tools.xai.x.min_views")
            if isinstance(favs, int) and favs > 0:
                xsrc["post_favorite_count"] = int(favs)
            if isinstance(views, int) and views > 0:
                xsrc["post_view_count"] = int(views)
            sources.append(xsrc)

        if sources:
            params["sources"] = sources

        return params

    # ---------- helpers ----------

    def _has_str(self, v) -> bool:
        """
        Return True if v is a non-empty string.

        :param v: Any
        :return: bool
        """
        return isinstance(v, str) and bool(v.strip())

    def _has_int(self, v) -> bool:
        """
        Return True if v is a positive integer.

        :param v: Any
        :return: true if v is a positive integer
        """
        return isinstance(v, int) and v > 0

    def _has_list(self, v) -> bool:
        if v is None:
            return False
        if isinstance(v, (list, tuple)):
            return len([x for x in v if str(x).strip()]) > 0
        return len([x for x in str(v).split(",") if x.strip()]) > 0

    def _as_list(self, v, limit: int) -> List[str]:
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            arr = [str(x).strip() for x in v if str(x).strip()]
        else:
            arr = [s.strip() for s in str(v).split(",") if s.strip()]
        return arr[:limit]