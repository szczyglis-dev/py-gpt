#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.18 03:40:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # HTTP / endpoints
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )
        plugin.add_option(
            "user_agent",
            type="text",
            value="pygpt/OSM",
            label="User-Agent",
            description="Custom User-Agent for requests. If empty, a default UA will be used.",
        )
        plugin.add_option(
            "contact_email",
            type="text",
            value="",
            label="Contact email (Nominatim)",
            description="Recommended by Nominatim usage policy. Include an email for contact.",
        )
        plugin.add_option(
            "accept_language",
            type="text",
            value="",
            label="Accept-Language",
            description="Preferred language for results, e.g. 'pl,en-US;q=0.8'.",
        )

        plugin.add_option(
            "nominatim_base",
            type="text",
            value="https://nominatim.openstreetmap.org",
            label="Nominatim base",
            description="Base URL for Nominatim (geocoding).",
        )
        plugin.add_option(
            "osrm_base",
            type="text",
            value="https://router.project-osrm.org",
            label="OSRM base",
            description="Base URL for OSRM routing.",
        )
        plugin.add_option(
            "tile_base",
            type="text",
            value="https://tile.openstreetmap.org",
            label="Tile base",
            description="Base URL for XYZ tiles (z/x/y.png).",
        )

        # Map defaults (used for URL zoom and bbox zoom estimation)
        plugin.add_option(
            "map_zoom",
            type="int",
            value=14,
            label="Default zoom",
            description="Default zoom if not specified (for OSM site URLs).",
        )
        plugin.add_option(
            "map_width",
            type="int",
            value=800,
            label="Default width",
            description="Used only to estimate zoom for bbox (no image rendering).",
        )
        plugin.add_option(
            "map_height",
            type="int",
            value=600,
            label="Default height",
            description="Used only to estimate zoom for bbox (no image rendering).",
        )

        # ---------------- Commands ----------------

        plugin.add_cmd(
            "osm_geocode",
            instruction="OpenStreetMap: Forward geocoding via Nominatim.",
            params=[
                {"name": "query", "type": "str", "required": True, "description": "Address or place to search"},
                {"name": "limit", "type": "int", "required": False, "description": "Max results"},
                {"name": "countrycodes", "type": "str", "required": False, "description": "Comma-separated ISO2 codes (e.g., 'pl,de')"},
                {"name": "viewbox", "type": "str", "required": False, "description": "minlon,minlat,maxlon,maxlat (or list[4])"},
                {"name": "bounded", "type": "bool", "required": False, "description": "Restrict results to viewbox"},
                {"name": "addressdetails", "type": "bool", "required": False, "description": "Include address details"},
                {"name": "polygon_geojson", "type": "bool", "required": False, "description": "Include polygon geometry"},
                {"name": "near", "type": "str", "required": False, "description": "Near point/address; builds a viewbox automatically"},
                {"name": "near_lat", "type": "float", "required": False, "description": "Near latitude (alternative to 'near')"},
                {"name": "near_lon", "type": "float", "required": False, "description": "Near longitude"},
                {"name": "radius_m", "type": "int", "required": False, "description": "Radius for near-based viewbox (m)"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom for returned map_url (defaults to 'Default zoom')"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' value for map_url"},
            ],
            enabled=True,
            description="OSM: geocode (results include map_url)",
            tab="map",
        )

        plugin.add_cmd(
            "osm_reverse",
            instruction="OpenStreetMap: Reverse geocoding via Nominatim.",
            params=[
                {"name": "lat", "type": "float", "required": False, "description": "Latitude"},
                {"name": "lon", "type": "float", "required": False, "description": "Longitude"},
                {"name": "point", "type": "str", "required": False, "description": "Alternative 'lat,lon'"},
                {"name": "zoom", "type": "int", "required": False, "description": "Detail level (also used for map_url zoom)"},
                {"name": "addressdetails", "type": "bool", "required": False, "description": "Include address details"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' value for map_url"},
            ],
            enabled=True,
            description="OSM: reverse geocode (response includes map_url)",
            tab="map",
        )

        plugin.add_cmd(
            "osm_search",
            instruction="OpenStreetMap: General search (Nominatim) with optional near/viewbox filters.",
            params=[
                {"name": "query", "type": "str", "required": True, "description": "Free-text search"},
                {"name": "limit", "type": "int", "required": False, "description": "Max results"},
                {"name": "countrycodes", "type": "str", "required": False, "description": "Comma-separated ISO2 codes"},
                {"name": "near", "type": "str", "required": False, "description": "Near point/address"},
                {"name": "near_lat", "type": "float", "required": False, "description": "Near latitude"},
                {"name": "near_lon", "type": "float", "required": False, "description": "Near longitude"},
                {"name": "radius_m", "type": "int", "required": False, "description": "Radius for near viewbox (m)"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom for returned map_url"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' value for map_url"},
            ],
            enabled=True,
            description="OSM: search (results include map_url)",
            tab="map",
        )

        plugin.add_cmd(
            "osm_route",
            instruction="OpenStreetMap: Routing via OSRM (driving/walking/cycling). Lightweight by default.",
            params=[
                {"name": "start", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "start_lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "start_lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "end", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "end_lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "end_lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "waypoints", "type": "list", "required": False, "description": "Optional intermediate points"},

                {"name": "profile", "type": "str", "required": False, "description": "driving|walking|cycling"},
                {"name": "mode", "type": "str", "required": False, "description": "url|summary|full (default: summary)"},
                {"name": "include_geometry", "type": "bool", "required": False, "description": "Include compact geometry (polyline6) in 'full' mode"},
                {"name": "include_steps", "type": "bool", "required": False, "description": "Include step-by-step (only in 'full' mode)"},
                {"name": "alternatives", "type": "int", "required": False, "description": "0|1; if >0 treated as 'true' for OSRM alternatives"},
                {"name": "max_polyline_chars", "type": "int", "required": False, "description": "Limit geometry string length (default 5000)"},
                {"name": "debug_url", "type": "bool", "required": False, "description": "Include OSRM request URL in the response"},

                {"name": "save_map", "type": "bool", "required": False, "description": "Build an OSM map URL focused on route bbox/center"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom for preview URL (when applicable)"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' for preview"},
                {"name": "width", "type": "int", "required": False, "description": "Used only to estimate zoom for bbox"},
                {"name": "height", "type": "int", "required": False, "description": "Used only to estimate zoom for bbox"},

                {"name": "markers", "type": "list", "required": False, "description": "Optional list of points; first used as marker in preview"},
            ],
            enabled=True,
            description="OSM: route (returns distance/duration and map_url; geometry optional in 'full')",
            tab="route",
        )

        plugin.add_cmd(
            "osm_staticmap",
            instruction="OpenStreetMap: Build a map URL on openstreetmap.org (center/zoom or bbox; optional single marker).",
            params=[
                {"name": "center", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom level"},
                {"name": "bbox", "type": "list", "required": False, "description": "minlon,minlat,maxlon,maxlat"},
                {"name": "markers", "type": "list", "required": False, "description": "List of candidate points; first valid becomes the marker"},
                {"name": "marker", "type": "bool", "required": False, "description": "If true and no markers given, place marker at center"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' value"},
                {"name": "width", "type": "int", "required": False, "description": "Used only to estimate zoom for bbox"},
                {"name": "height", "type": "int", "required": False, "description": "Used only to estimate zoom for bbox"},
            ],
            enabled=True,
            description="OSM: build map URL (openstreetmap.org)",
            tab="map",
        )

        plugin.add_cmd(
            "osm_bbox_map",
            instruction="OpenStreetMap: Shortcut to build a map URL for a given bbox (openstreetmap.org).",
            params=[
                {"name": "bbox", "type": "list", "required": True, "description": "minlon,minlat,maxlon,maxlat"},
                {"name": "markers", "type": "list", "required": False, "description": "Markers (first will be used for OSM site marker)"},
                {"name": "width", "type": "int", "required": False, "description": "Used only to estimate zoom"},
                {"name": "height", "type": "int", "required": False, "description": "Used only to estimate zoom"},
            ],
            enabled=True,
            description="OSM: bbox URL",
            tab="map",
        )

        plugin.add_cmd(
            "osm_show_url",
            instruction="OpenStreetMap: Return an OSM website URL centered on a point (with marker).",
            params=[
                {"name": "point", "type": "str", "required": False, "description": "'lat,lon' or address"},
                {"name": "lat", "type": "float", "required": False, "description": "Latitude"},
                {"name": "lon", "type": "float", "required": False, "description": "Longitude"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom"},
                {"name": "layers", "type": "str", "required": False, "description": "Optional OSM site 'layers=' value"},
            ],
            enabled=True,
            description="OSM: show URL",
            tab="map",
        )

        plugin.add_cmd(
            "osm_route_url",
            instruction="OpenStreetMap: Return a directions URL on openstreetmap.org.",
            params=[
                {"name": "start", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "end", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "start_lat", "type": "float", "required": False, "description": "Latitude start"},
                {"name": "start_lon", "type": "float", "required": False, "description": "Longitude start"},
                {"name": "end_lat", "type": "float", "required": False, "description": "Latitude end"},
                {"name": "end_lon", "type": "float", "required": False, "description": "Longitude end"},
                {"name": "mode", "type": "str", "required": False, "description": "car|bike|foot"},
            ],
            enabled=True,
            description="OSM: route URL",
            tab="route",
        )

        plugin.add_cmd(
            "osm_tile",
            instruction="OpenStreetMap: Download a single XYZ tile (z/x/y.png).",
            params=[
                {"name": "z", "type": "int", "required": True, "description": "Zoom"},
                {"name": "x", "type": "int", "required": True, "description": "X index"},
                {"name": "y", "type": "int", "required": True, "description": "Y index"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path"},
            ],
            enabled=True,
            description="OSM: download tile",
            tab="map",
        )