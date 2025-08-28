#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

import os
import time

import requests
from typing import List

from pygpt_net.item.ctx import CtxItem


class Container:
    def __init__(self, window=None):
        """
        Container wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def download_files(self, ctx: CtxItem, files: list) -> List[str]:
        """
        Download files for the model

        :param ctx: Context item
        :param files: List of files to download
        """
        if not files or not isinstance(files, list):
            return []

        model_data = self.window.core.models.get(ctx.model)
        args = self.window.core.models.prepare_client_args(ctx.mode, model_data)
        base_url = args.get('base_url', '')
        api_key = args.get('api_key', '')
        organization_key = args.get('organization_key', '')
        headers = {}
        headers["Authorization"] = f"Bearer {api_key}"
        if organization_key:
            headers["OpenAI-Organization"] = organization_key

        downloaded_files = []

        for file in files:
            file_id = file.get('file_id')
            if not file_id:
                continue
            container_id = file.get('container_id')
            if not container_id:
                continue

            # get file info
            url = f"{base_url}/containers/{container_id}/files/{file_id}"
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    file_info = response.json()
                else:
                    print(f"Failed to get file info for {file_id}: {response.status_code} {response.text}")
                    continue
            except requests.RequestException as e:
                print(f"Error getting file info for {file_id}: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error getting file info for {file_id}: {e}")
                continue

            file_name = file_info.get('path', file_id)
            file_name = os.path.basename(file_name)
            url = f"{base_url}/containers/{container_id}/files/{file_id}/content"

            # prepare the path to save the file
            if self.window.core.config.has("download.dir") and self.window.core.config.get("download.dir") != "":
                dir = os.path.join(
                    self.window.core.config.get_user_dir('data'),
                    self.window.core.config.get("download.dir"),
                )
            else:
                dir = self.window.core.config.get_user_dir('data')

            path = os.path.join(dir, file_name)
            if os.path.exists(path):
                prefix = time.strftime("%Y%m%d_%H%M%S_")
                path = os.path.join(dir, f"{prefix}{file_name}")

            # download the file
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    file_content = response.content
                    os.makedirs(dir, exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(file_content)
                    downloaded_files.append(str(path))
                else:
                    print(f"Failed to download file {file_id}: {response.status_code} {response.text}")
            except requests.RequestException as e:
                print(f"Error downloading file {file_id}: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error downloading file {file_id}: {e}")
                continue

        # append to ctx
        if downloaded_files:
            downloaded_files = self.window.core.filesystem.make_local_list(downloaded_files)
            if not isinstance(ctx.files, list):
                ctx.files = []
            ctx.files += downloaded_files
            images = []
            for path in downloaded_files:
                ext = os.path.splitext(path)[1].lower().lstrip(".")
                if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                    if path not in images:
                        images.append(path)
            if images:
                if not isinstance(ctx.images, list):
                    ctx.images = []
                ctx.images += images

        return downloaded_files