#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 05:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Optional, Dict, Any, List

from pygpt_net.item.model import ModelItem


class Remote:
    def __init__(self, window=None):
        """
        Live Search builder for xAI:
        - Returns a dict with 'sdk' (X-only toggle) and 'http' (full search_parameters).
        - SDK path: native streaming (xai_sdk.chat.stream()) works only for basic X search (no advanced filters).
        - HTTP path: full Live Search (web/news/rss/X with filters), streaming via SSE.

        :param window: Window instance
        """
        self.window = window

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

        mode = str(cfg.get("remote_tools.xai.mode") or "auto").lower()
        if mode not in ("auto", "on", "off"):
            mode = "auto"

        if mode == "off":
            if is_web:
                mode = "auto"  # override off if global web_search enabled

        # sources toggles
        s_web = bool(cfg.get("remote_tools.xai.sources.web", True))
        s_x   = bool(cfg.get("remote_tools.xai.sources.x", True))
        s_news = bool(cfg.get("remote_tools.xai.sources.news", False))
        s_rss  = bool(cfg.get("remote_tools.xai.sources.rss", False))

        # advanced flags
        adv_web_allowed   = self._has_list(cfg.get("remote_tools.xai.web.allowed_websites"))
        adv_web_excluded  = self._has_list(cfg.get("remote_tools.xai.web.excluded_websites"))
        adv_web_country   = self._has_str(cfg.get("remote_tools.xai.web.country"))
        adv_web_safe      = cfg.get("remote_tools.xai.web.safe_search", None)

        adv_news_excl     = self._has_list(cfg.get("remote_tools.xai.news.excluded_websites"))
        adv_news_country  = self._has_str(cfg.get("remote_tools.xai.news.country"))
        adv_news_safe     = cfg.get("remote_tools.xai.news.safe_search", None)

        adv_x_incl        = self._has_list(cfg.get("remote_tools.xai.x.included_handles"))
        adv_x_excl        = self._has_list(cfg.get("remote_tools.xai.x.excluded_handles"))
        adv_x_favs        = self._has_int(cfg.get("remote_tools.xai.x.min_favs"))
        adv_x_views       = self._has_int(cfg.get("remote_tools.xai.x.min_views"))

        adv_rss_link      = self._has_str(cfg.get("remote_tools.xai.rss.link"))

        adv_from          = self._has_str(cfg.get("remote_tools.xai.from_date"))
        adv_to            = self._has_str(cfg.get("remote_tools.xai.to_date"))

        adv_max_results   = self._has_int(cfg.get("remote_tools.xai.max_results"))
        adv_return_cits   = cfg.get("remote_tools.xai.return_citations", True) is not True  # different than default?

        # SDK-capable if: mode!=off and ONLY X is enabled and no X filters/date/max_results customizations
        x_only = s_x and not s_web and not s_news and not s_rss
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
            s_web or s_news or s_rss
        )
        if need_http:
            http_params = self._build_http_params(cfg, mode, s_web, s_x, s_news, s_rss)
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
            s_news: bool,
            s_rss: bool
    ) -> dict:
        """
        Build search_parameters for Chat Completions (HTTP).

        :param cfg: Config dict
        :param mode: "auto"|"on"|"off"
        :param s_web: Include web search
        :param s_x: Include X search
        :param s_news: Include news search
        :param s_rss: Include RSS search
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

        if s_news:
            news: Dict[str, Any] = {"type": "news"}
            country = cfg.get("remote_tools.xai.news.country")
            if isinstance(country, str) and len(country.strip()) == 2:
                news["country"] = country.strip().upper()
            excluded = self._as_list(cfg.get("remote_tools.xai.news.excluded_websites"), 5)
            if excluded:
                news["excluded_websites"] = excluded
            safe = cfg.get("remote_tools.xai.news.safe_search")
            if safe is not None:
                news["safe_search"] = bool(safe)
            sources.append(news)

        if s_rss:
            link = cfg.get("remote_tools.xai.rss.link")
            if isinstance(link, str) and link.strip():
                sources.append({"type": "rss", "links": [link.strip()]})

        if sources:
            params["sources"] = sources

        return params

    def _has_list(self, v) -> bool:
        """
        Return True if v is a non-empty list/tuple or a non-empty comma-separated string.

        :param v: Any
        :return: bool
        """
        if v is None:
            return False
        if isinstance(v, (list, tuple)):
            return len([x for x in v if str(x).strip()]) > 0
        return len([x for x in str(v).split(",") if x.strip()]) > 0

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

    def _as_list(self, v, limit: int) -> List[str]:
        """
        Convert v to a list of strings, limited to 'limit' items.

        :param v: Any
        :param limit: limit number of items
        :return: List of strings
        """
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            arr = [str(x).strip() for x in v if str(x).strip()]
        else:
            arr = [s.strip() for s in str(v).split(",") if s.strip()]
        return arr[:limit]