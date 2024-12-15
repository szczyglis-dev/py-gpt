#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 01:00:00                  #
# ================================================== #

import os
import uuid
from typing import Optional, List, Dict, Tuple, Union

import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


class Helpers:
    def __init__(self, window=None):
        """
        Web helpers core

        :param window: Window instance
        """
        self.window = window

    def request(
            self,
            url: str = "",
            method: str = "GET",
            headers: Optional[dict] = None,
            params: Optional[dict] = None,
            data: Optional[Union[str, dict]] = None,
            json: Optional[dict] = None,
            files: Optional[dict] = None,
            cookies: Optional[dict] = None,
            timeout: int = 10,
            disable_ssl_verify: bool = False,
            allow_redirects: bool = True,
            stream: bool = False,
            user_agent: Optional[str] = None,
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Make HTTP request

        :param url: URL
        :param method: HTTP method
        :param headers: Headers
        :param params: GET parameters
        :param data: POST data
        :param json: JSON data
        :param files: Files
        :param cookies: Cookies
        :param timeout: Timeout
        :param disable_ssl_verify: Disable SSL verification
        :param allow_redirects: Allow redirects
        :param stream: Stream
        :param user_agent: User agent
        :return: status code, response text
        """
        upload = {}
        try:
            method = method.upper()
            session = requests.Session()
            args = {}

            if data:
                args['data'] = data
            if json:
                args['json'] = json
            if cookies:
                args['cookies'] = cookies
            if params:
                args['params'] = params
            if headers:
                args['headers'] = headers

            args['timeout'] = timeout
            if disable_ssl_verify:
                args['verify'] = False
            if not allow_redirects:
                args['allow_redirects'] = False
            if stream:
                args['stream'] = True
            if user_agent:
                if 'headers' not in args:
                    args['headers'] = {}
                args['headers']['User-Agent'] = user_agent

            if files:
                for key, value in files.items():
                    if os.path.exists(value) and os.path.isfile(value):
                        upload[key] = open(value, 'rb')
                args['files'] = upload

            if method == 'GET':
                response = session.get(url, **args)
            elif method == 'POST':
                response = session.post(url, **args)
            elif method == 'PUT':
                response = session.put(url, **args)
            elif method == 'DELETE':
                response = session.delete(url, **args)
            elif method == 'PATCH':
                response = session.patch(url, **args)
            else:
                return None, f'Invalid HTTP method: {method}'
            for k in upload:
                upload[k].close()  # close files if opened
            return response.status_code, response.text
        except Exception as e:
            for k in upload:
                upload[k].close()  # close files if opened
            return None, f'Error: {e}'

    def get_main_image(self, url: str) -> Optional[str]:
        """
        Get main image from URL

        :param url: URL to get image from
        :return: image URL
        """
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return twitter_image['content']

        link_image = soup.find('link', rel='image_src')
        if link_image and link_image.get('href'):
            return link_image['href']

        images = soup.find_all('img')
        if images:
            images = [img for img in images if 'logo' not in (img.get('src') or '').lower()]
            largest_image = None
            max_area = 0
            for img in images:
                src = img.get('src')
                if not src:
                    continue
                src = requests.compat.urljoin(url, src)
                try:
                    img_response = requests.get(src, stream=True, timeout=5)
                    img_response.raw.decode_content = True

                    from PIL import Image
                    image = Image.open(img_response.raw)
                    width, height = image.size
                    area = width * height
                    if area > max_area:
                        max_area = area
                        largest_image = src
                except:
                    continue
            if largest_image:
                return largest_image
        return None

    def get_links(self, url: str) -> List[Dict[str, str]]:
        """
        Get links from URL

        :param url: URL to get links from
        :return: links list
        """
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        urls = []
        for link in soup.find_all('a'):
            try:
                name = link.get_text(strip=True)
                address = link.get('href')
                if address:
                    address = urljoin(url, address)
                    if not name:
                        title = link.get('title')
                        if title:
                            name = title
                        else:
                            name = address
                    if address not in urls:
                        urls.append(address)
                        links.append({name: address})
            except:
                continue
        return links


    def get_images(self, url: str) -> List[str]:
        """
        Get images from URL

        :param url: URL to get images from
        :return: images list
        """
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        images = []
        for img in soup.find_all('img'):
            try:
                address = img.get('src')
                if address:
                    address = urljoin(url, address)
                    if address not in images:
                        images.append(address)
            except:
                continue
        return images

    def download_image(self, img: str) -> str:
        """
        Download image from URL

        :param img: URL to download image from
        :return: local path to image
        """
        dir = self.window.core.config.get_user_dir("img")
        response = requests.get(img, stream=True)
        name = img.replace("http://", "").replace("https://", "").replace("/", "_")
        path = os.path.join(dir, name)
        if os.path.exists(path):
            name = name + uuid.uuid4().hex[:6].upper()
        download_path = os.path.join(dir, name)
        with open(download_path, 'wb', ) as f:
            f.write(response.content)
        return self.window.core.filesystem.make_local(download_path)