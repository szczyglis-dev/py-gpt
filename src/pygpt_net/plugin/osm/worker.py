#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.18 00:37:10                  #
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
    - Search (Nominatim, with optional near/bbox)
    - Routing via OSRM (driving/walking/cycling)
    - Static map generation via staticmap.openstreetmap.de (markers/paths/bbox)
    - Utility: show URL on openstreetmap.org, download single tile
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
                        elif item["cmd"] == "osm_show_url":
                            response = self.cmd_osm_show_url(item)
                        elif item["cmd"] == "osm_route_url":
                            response = self.cmd_osm_route_url(item)
                        elif item["cmd"] == "osm_tile":
                            response = self.cmd_osm_tile(item)
                        elif item["cmd"] == "osm_bbox_map":
                            response = self.cmd_osm_bbox_map(item)

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
        # Nominatim requires a proper UA and (ideally) a contact address
        return {
            "User-Agent": ua,
            "Accept": "*/*",
        }

    def _nominatim_base(self) -> str:
        return (self.plugin.get_option_value("nominatim_base") or "https://nominatim.openstreetmap.org").rstrip("/")

    def _osrm_base(self) -> str:
        return (self.plugin.get_option_value("osrm_base") or "https://router.project-osrm.org").rstrip("/")

    def _static_base(self) -> str:
        return (self.plugin.get_option_value("staticmap_base") or "https://staticmap.openstreetmap.de").rstrip("/")

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

    # ---------------------- Geo helpers ----------------------

    def _is_number(self, x: Any) -> bool:
        try:
            float(x)
            return True
        except Exception:
            return False

    def _parse_point(self, v: Any) -> Optional[LatLon]:
        """Accepts 'lat,lon' string, [lat,lon], {'lat':..,'lon':..}, or tuple."""
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

    def _resolve_point(self, v: Any) -> LatLon:
        """Parse lat/lon or geocode if string address."""
        pt = self._parse_point(v)
        if pt:
            return pt
        # Try geocoding single-line address
        q = str(v).strip()
        res = self._nominatim_search({"q": q, "limit": 1})
        if res:
            return float(res[0]["lat"]), float(res[0]["lon"])
        raise RuntimeError(f"Unable to resolve location: {v}")

    def _bbox_from_radius(self, lat: float, lon: float, radius_m: float) -> Tuple[float, float, float, float]:
        # crude approx; good enough for search viewboxes
        dlat = radius_m / 111320.0
        dlon = radius_m / (111320.0 * max(math.cos(math.radians(lat)), 1e-6))
        return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)  # (minlon, minlat, maxlon, maxlat)

    def _bbox_from_coords(self, coords: List[LatLon]) -> Tuple[float, float, float, float]:
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        return (min(lons), min(lats), max(lons), max(lats))

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
        # OSRM expects lon,lat order
        coord_str = ";".join([f"{c[1]:.6f},{c[0]:.6f}" for c in coords])
        base = self._osrm_base()
        profile = (profile or "driving").lower()
        url = f"{base}/route/v1/{profile}/{coord_str}"

        params = {
            "overview": (opts or {}).get("overview", "full"),
            "geometries": (opts or {}).get("geometries", "geojson"),
            "steps": 1 if (opts or {}).get("steps", True) else 0,
            "alternatives": int((opts or {}).get("alternatives", 0)),
            "annotations": "false",
        }
        r = requests.get(url, headers=self._headers(), params=params, timeout=self._timeout())
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"OSRM route HTTP {r.status_code}: {r.text[:200]}")

        data = r.json()
        if (data or {}).get("code") != "Ok":
            raise RuntimeError(f"OSRM error: {(data or {}).get('message') or data}")
        return data

    # ---------------------- Static map helpers ----------------------

    def _encode_marker(self, m: Any) -> Optional[str]:
        """
        Accept marker like:
        - "lat,lon" or "lat,lon,red"
        - [lat,lon], {"lat":..,"lon":..,"color":"red","label":"A"}
        Returns string for staticmap.de markers param.
        """
        if isinstance(m, str):
            # Keep as-is if looks like 'lat,lon' or 'lat,lon,color'
            parts = [p.strip() for p in m.split(",")]
            if len(parts) >= 2 and self._is_number(parts[0]) and self._is_number(parts[1]):
                return ",".join(parts[:3])  # drop extras beyond color
            return None
        pt = self._parse_point(m)
        if not pt:
            return None
        lat, lon = pt
        color = None
        label = None
        if isinstance(m, dict):
            color = (m.get("color") or "").strip() or None  # e.g., red|blue|green|lightblue1
            label = (m.get("label") or "").strip() or None  # some styles support letter
        if color and label:
            return f"{lat:.6f},{lon:.6f},{color}-{label}"
        if color:
            return f"{lat:.6f},{lon:.6f},{color}"
        return f"{lat:.6f},{lon:.6f}"

    def _encode_path(self, points: List[Any], color: Optional[str] = None, weight: Optional[int] = None) -> Optional[str]:
        """
        Encode a single path for staticmap.de: "path=weight:3|color:blue|lat,lon|lat,lon|..."
        """
        coords: List[LatLon] = []
        for p in points or []:
            pt = self._parse_point(p)
            if pt:
                coords.append(pt)
        if len(coords) < 2:
            return None
        segs = []
        if weight:
            segs.append(f"weight:{int(weight)}")
        if color:
            segs.append(f"color:{color}")
        # append coordinates
        for (lat, lon) in coords:
            segs.append(f"{lat:.6f},{lon:.6f}")
        return "|".join(segs) if segs else None

    def _static_bases(self) -> List[str]:
        # user-configured first
        bases = [self._static_base()]
        # known public fallbacks (same API)
        for b in ("https://staticmap.openstreetmap.fr/staticmap", "https://staticmap.osm.ch"):
            if b not in bases:
                bases.append(b)
        return bases

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
            # expect "minlon,minlat,maxlon,maxlat" or list
            vb = p["viewbox"]
            if isinstance(vb, (list, tuple)) and len(vb) >= 4:
                params["viewbox"] = ",".join(str(x) for x in vb[:4])
            elif isinstance(vb, str):
                params["viewbox"] = vb
            params["bounded"] = 1 if p.get("bounded", True) else 0
        if p.get("addressdetails") is not None:
            params["addressdetails"] = 1 if p.get("addressdetails") else 0
        if p.get("polygon_geojson"):
            params["polygon_geojson"] = 1

        # Optional 'near' shortcut to build a viewbox around a point
        if p.get("near") or (p.get("near_lat") is not None and p.get("near_lon") is not None):
            try:
                near = p.get("near") or {"lat": p.get("near_lat"), "lon": p.get("near_lon")}
                lat, lon = self._resolve_point(near)
                radius = float(p.get("radius_m") or 1000.0)
                minlon, minlat, maxlon, maxlat = self._bbox_from_radius(lat, lon, radius)
                params["viewbox"] = f"{minlon},{minlat},{maxlon},{maxlat}"
                # Only restrict if user explicitly asked for bounded
                if p.get("bounded") is not None:
                    params["bounded"] = 1 if p.get("bounded") else 0
            except Exception:
                pass

        try:
            results = self._nominatim_search(params)
            # normalize essential fields
            norm = []
            for r in results:
                norm.append({
                    "display_name": r.get("display_name"),
                    "lat": float(r.get("lat")) if r.get("lat") else None,
                    "lon": float(r.get("lon")) if r.get("lon") else None,
                    "boundingbox": r.get("boundingbox"),
                    "type": r.get("type"),
                    "class": r.get("class"),
                    "importance": r.get("importance"),
                    "osm_id": r.get("osm_id"),
                    "osm_type": r.get("osm_type"),
                    "_raw": r,
                })
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
            # Flatten essential fields
            res = {
                "lat": lat, "lon": lon,
                "display_name": data.get("display_name"),
                "boundingbox": data.get("boundingbox"),
                "address": data.get("address"),
                "_raw": data,
            }
            return self.make_response(item, res)
        except Exception as e:
            return self.make_response(item, self.throw_error(e))

    def cmd_osm_search(self, item: dict) -> dict:
        # Alias to geocode with same params; kept separate for UX symmetry
        item2 = {"cmd": "osm_geocode", "params": item.get("params", {})}
        return self.cmd_osm_geocode(item2)

    def cmd_osm_route(self, item: dict) -> dict:
        p = item.get("params", {})
        # Accept start/end as address or lat,lon; optional waypoints
        try:
            start = self._resolve_point(p.get("start") or [p.get("start_lat"), p.get("start_lon")])
            end = self._resolve_point(p.get("end") or [p.get("end_lat"), p.get("end_lon")])
        except Exception:
            return self.make_response(item, "Params 'start' and 'end' required (address or lat,lon)")

        waypoints_in = p.get("waypoints") or []
        coords: List[LatLon] = [start]
        for w in waypoints_in:
            try:
                coords.append(self._resolve_point(w))
            except Exception:
                continue
        coords.append(end)

        profile = (p.get("profile") or "driving").lower()  # driving|walking|cycling
        opts = {
            "overview": p.get("overview") or "full",
            "geometries": p.get("geometries") or "geojson",
            "steps": bool(p.get("steps", True)),
            "alternatives": int(p.get("alternatives") or 0),
        }
        try:
            data = self._osrm_route(coords, profile, opts)
            route = (data.get("routes") or [{}])[0]
            distance_m = route.get("distance")
            duration_s = route.get("duration")
            geometry = (route.get("geometry") or {})
            coords_geo = []
            # geometry for geojson is {"type":"LineString","coordinates":[[lon,lat],...]}
            if (geometry or {}).get("type") == "LineString":
                coords_geo = [(float(lat), float(lon)) for lon, lat in geometry.get("coordinates", [])]
            elif isinstance(geometry, dict) and "coordinates" in geometry:
                # still try to parse
                coords_geo = [(float(lat), float(lon)) for lon, lat in geometry.get("coordinates", [])]

            result = {
                "profile": profile,
                "distance_m": distance_m,
                "duration_s": duration_s,
                "waypoints": [{"lat": c[0], "lon": c[1]} for c in coords],
                "geometry": geometry,
                "_raw": data,
            }

            # Optional: create a static map preview with path + start/end markers
            if p.get("save_map") or p.get("out"):
                markers = p.get("markers") or []
                # Ensure start/end markers exist unless user overrides
                if not markers:
                    markers = [
                        {"lat": start[0], "lon": start[1], "color": "green", "label": "S"},
                        {"lat": end[0], "lon": end[1], "color": "red", "label": "E"},
                    ]
                out = p.get("out") or os.path.join("openstreetmap", f"osm_route_{self._now()}.png")
                # Build bbox from route to fit nicely
                bbox = None
                if coords_geo:
                    minlon, minlat, maxlon, maxlat = self._bbox_from_coords(coords_geo)
                    bbox = [minlon, minlat, maxlon, maxlat]
                sm = self._call_cmd("osm_staticmap", {
                    "bbox": bbox,
                    "markers": markers,
                    "path": coords_geo if coords_geo else [{"lat": start[0], "lon": start[1]}, {"lat": end[0], "lon": end[1]}],
                    "weight": int(p.get("weight") or 4),
                    "color": p.get("color") or "blue",
                    "width": int(p.get("width") or self._map_width_default()),
                    "height": int(p.get("height") or self._map_height_default()),
                    "out": out,
                })
                smd = sm.get("data") or sm
                if isinstance(smd, dict) and smd.get("ok"):
                    result["map_file"] = smd.get("file")
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
        p = item.get("params", {})

        width = int(p.get("width") or self._map_width_default())
        height = int(p.get("height") or self._map_height_default())
        maptype = (p.get("maptype") or self.plugin.get_option_value("map_type") or "mapnik").strip()

        base_params: List[Tuple[str, Any]] = [
            ("size", f"{width}x{height}"),
            ("maptype", maptype),
        ]

        params: List[Tuple[str, Any]] = list(base_params)

        # center/zoom or bbox
        if p.get("bbox"):
            vb = p["bbox"]
            if isinstance(vb, (list, tuple)) and len(vb) >= 4:
                minlon, minlat, maxlon, maxlat = vb[:4]
                params.append(("bbox", f"{minlon},{minlat},{maxlon},{maxlat}"))
            elif isinstance(vb, str):
                params.append(("bbox", vb))
        else:
            center_pt = None
            if p.get("center"):
                center_pt = self._resolve_point(p.get("center"))
            elif (p.get("lat") is not None) and (p.get("lon") is not None):
                center_pt = (float(p.get("lat")), float(p.get("lon")))
            if center_pt:
                params.append(("center", f"{center_pt[0]:.6f},{center_pt[1]:.6f}"))
            zoom = p.get("zoom") if p.get("zoom") is not None else self.plugin.get_option_value("map_zoom")
            if zoom is not None:
                params.append(("zoom", int(zoom)))

        # markers
        markers = p.get("markers") or []
        enc_markers: List[str] = []
        if isinstance(markers, (list, tuple)):
            for m in markers:
                em = self._encode_marker(m)
                if em:
                    enc_markers.append(em)
        elif isinstance(markers, str):
            enc_markers.append(markers)
        if enc_markers:
            params.append(("markers", "|".join(enc_markers)))

        # path(s)
        weight = p.get("weight")
        color = p.get("color")
        if p.get("path"):
            enc = self._encode_path(p.get("path"), color=color, weight=weight)
            if enc:
                params.append(("path", enc))
        for pp in (p.get("paths") or []):
            if isinstance(pp, dict):
                enc = self._encode_path(pp.get("points") or [], color=pp.get("color") or color,
                                        weight=pp.get("weight") or weight)
            else:
                enc = self._encode_path(pp, color=color, weight=weight)
            if enc:
                params.append(("path", enc))

        last_err = None
        for base in self._static_bases():
            try:
                url = f"{base.rstrip('/')}/staticmap.php"
                r = requests.get(url, headers=self._headers(), params=params, timeout=self._timeout())
                if 200 <= r.status_code < 300:
                    ctype = r.headers.get("Content-Type", "")
                    ext = "png" if "png" in ctype.lower() else ("jpg" if "jpeg" in ctype.lower() else "png")
                    out = p.get("out")
                    if not out:
                        name_hint = "bbox" if p.get("bbox") else (
                            f"center_{self._slug(str(p.get('center') or '') or 'map')}")
                        out = os.path.join("openstreetmap", f"osm_static_{name_hint}_{self._now()}.{ext}")
                    local = self._save_bytes(r.content, out)
                    self._add_image(local)
                    return self.make_response(item, {
                        "ok": True,
                        "file": local,
                        "service": base,
                        "request_url": r.request.url,
                        "_meta": {"status": r.status_code, "content_type": ctype},
                    })
                else:
                    last_err = f"{base} HTTP {r.status_code}: {r.text[:200]}"
            except Exception as e:
                last_err = f"{base} error: {e}"

        return self.make_response(item, {
            "ok": False,
            "error": last_err or "All static map backends failed",
        })

    def cmd_osm_show_url(self, item: dict) -> dict:
        p = item.get("params", {})
        pt = self._parse_point(p.get("point") or [p.get("lat"), p.get("lon")])
        if not pt:
            return self.make_response(item, "Param 'point' or 'lat'+'lon' required")
        lat, lon = pt
        zoom = int(p.get("zoom") or self.plugin.get_option_value("map_zoom") or 15)
        url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map={zoom}/{lat:.6f}/{lon:.6f}"
        return self.make_response(item, {"url": url, "lat": lat, "lon": lon, "zoom": zoom})

    def cmd_osm_route_url(self, item: dict) -> dict:
        p = item.get("params", {})
        try:
            start = self._resolve_point(p.get("start") or [p.get("start_lat"), p.get("start_lon")])
            end = self._resolve_point(p.get("end") or [p.get("end_lat"), p.get("end_lon")])
        except Exception:
            return self.make_response(item, "Params 'start' and 'end' required (address or lat,lon)")
        mode = (p.get("mode") or p.get("profile") or "car").lower()
        # OSM website engines commonly: fossgis_osrm_car|bike|foot
        if mode in ("driving", "car"):
            engine = "fossgis_osrm_car"
        elif mode in ("cycling", "bike", "bicycle"):
            engine = "fossgis_osrm_bike"
        else:
            engine = "fossgis_osrm_foot"
        url = f"https://www.openstreetmap.org/directions?engine={engine}&route={start[0]:.6f},{start[1]:.6f};{end[0]:.6f},{end[1]:.6f}"
        return self.make_response(item, {"url": url, "engine": engine})

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

    def cmd_osm_bbox_map(self, item: dict) -> dict:
        p = item.get("params", {})
        vb = p.get("bbox")
        if not vb:
            return self.make_response(item, "Param 'bbox' required (minlon,minlat,maxlon,maxlat)")
        return self.cmd_osm_staticmap({"cmd": "osm_staticmap", "params": p})