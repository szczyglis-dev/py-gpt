#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import os
import time
import pytest
import requests

from pygpt_net.provider.gpt.container import Container

class DummyResponse:
    def __init__(self, status_code, content=None, json_data=None, text=""):
        self.status_code = status_code
        self._content = content
        self._json = json_data
        self.text = text
        self.content = content
    def json(self):
        if self._json is not None:
            return self._json
        raise ValueError("No JSON data")

class FakeModels:
    def get(self, model):
        return {"dummy": "dummy"}
    def prepare_client_args(self, mode, model_data):
        return {"base_url": "http://test", "api_key": "testkey", "organization_key": "orgkey"}

class FakeConfig:
    def has(self, key):
        if key == "download.dir":
            return False
        return False
    def get(self, key):
        if key == "download.dir":
            return ""
        return ""
    def get_user_dir(self, arg):
        return self.user_dir

class FakeFilesystem:
    def make_local_list(self, lst):
        return lst

class FakeCore:
    def __init__(self, user_dir):
        self.models = FakeModels()
        self.config = FakeConfig()
        self.config.user_dir = user_dir
        self.filesystem = FakeFilesystem()

class FakeWindow:
    def __init__(self, user_dir):
        self.core = FakeCore(user_dir)

class FakeCtx:
    def __init__(self):
        self.files = []
        self.images = []
        self.model = "model1"
        self.mode = "mode1"

@pytest.fixture
def fake_window(tmp_path):
    return FakeWindow(str(tmp_path))

@pytest.fixture
def fake_ctx():
    return FakeCtx()

def test_download_files_empty(fake_window, fake_ctx):
    container = Container(window=fake_window)
    result = container.download_files(fake_ctx, [])
    assert result == []
    result = container.download_files(fake_ctx, None)
    assert result == []
    result = container.download_files(fake_ctx, "notalist")
    assert result == []

def test_download_files_missing_keys(fake_window, fake_ctx):
    container = Container(window=fake_window)
    files = [{"file_id": "f1"}, {"container_id": "c1"}, {"wrong": "value"}]
    result = container.download_files(fake_ctx, files)
    assert result == []

def test_download_files_exception_in_info(monkeypatch, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            raise requests.RequestException("info exception")
        return DummyResponse(200, content=b"content")
    monkeypatch.setattr(requests, "get", fake_get)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert result == []

def test_download_files_info_fail(monkeypatch, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            return DummyResponse(404, json_data={}, text="Not Found")
        return DummyResponse(200, content=b"content")
    monkeypatch.setattr(requests, "get", fake_get)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert result == []

def test_download_files_download_fail(monkeypatch, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            return DummyResponse(200, json_data={"path": "subdir/file.png"})
        return DummyResponse(400, text="Download error")
    monkeypatch.setattr(requests, "get", fake_get)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert result == []

def test_download_files_exception_in_download(monkeypatch, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            return DummyResponse(200, json_data={"path": "subdir/file.png"})
        raise requests.RequestException("download exception")
    monkeypatch.setattr(requests, "get", fake_get)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert result == []

def test_download_files_success_no_existing(monkeypatch, tmp_path, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            return DummyResponse(200, json_data={"path": "subdir/testimage.png"})
        return DummyResponse(200, content=b"filecontent")
    monkeypatch.setattr(requests, "get", fake_get)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert len(result) == 1

def test_download_files_success_existing_file(monkeypatch, tmp_path, fake_window, fake_ctx):
    def fake_get(url, headers):
        if not url.endswith("/content"):
            return DummyResponse(200, json_data={"path": "subdir/testimage.png"})
        return DummyResponse(200, content=b"filecontent")
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(time, "strftime", lambda fmt: "TESTPREFIX_")
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    container = Container(window=fake_window)
    files = [{"file_id": "f1", "container_id": "c1"}]
    result = container.download_files(fake_ctx, files)
    assert len(result) == 1
    file_path = result[0]
    assert "TESTPREFIX_" in os.path.basename(file_path)
    with open(file_path, "rb") as f:
        data = f.read()
    assert data == b"filecontent"
    assert file_path in fake_ctx.files
    assert file_path in fake_ctx.images