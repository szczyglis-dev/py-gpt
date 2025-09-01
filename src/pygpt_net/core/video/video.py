#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.01 23:00:00                  #
# ================================================== #

import uuid
import os
import shutil
import subprocess
from typing import Optional, List, Dict
from time import strftime

from PySide6.QtCore import Slot, QObject

from pygpt_net.core.types import VIDEO_AVAILABLE_ASPECT_RATIOS
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Video(QObject):
    def __init__(self, window=None):
        """
        Video generation core

        :param window: Window instance
        """
        super().__init__()
        self.window = window

    def install(self):
        """Install provider data, img dir, etc."""
        img_dir = os.path.join(self.window.core.config.get_user_dir("video"))
        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

    @Slot(object, list, str)
    def handle_finished(
            self,
            ctx: CtxItem,
            paths: List[str],
            prompt: str
    ):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response(ctx, paths, prompt)

    @Slot(object, list, str)
    def handle_finished_inline(
            self,
            ctx: CtxItem,
            paths: List[str],
            prompt: str
    ):
        """
        Handle finished image generation

        :param ctx: CtxItem
        :param paths: images paths list
        :param prompt: prompt used for generate images
        """
        self.window.controller.chat.image.handle_response_inline(
            ctx,
            paths,
            prompt,
        )

    @Slot(object)
    def handle_status(self, msg: str):
        """
        Handle thread status message

        :param msg: status message
        """
        self.window.update_status(msg)

        is_log = False
        if self.window.core.config.has("log.dalle") \
                and self.window.core.config.get("log.dalle"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print(msg)

    @Slot(object)
    def handle_error(self, msg: any):
        """
        Handle thread error message

        :param msg: error message
        """
        self.window.update_status(msg)
        self.window.core.debug.log(msg)
        self.window.ui.dialogs.alert(msg)

    def save_video(self, path: str, video: bytes) -> bool:
        """
        Save video to file

        :param path: path to save
        :param video: image data
        :return: True if success
        """
        try:
            with open(path, 'wb') as file:
                file.write(video)
            try:
                # try to make web compatible
                self.make_web_compatible(path)
            except Exception as e:
                pass
            return True
        except Exception as e:
            print(trans('img.status.save.error') + ": " + str(e))
            return False

    def make_web_compatible(
            self,
            src_path: str,
            fps: int = 30,
            crf_h264: int = 22,
            crf_vp9: int = 30,
            audio_bitrate: str = "128k",
            make_mp4: bool = True,
            make_webm: bool = True,
            overwrite: bool = True,
    ) -> Dict[str, Optional[str]]:
        """
        Create browser-friendly video variants (MP4 H.264/AAC yuv420p + WebM VP9/Opus yuv420p).

        Returns:
            dict: {"mp4": "/abs/path/file.web.mp4" or None, "webm": "/abs/path/file.webm" or None}

        Notes:
        - Requires ffmpeg in PATH.
        - Ensures even dimensions, yuv420p, faststart for MP4, and Opus for WebM.
        - Uses CRF for quality: lower = better (and larger). Tweak crf_h264 / crf_vp9 if needed.
        """
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")

        # Ensure ffmpeg is available
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found in PATH. Please install ffmpeg.")

        root, _ = os.path.splitext(os.path.abspath(src_path))
        out_mp4 = f"{root}.web.mp4"
        out_webm = f"{root}.webm"

        # Remove outputs if overwrite is requested
        if overwrite:
            for p in (out_mp4, out_webm):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

        # Common video filter:
        # - scale to even dimensions (required by many encoders)
        # - format to yuv420p (8-bit), also set SAR=1
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos,format=yuv420p,setsar=1"

        results = {"mp4": None, "webm": None}

        def run_cmd(cmd, dst):
            # Run ffmpeg and return dst on success, None on failure
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                return dst if os.path.exists(dst) else None
            except subprocess.CalledProcessError as e:
                # If needed, print(e.stdout.decode(errors="ignore"))
                return None

        if make_mp4:
            # H.264 High@4.1, yuv420p, AAC; add faststart for web playback
            mp4_cmd = [
                ffmpeg, "-y",
                "-i", src_path,
                "-map", "0:v:0", "-map", "0:a:0?",  # include audio if present
                "-vf", vf,
                "-r", str(fps),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-profile:v", "high", "-level", "4.1",
                "-preset", "medium",
                "-crf", str(crf_h264),
                "-color_primaries", "bt709", "-colorspace", "bt709", "-color_trc", "bt709",
                "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", audio_bitrate, "-ac", "2", "-ar", "48000",
                "-sn",
                out_mp4,
            ]
            results["mp4"] = run_cmd(mp4_cmd, out_mp4)

        if make_webm:
            # VP9 (CRF, constant quality), Opus audio
            webm_cmd = [
                ffmpeg, "-y",
                "-i", src_path,
                "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", vf,
                "-r", str(fps),
                "-c:v", "libvpx-vp9",
                "-b:v", "0",  # use CRF mode
                "-crf", str(crf_vp9),
                "-row-mt", "1",
                "-pix_fmt", "yuv420p",
                "-deadline", "good",  # "good" for quality; "realtime" for speed
                "-cpu-used", "2",  # lower = slower/better; tweak for performance
                "-c:a", "libopus", "-b:a", audio_bitrate, "-ac", "2", "-ar", "48000",
                "-sn",
                out_webm,
            ]
            results["webm"] = run_cmd(webm_cmd, out_webm)

        return results

    def make_safe_filename(self, name: str) -> str:
        """
        Make safe filename

        :param name: filename to make safe
        :return: safe filename
        """
        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"
        return "".join(safe_char(c) for c in name).rstrip("_")[:30]

    def gen_unique_path(self, ctx: CtxItem):
        """
        Generate unique image path based on context

        :param ctx: CtxItem
        :return: unique image path
        """
        img_id = uuid.uuid4()
        dt_prefix = strftime("%Y%m%d_%H%M%S")
        img_dir = self.window.core.config.get_user_dir("img")
        filename = f"{dt_prefix}_{img_id}.png"
        return os.path.join(img_dir, filename)

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model id (strip optional 'models/' prefix).

        :param model: model id
        """
        try:
            return model.split("/")[-1]
        except Exception:
            return model

    def get_aspect_ratio_option(self) -> dict:
        """
        Get image resolution option for UI

        :return: dict
        """
        return {
            "type": "combo",
            "slider": True,
            "label": "video.aspect_ratio",
            "value": "16:9",
            "keys": self.get_available_aspect_ratio(),
        }

    def get_available_aspect_ratio(self, model: str = None) -> Dict[str, str]:
        """
        Get available image resolutions

        :param model: model name
        :return: dict of available resolutions
        """
        return VIDEO_AVAILABLE_ASPECT_RATIOS

