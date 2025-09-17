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
            "staticmap_base",
            type="text",
            value="https://staticmap.openstreetmap.de",
            label="Static map base",
            description="Base URL for static map service.",
        )
        plugin.add_option(
            "tile_base",
            type="text",
            value="https://tile.openstreetmap.org",
            label="Tile base",
            description="Base URL for XYZ tiles (z/x/y.png).",
        )

        # Map defaults
        plugin.add_option(
            "map_type",
            type="text",
            value="mapnik",
            label="Default map type",
            description="Static map layer type (provider dependent).",
        )
        plugin.add_option(
            "map_zoom",
            type="int",
            value=14,
            label="Default zoom",
            description="Default zoom if not specified (for center-based maps).",
        )
        plugin.add_option(
            "map_width",
            type="int",
            value=800,
            label="Default width",
            description="Default static map width (px).",
        )
        plugin.add_option(
            "map_height",
            type="int",
            value=600,
            label="Default height",
            description="Default static map height (px).",
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
            ],
            enabled=True,
            description="OSM: geocode",
            tab="map",
        )

        plugin.add_cmd(
            "osm_reverse",
            instruction="OpenStreetMap: Reverse geocoding via Nominatim.",
            params=[
                {"name": "lat", "type": "float", "required": False, "description": "Latitude"},
                {"name": "lon", "type": "float", "required": False, "description": "Longitude"},
                {"name": "point", "type": "str", "required": False, "description": "Alternative 'lat,lon'"},
                {"name": "zoom", "type": "int", "required": False, "description": "Detail level"},
                {"name": "addressdetails", "type": "bool", "required": False, "description": "Include address details"},
            ],
            enabled=True,
            description="OSM: reverse geocode",
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
            ],
            enabled=True,
            description="OSM: search",
            tab="map",
        )

        plugin.add_cmd(
            "osm_route",
            instruction="OpenStreetMap: Routing via OSRM (driving/walking/cycling).",
            params=[
                {"name": "start", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "start_lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "start_lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "end", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "end_lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "end_lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "waypoints", "type": "list", "required": False, "description": "Optional intermediate points"},
                {"name": "profile", "type": "str", "required": False, "description": "driving|walking|cycling"},
                {"name": "overview", "type": "str", "required": False, "description": "full|simplified|false"},
                {"name": "steps", "type": "bool", "required": False, "description": "Include step-by-step"},
                {"name": "alternatives", "type": "int", "required": False, "description": "Number of alternatives"},
                {"name": "save_map", "type": "bool", "required": False, "description": "Generate a static map image"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path (if saving map)"},
                {"name": "width", "type": "int", "required": False, "description": "Map width (px)"},
                {"name": "height", "type": "int", "required": False, "description": "Map height (px)"},
                {"name": "color", "type": "str", "required": False, "description": "Path color"},
                {"name": "weight", "type": "int", "required": False, "description": "Path weight"},
                {"name": "markers", "type": "list", "required": False, "description": "Markers list for map"},
            ],
            enabled=True,
            description="OSM: route",
            tab="route",
        )

        plugin.add_cmd(
            "osm_staticmap",
            instruction="OpenStreetMap: Generate static map image (center/zoom or bbox, markers, path).",
            params=[
                {"name": "center", "type": "str", "required": False, "description": "Address or 'lat,lon'"},
                {"name": "lat", "type": "float", "required": False, "description": "Latitude (alternative)"},
                {"name": "lon", "type": "float", "required": False, "description": "Longitude (alternative)"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom level"},
                {"name": "bbox", "type": "list", "required": False, "description": "minlon,minlat,maxlon,maxlat"},
                {"name": "markers", "type": "list", "required": False, "description": "Markers list"},
                {"name": "path", "type": "list", "required": False, "description": "List of points for one path"},
                {"name": "paths", "type": "list", "required": False, "description": "Multiple paths"},
                {"name": "color", "type": "str", "required": False, "description": "Path color"},
                {"name": "weight", "type": "int", "required": False, "description": "Path weight"},
                {"name": "width", "type": "int", "required": False, "description": "Image width"},
                {"name": "height", "type": "int", "required": False, "description": "Image height"},
                {"name": "maptype", "type": "str", "required": False, "description": "Static map type/layer"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path"},
            ],
            enabled=True,
            description="OSM: static map",
            tab="map",
        )

        plugin.add_cmd(
            "osm_bbox_map",
            instruction="OpenStreetMap: Generate static map for a bounding box.",
            params=[
                {"name": "bbox", "type": "list", "required": True, "description": "minlon,minlat,maxlon,maxlat"},
                {"name": "markers", "type": "list", "required": False, "description": "Markers"},
                {"name": "path", "type": "list", "required": False, "description": "Path points"},
                {"name": "width", "type": "int", "required": False, "description": "Width"},
                {"name": "height", "type": "int", "required": False, "description": "Height"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path"},
            ],
            enabled=True,
            description="OSM: bbox static map",
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