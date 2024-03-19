#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 01:00:00                  #
# ================================================== #

class Types:
    def __init__(self, window=None):
        """
        Filesystem types handler

        :param window: Window instance
        """
        self.window = window

    def is_image(self, path: str) -> bool:
        """
        Check if file is image

        :param path: path to file
        :return: True if file is image
        """
        return str(path).lower().endswith(tuple(self.get_img_ext()))

    def is_video(self, path: str) -> bool:
        """
        Check if file is video

        :param path: path to file
        :return: True if file is video
        """
        return str(path).lower().endswith(tuple(self.get_video_ext()))

    def is_audio(self, path: str) -> bool:
        """
        Check if file is audio

        :param path: path to file
        :return: True if file is audio
        """
        return str(path).lower().endswith(tuple(self.get_audio_ext()))

    def get_img_ext(self) -> list:
        """
        Get image extensions

        :return: list with image extensions
        """
        return ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']

    def get_video_ext(self) -> list:
        """
        Get video extensions

        :return: list with video extensions
        """
        return ['.mp4', '.avi', '.mkv', '.webm', '.mov', '.flv', '.wmv', '.3gp', '.ogg', '.ogv', '.mpg', '.mpeg', '.m4v']

    def get_audio_ext(self) -> list:
        """
        Get audio extensions

        :return: list with audio extensions
        """
        return ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac', '.aiff', '.alac', '.dsd', '.pcm', '.mpc']

    def get_excluded_extensions(self) -> list[str]:
        """
        Get excluded extensions if no loader is available

        :return: list of excluded extensions
        """
        # images
        excluded = ["jpg", "jpeg", "png", "psd", "gif", "bmp", "tiff",
                    "webp", "svg", "ico", "heic", "heif", "avif", "apng"]

        # audio
        excluded += ["mp3", "wav", "flac", "ogg", "m4a", "wma",
                     "aac", "aiff", "alac", "dsd", "pcm", "mpc"]

        # video
        excluded += ["mp4", "mkv", "avi", "mov", "wmv", "flv",
                     "webm", "vob", "ogv", "3gp", "3g2", "m4v", "m2v"]

        # archives
        excluded += ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "lz", "lz4",
                     "zst", "ar", "iso", "nrg", "dmg", "vhd", "vmdk", "vhdx", "vdi",
                     "img", "wim", "swm", "esd", "cab", "rpm", "deb", "pkg", "apk"]

        # binary
        excluded += ["exe", "dll", "so", "dylib", "app", "msi", "dmg", "pkg", "deb", "rpm", "apk", "jar",
                     "war", "ear", "class", "pyc", "whl", "egg", "so", "dylib", "a", "o", "lib", "bin",
                     "elf", "ko", "sys", "drv"]

        # sort and save
        excluded = sorted(excluded)

        return excluded

