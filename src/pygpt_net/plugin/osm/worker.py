#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.18 03:25:00                  #
# ================================================== #

from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals

Number = Union[int, float]
LatLon = Tuple[float, float]


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """
    OpenStreetMap plugin worker:
    - Geocoding (forward/reverse) via Nominatim
    - Search (alias of geocode)
    - Routing via OSRM (driving/walking/cycling), lightweight by default
    - "Static map": returns openstreetmap.org URL (center/zoom or bbox + optional marker)
    - Utility: OSM site URL, directions URL, single XYZ tile download
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

                        if item["cmd"] == "osm_geocode":
                            response = self.cmd_osm_geocode(item)
                        elif item["cmd"] == "osm_reverse":
                            response = self.cmd_osm_reverse(item)
                        elif item["cmd"] == "osm_search":
                            response = self.cmd_osm_search(item)
                        elif item["cmd"] == "osm_route":
                            response = self.cmd_osm_route(item)
                        elif item["cmd"] == "osm_staticmap":
                            response = self.cmd_osm_staticmap(item)
                        elif item["cmd"] == "osm_bbox_map":
                            response = self.cmd_osm_bbox_map(item)
                        elif item["cmd"] == "osm_show_url":
                            response = self.cmd_osm_show_url(item)
                        elif item["cmd"] == "osm_route_url":
                            response = self.cmd_osm_route_url(item)
                        elif item["cmd"] == "osm_tile":
                            response = self.cmd_osm_tile(item)

                        if response is not None:
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

    # ---------------------- HTTP / Config helpers ----------------------

    def _timeout(self) -> int:
        try:
            return int(self.plugin.get_option_value("http_timeout") or 30)
        except Exception:
            return 30

    def _headers(self) -> Dict[str, str]:
        ua = (self.plugin.get_option_value("user_agent") or "").strip()
        if not ua:
            ua = "pygpt-net-osm-plugin/1.0 (+https://pygpt.net)"
        return {
            "User-Agent": ua,
            "Accept": "*/*",
        }

    def _nominatim_base(self) -> str:
        return (self.plugin.get_option_value("nominatim_base") or "https://nominatim.openstreetmap.org").rstrip("/")

    def _osrm_base(self) -> str:
        return (self.plugin.get_option_value("osrm_base") or "https://router.project-osrm.org").rstrip("/")

    def _tile_base(self) -> str:
        return (self.plugin.get_option_value("tile_base") or "https://tile.openstreetmap.org").rstrip("/")

    def _nominatim_common_params(self) -> Dict[str, Any]:
        p = {"format": "jsonv2"}
        email = (self.plugin.get_option_value("contact_email") or "").strip()
        if email:
            p["email"] = email
        lang = (self.plugin.get_option_value("accept_language") or "").strip()
        if lang:
            p["accept-language"] = lang
        return p

    # ---------------------- File / util helpers ----------------------

    def _save_bytes(self, data: bytes, out_path: str) -> str:
        local = self.prepare_path(out_path)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as fh:
            fh.write(data)
        return local

    def prepare_path(self, path: str) -> str:
        if path in [".", "./"]:
            return self.plugin.window.core.config.get_user_dir("data")
        if self.is_absolute_path(path):
            return path
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), path)

    def is_absolute_path(self, path: str) -> bool:
        return os.path.isabs(path)

    def _slug(self, s: str, maxlen: int = 80) -> str:
        s = re.sub(r"\s+", "_", (s or "").strip())
        s = re.sub(r"[^a-zA-Z0-9_\-\.]", "", s)
        return (s[:maxlen] or "map").strip("._-") or "map"

    def _now(self) -> int:
        return int(time.time())

    def _add_image(self, path: str):
        try:
            if self.ctx is None:
                return
            if path:
                path = self.plugin.window.core.filesystem.to_workdir(path)
            if not hasattr(self.ctx, "images_before") or self.ctx.images_before is None:
                self.ctx.images_before = []
            if path and path not in self.ctx.images_before:
                self.ctx.images_before.append(path)
        except Exception:
            pass

    # ---------------------- Internal helpers ----------------------

    def _call_cmd(self, cmd: str, params: dict) -> dict:
        fn = getattr(self, f"cmd_{cmd}", None)
        if not callable(fn):
            raise RuntimeError(f"Unknown command: {cmd}")
        return fn({"cmd": cmd, "params": params})

    def _get_payload(self, resp: Any) -> Any:
        if isinstance(resp, dict):
            if resp.get("data") is not None:
                return resp["data"]
            if resp.get("result") is not None:
                return resp["result"]
        return resp

    # ---------------------- Geo helpers ----------------------

    def _is_number(self, x: Any) -> bool:
        try:
            float(x)
            return True
        except Exception:
            return False

    def _parse_point(self, v: Any) -> Optional[LatLon]:
        if v is None:
            return None
        if isinstance(v, (list, tuple)) and len(v) >= 2 and self._is_number(v[0]) and self._is_number(v[1]):
            return float(v[0]), float(v[1])
        if isinstance(v, dict) and "lat" in v and "lon" in v and self._is_number(v["lat"]) and self._is_number(v["lon"]):
            return float(v["lat"]), float(v["lon"])
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",")]
            if len(parts) >= 2 and self._is_number(parts[0]) and self._is_number(parts[1]):
                return float(parts[0]), float(parts[1])
        return None

    def _validate_latlon(self, lat: float, lon: float) -> Tuple[float, float]:
        if not (math.isfinite(lat) and math.isfinite(lon)):
            raise ValueError("Non-finite coordinate")
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError("Coordinate out of range")
        return float(lat), float(lon)

    def _resolve_point(self, v: Any) -> LatLon:
        pt = self._parse_point(v)
        if pt:
            return self._validate_latlon(pt[0], pt[1])
        q = str(v).strip()
        res = self._nominatim_search({"q": q, "limit": 1})
        if res:
            lat = float(res[0]["lat"])
            lon = float(res[0]["lon"])
            return self._validate_latlon(lat, lon)
        raise RuntimeError(f"Unable to resolve location: {v}")

    def _bbox_from_radius(self, lat: float, lon: float, radius_m: float) -> Tuple[float, float, float, float]:
        dlat = radius_m / 111320.0
        dlon = radius_m / (111320.0 * max(math.cos(math.radians(lat)), 1e-6))
        return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)

    def _bbox_from_coords(self, coords: List[LatLon]) -> Tuple[float, float, float, float]:
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        return (min(lons), min(lats), max(lons), max(lats))

    # ---------------------- OSM site URL helpers ----------------------

    def _clamp(self, x: float, a: float, b: float) -> float:
        return max(a, min(b, x))

    def _lat_to_yn(self, lat: float) -> float:
        lat = self._clamp(lat, -85.05112878, 85.05112878)
        rad = math.radians(lat)
        y = math.log(math.tan(math.pi / 4.0 + rad / 2.0))
        return (1.0 - y / math.pi) / 2.0

    def _estimate_zoom_for_bbox(self, minlon: float, minlat: float, maxlon: float, maxlat: float,
                                width: int, height: int) -> int:
        dlon = max(1e-9, maxlon - minlon)
        z_lon = math.log2((width * 360.0) / (256.0 * dlon))
        y1 = self._lat_to_yn(minlat)
        y2 = self._lat_to_yn(maxlat)
        dy = max(1e-12, abs(y2 - y1))
        z_lat = math.log2(height / (256.0 * dy))
        z = int(max(0, min(20, math.floor(min(z_lon, z_lat)) - 1)))
        return z

    def _osm_site_url(self, lat: float, lon: float,
                      zoom: int | None = None,
                      marker: bool = True,
                      layers: str | None = None) -> str:
        z = zoom if zoom is not None else int(self.plugin.get_option_value("map_zoom") or 14)
        z = max(0, min(20, int(z)))
        base = "https://www.openstreetmap.org/"
        qparts = []
        if marker:
            qparts.append(f"mlat={lat:.6f}")
            qparts.append(f"mlon={lon:.6f}")
        if layers:
            qparts.append(f"layers={layers}")
        url = base
        if qparts:
            url += "?" + "&".join(qparts)
        url += f"#map={z}/{lat:.6f}/{lon:.6f}"
        return url

    def _directions_url(self, start: LatLon, end: LatLon, mode: str | None = "car") -> str:
        mode = (mode or "car").lower()
        if mode in ("driving", "car"):
            engine = "fossgis_osrm_car"
        elif mode in ("cycling", "bike", "bicycle"):
            engine = "fossgis_osrm_bike"
        else:
            engine = "fossgis_osrm_foot"
        return f"https://www.openstreetmap.org/directions?engine={engine}&route={start[0]:.6f},{start[1]:.6f};{end[0]:.6f},{end[1]:.6f}"

    def _directions_url_coords(self, coords: List[LatLon], mode: str | None = "car") -> str:
        mode = (mode or "car").lower()
        if mode in ("driving", "car"):
            engine = "fossgis_osrm_car"
        elif mode in ("cycling", "bike", "bicycle"):
            engine = "fossgis_osrm_bike"
        else:
            engine = "fossgis_osrm_foot"
        # route expects 'lat,lon;lat,lon;...' (note: OSM site, not OSRM API order)
        parts = [f"{c[0]:.6f},{c[1]:.6f}" for c in coords]
        return f"https://www.openstreetmap.org/directions?engine={engine}&route=" + ";".join(parts)

    # ---------------------- Nominatim wrappers ----------------------

    def _nominatim_search(self, params: Dict[str, Any]) -> List[dict]:
        base = self._nominatim_base()
        p = self._nominatim_common_params()
        p.update(params or {})
        url = f"{base}/search"
        r = requests.get(url, headers=self._headers(), params=p, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"Nominatim search HTTP {r.status_code}: {r.text[:200]}")
        try:
            data = r.json() or []
        except Exception:
            data = []
        return data if isinstance(data, list) else []

    def _nominatim_reverse(self, lat: float, lon: float, params: Dict[str, Any]) -> dict:
        base = self._nominatim_base()
        p = self._nominatim_common_params()
        p.update({"lat": lat, "lon": lon})
        p.update(params or {})
        url = f"{base}/reverse"
        r = requests.get(url, headers=self._headers(), params=p, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"Nominatim reverse HTTP {r.status_code}: {r.text[:200]}")
        try:
            data = r.json() or {}
        except Exception:
            data = {}
        return data if isinstance(data, dict) else {"data": data}

    # ---------------------- OSRM wrapper ----------------------

    def _osrm_route(self, coords: List[LatLon], profile: str = "driving", opts: Optional[Dict[str, Any]] = None) -> dict:
        if not coords or len(coords) < 2:
            raise RuntimeError("At least 2 coordinates required for routing")

        norm: List[str] = []
        for (lat, lon) in coords:
            lat, lon = self._validate_latlon(lat, lon)
            norm.append(f"{lon:.6f},{lat:.6f}")
        coord_str = ";".join(norm)

        base = self._osrm_base()
        profile = (profile or "driving").lower()
        url = f"{base}/route/v1/{profile}/{coord_str}"

        steps_bool = bool((opts or {}).get("steps", False))
        alternatives_raw = (opts or {}).get("alternatives", 0)
        try:
            alternatives_bool = bool(int(alternatives_raw))
        except Exception:
            alternatives_bool = bool(alternatives_raw)

        params = {
            "overview": (opts or {}).get("overview", "false"),
            "geometries": (opts or {}).get("geometries", "polyline6"),
            "steps": "true" if steps_bool else "false",
            "alternatives": "true" if alternatives_bool else "false",
            "annotations": "false",
        }

        r = requests.get(url, headers=self._headers(), params=params, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"OSRM route HTTP {r.status_code}: {r.text[:200]}")

        data = r.json()
        if (data or {}).get("code") != "Ok":
            raise RuntimeError(f"OSRM error: {(data or {}).get('message') or data}")
        data["_request_url"] = r.request.url
        return data

    # ---------------------- Commands ----------------------

    def cmd_osm_geocode(self, item: dict) -> dict:
        p = item.get("params", {})
        q = p.get("query") or p.get("q")
        if not q:
            return self.make_response(item, "Param 'query' required")

        params: Dict[str, Any] = {"q": q}
        if p.get("limit") is not None:
            params["limit"] = int(p["limit"])
        if p.get("countrycodes"):
            params["countrycodes"] = p["countrycodes"]
        if p.get("viewbox"):
            vb = p["viewbox"]
            if isinstance(vb, (list, tuple)) and len(vb) >= 4:
                params["viewbox"] = ",".join(str(x) for x in vb[:4])
            elif isinstance(vb, str):
                params["viewbox"] = vb
            if p.get("bounded") is not None:
                params["bounded"] = 1 if p.get("bounded") else 0
        if p.get("addressdetails") is not None:
            params["addressdetails"] = 1 if p.get("addressdetails") else 0
        if p.get("polygon_geojson"):
            params["polygon_geojson"] = 1

        if p.get("near") or (p.get("near_lat") is not None and p.get("near_lon") is not None):
            try:
                near = p.get("near") or {"lat": p.get("near_lat"), "lon": p.get("near_lon")}
                latn, lonn = self._resolve_point(near)
                radius = float(p.get("radius_m") or 1000.0)
                minlon, minlat, maxlon, maxlat = self._bbox_from_radius(latn, lonn, radius)
                params["viewbox"] = f"{minlon},{minlat},{maxlon},{maxlat}"
                if p.get("bounded") is not None:
                    params["bounded"] = 1 if p.get("bounded") else 0
            except Exception:
                pass

        try:
            results = self._nominatim_search(params)

            norm = []
            zoom_for_url = int(p.get("zoom") or self.plugin.get_option_value("map_zoom") or 14)
            layers = p.get("layers")
            for r in results:
                latf = float(r.get("lat")) if r.get("lat") else None
                lonf = float(r.get("lon")) if r.get("lon") else None
                item_res = {
                    "display_name": r.get("display_name"),
                    "lat": latf,
                    "lon": lonf,
                    "boundingbox": r.get("boundingbox"),
                    "type": r.get("type"),
                    "class": r.get("class"),
                    "importance": r.get("importance"),
                    "osm_id": r.get("osm_id"),
                    "osm_type": r.get("osm_type"),
                    "_raw": r,
                }
                if (latf is not None) and (lonf is not None):
                    item_res["map_url"] = self._osm_site_url(latf, lonf, zoom_for_url, marker=True, layers=layers)
                norm.append(item_res)
            return self.make_response(item, {"query": q, "count": len(norm), "results": norm})
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    def cmd_osm_reverse(self, item: dict) -> dict:
        p = item.get("params", {})
        lat = p.get("lat")
        lon = p.get("lon")
        pt = self._parse_point([lat, lon]) if (lat is not None and lon is not None) else self._parse_point(p.get("point"))
        if not pt:
            return self.make_response(item, "Params 'lat' and 'lon' or 'point' required")
        lat, lon = pt
        params: Dict[str, Any] = {}
        if p.get("zoom") is not None:
            params["zoom"] = int(p["zoom"])
        if p.get("addressdetails") is not None:
            params["addressdetails"] = 1 if p.get("addressdetails") else 0
        try:
            data = self._nominatim_reverse(lat, lon, params)
            res = {
                "lat": lat, "lon": lon,
                "display_name": data.get("display_name"),
                "boundingbox": data.get("boundingbox"),
                "address": data.get("address"),
                "_raw": data,
            }
            zoom_for_url = int(p.get("zoom") or self.plugin.get_option_value("map_zoom") or 14)
            layers = p.get("layers")
            res["map_url"] = self._osm_site_url(lat, lon, zoom_for_url, marker=True, layers=layers)
            return self.make_response(item, res)
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    def cmd_osm_search(self, item: dict) -> dict:
        return self._call_cmd("osm_geocode", item.get("params", {}))

    def cmd_osm_route(self, item: dict) -> dict:
        """
        Modes:
          - mode="url": no OSRM call; returns only directions URL + waypoints.
          - mode="summary" (default): OSRM with overview=false, steps=false; returns distance/duration + directions URL.
          - mode="full": OSRM with overview=simplified, geometries=polyline6; optionally include geometry if include_geometry=True.
        """
        p = item.get("params", {})
        try:
            start = self._resolve_point(p.get("start") or [p.get("start_lat"), p.get("start_lon")])
            end = self._resolve_point(p.get("end") or [p.get("end_lat"), p.get("end_lon")])
        except Exception:
            return self.make_response(item, "Params 'start' and 'end' required (address or lat,lon)")

        # Build coords list with optional waypoints
        waypoints_in = p.get("waypoints") or []
        coords: List[LatLon] = [start]
        for w in waypoints_in:
            try:
                coords.append(self._resolve_point(w))
            except Exception:
                continue
        coords.append(end)

        profile = (p.get("profile") or "driving").lower()
        mode = (p.get("mode") or "summary").lower()

        directions_url = self._directions_url_coords(coords, mode=profile)

        result: Dict[str, Any] = {
            "profile": profile,
            "waypoints": [{"lat": c[0], "lon": c[1]} for c in coords],
            "map_url": directions_url,
            "directions_url": directions_url,
        }

        if mode == "url":
            return self.make_response(item, result)

        include_geometry = bool(p.get("include_geometry") or (mode == "full"))
        include_steps = bool(p.get("include_steps") and mode == "full")
        alternatives = p.get("alternatives") or 0

        opts = {
            "overview": "simplified" if include_geometry else "false",
            "geometries": "polyline6",
            "steps": include_steps,
            "alternatives": alternatives,
        }

        try:
            data = self._osrm_route(coords, profile, opts)
            route = (data.get("routes") or [{}])[0]
            result["distance_m"] = route.get("distance")
            result["duration_s"] = route.get("duration")

            if include_geometry and "geometry" in route:
                max_chars = int(p.get("max_polyline_chars") or 5000)
                geom = route.get("geometry")
                if isinstance(geom, str) and len(geom) > max_chars:
                    geom = geom[:max_chars] + "...(truncated)"
                result["geometry_polyline6"] = geom

            if p.get("save_map") or p.get("want_url"):
                preview_bbox = None
                if isinstance(route.get("geometry"), dict) and route["geometry"].get("type") == "LineString":
                    coords_geo: List[LatLon] = [(float(lat), float(lon)) for lon, lat in route["geometry"].get("coordinates", [])]
                    if coords_geo:
                        minlon, minlat, maxlon, maxlat = self._bbox_from_coords(coords_geo)
                        preview_bbox = [minlon, minlat, maxlon, maxlat]

                sm = self._call_cmd("osm_staticmap", {
                    "bbox": preview_bbox,
                    "center": {"lat": start[0], "lon": start[1]} if not preview_bbox else None,
                    "zoom": p.get("zoom"),
                    "markers": [{"lat": start[0], "lon": start[1]}],
                    "layers": p.get("layers"),
                    "width": int(p.get("width") or self._map_width_default()),
                    "height": int(p.get("height") or self._map_height_default()),
                })
                smd = self._get_payload(sm)
                if isinstance(smd, dict) and smd.get("ok") and smd.get("url"):
                    result["preview_url"] = smd["url"]

            if p.get("debug_url"):
                result["osrm_request_url"] = data.get("_request_url")

            return self.make_response(item, result)
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    def _map_width_default(self) -> int:
        try:
            return int(self.plugin.get_option_value("map_width") or 800)
        except Exception:
            return 800

    def _map_height_default(self) -> int:
        try:
            return int(self.plugin.get_option_value("map_height") or 600)
        except Exception:
            return 600

    def cmd_osm_staticmap(self, item: dict) -> dict:
        """
        Build an openstreetmap.org URL instead of downloading a static image.
        Supports center/zoom or bbox. Uses the first marker (if any) to set ?mlat/mlon.
        """
        p = item.get("params", {})

        width = int(p.get("width") or self._map_width_default())
        height = int(p.get("height") or self._map_height_default())

        center_pt = None
        zoom = None

        if p.get("bbox"):
            vb = p["bbox"]
            try:
                if isinstance(vb, (list, tuple)) and len(vb) >= 4:
                    minlon, minlat, maxlon, maxlat = map(float, vb[:4])
                elif isinstance(vb, str):
                    parts = [float(x) for x in vb.split(",")]
                    minlon, minlat, maxlon, maxlat = parts[:4]
                else:
                    return self.make_response(item, "Invalid 'bbox' format")

                clat = (minlat + maxlat) / 2.0
                clon = (minlon + maxlon) / 2.0
                center_pt = (clat, clon)
                zoom = int(p.get("zoom")) if p.get("zoom") is not None else self._estimate_zoom_for_bbox(
                    minlon, minlat, maxlon, maxlat, width, height
                )
            except Exception:
                return self.make_response(item, "Invalid 'bbox' format")

        if center_pt is None:
            if p.get("center"):
                center_pt = self._resolve_point(p.get("center"))
            elif (p.get("lat") is not None) and (p.get("lon") is not None):
                center_pt = (float(p.get("lat")), float(p.get("lon")))
        if zoom is None:
            z = p.get("zoom")
            zoom = int(z) if z is not None else int(self.plugin.get_option_value("map_zoom") or 14)

        if center_pt is None:
            mpt = None
            markers = p.get("markers") or []
            if isinstance(markers, (list, tuple)) and markers:
                for m in markers:
                    mpt = self._parse_point(m)
                    if mpt:
                        break
            elif isinstance(markers, str):
                mpt = self._parse_point(markers)
            if mpt:
                center_pt = mpt
            else:
                return self.make_response(item, "Param 'center' or 'lat'/'lon' or 'bbox' required")

        lat, lon = center_pt

        mlat = None
        mlon = None
        markers = p.get("markers") or []
        if isinstance(markers, (list, tuple)) and markers:
            for m in markers:
                mpt = self._parse_point(m)
                if mpt:
                    mlat, mlon = mpt[0], mpt[1]
                    break
        elif isinstance(markers, str):
            mpt = self._parse_point(markers)
            if mpt:
                mlat, mlon = mpt[0], mpt[1]
        elif p.get("marker"):
            mlat, mlon = lat, lon

        layers = p.get("layers")
        qparts = []
        if mlat is not None and mlon is not None:
            qparts.append(f"mlat={mlat:.6f}")
            qparts.append(f"mlon={mlon:.6f}")
        if layers:
            qparts.append(f"layers={layers}")

        base = "https://www.openstreetmap.org/"
        url = base
        if qparts:
            url += "?" + "&".join(qparts)
        url += f"#map={int(zoom)}/{lat:.6f}/{lon:.6f}"

        return self.make_response(item, {
            "ok": True,
            "url": url,
            "center": {"lat": lat, "lon": lon},
            "zoom": int(zoom),
            "marker": {"lat": mlat, "lon": mlon} if (mlat is not None and mlon is not None) else None,
            "service": "openstreetmap.org",
        })

    def cmd_osm_bbox_map(self, item: dict) -> dict:
        p = item.get("params", {})
        if not p.get("bbox"):
            return self.make_response(item, "Param 'bbox' required (minlon,minlat,maxlon,maxlat)")
        return self._call_cmd("osm_staticmap", p)

    def cmd_osm_show_url(self, item: dict) -> dict:
        p = item.get("params", {})
        pt = self._parse_point(p.get("point") or [p.get("lat"), p.get("lon")])
        if not pt:
            return self.make_response(item, "Param 'point' or 'lat'+'lon' required")
        lat, lon = pt
        zoom = int(p.get("zoom") or self.plugin.get_option_value("map_zoom") or 15)
        url = self._osm_site_url(lat, lon, zoom=zoom, marker=True, layers=p.get("layers"))
        return self.make_response(item, {"url": url, "lat": lat, "lon": lon, "zoom": zoom})

    def cmd_osm_route_url(self, item: dict) -> dict:
        p = item.get("params", {})
        try:
            start = self._resolve_point(p.get("start") or [p.get("start_lat"), p.get("start_lon")])
            end = self._resolve_point(p.get("end") or [p.get("end_lat"), p.get("end_lon")])
        except Exception:
            return self.make_response(item, "Params 'start' and 'end' required (address or lat,lon)")
        url = self._directions_url(start, end, mode=(p.get("mode") or p.get("profile") or "car"))
        return self.make_response(item, {"url": url})

    def cmd_osm_tile(self, item: dict) -> dict:
        p = item.get("params", {})
        try:
            z = int(p.get("z"))
            x = int(p.get("x"))
            y = int(p.get("y"))
        except Exception:
            return self.make_response(item, "Params 'z','x','y' required (tile indices)")
        url = f"{self._tile_base()}/{z}/{x}/{y}.png"
        r = requests.get(url, headers=self._headers(), timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            return self.make_response(item, {"ok": False, "status": r.status_code, "error": r.text})
        out = p.get("out") or os.path.join("openstreetmap", f"tile_{z}_{x}_{y}.png")
        local = self._save_bytes(r.content, out)
        self._add_image(local)
        return self.make_response(item, {"ok": True, "file": local, "url": url})