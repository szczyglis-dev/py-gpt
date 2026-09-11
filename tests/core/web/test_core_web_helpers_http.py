from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.web.helpers as mod
from pygpt_net.core.web.helpers import Helpers


def test_request_dispatches_method_and_builds_options(tmp_path, monkeypatch):
    session = SimpleNamespace(
        get=MagicMock(return_value=SimpleNamespace(status_code=200, text="ok")),
        post=MagicMock(return_value=SimpleNamespace(status_code=201, text="created")),
        put=MagicMock(), delete=MagicMock(), patch=MagicMock(),
    )
    monkeypatch.setattr(mod.requests, "Session", MagicMock(return_value=session))
    helper = Helpers()
    status, text = helper.request(
        "https://example.test", method="get", params={"q": 1}, headers={"X": "Y"},
        timeout=3, disable_ssl_verify=True, allow_redirects=False, stream=True, user_agent="UA",
    )
    assert (status, text) == (200, "ok")
    kwargs = session.get.call_args.kwargs
    assert kwargs["params"] == {"q": 1}
    assert kwargs["headers"] == {"X": "Y", "User-Agent": "UA"}
    assert kwargs["timeout"] == 3 and kwargs["verify"] is False
    assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
    assert helper.request("x", method="TRACE") == (None, "Invalid HTTP method: TRACE")


def test_request_upload_closes_file_and_returns_errors(tmp_path, monkeypatch):
    upload = tmp_path / "a.txt"; upload.write_text("x")
    captured = {}
    def post(url, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status_code=200, text="ok")
    session = SimpleNamespace(post=post)
    monkeypatch.setattr(mod.requests, "Session", MagicMock(return_value=session))
    helper = Helpers()
    assert helper.request("x", method="POST", files={"f": str(upload)}) == (200, "ok")
    assert captured["files"]["f"].closed is True

    bad_session = SimpleNamespace(get=MagicMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mod.requests, "Session", MagicMock(return_value=bad_session))
    status, text = helper.request("x")
    assert status is None and "boom" in text


def test_get_main_image_prefers_metadata(monkeypatch):
    html = b'<html><head><meta property="og:image" content="https://cdn/x.png"></head></html>'
    monkeypatch.setattr(mod.requests, "get", MagicMock(return_value=SimpleNamespace(content=html)))
    assert Helpers().get_main_image("https://example.test") == "https://cdn/x.png"


def test_get_links_and_images_make_absolute_and_deduplicate(monkeypatch):
    html = (b'<html><body>'
            b'<a href="/a">A</a><a href="/a">Duplicate</a><a href="b" title="Bee"></a>'
            b'<img src="/i.png"><img src="/i.png"><img src="https://cdn/j.png">'
            b'</body></html>')
    monkeypatch.setattr(mod.requests, "get", MagicMock(return_value=SimpleNamespace(content=html)))
    helper = Helpers()
    assert helper.get_links("https://example.test/root") == [
        {"A": "https://example.test/a"}, {"Bee": "https://example.test/b"}
    ]
    assert helper.get_images("https://example.test/root") == [
        "https://example.test/i.png", "https://cdn/j.png"
    ]


def test_download_image_writes_after_security_check_and_returns_local_path(tmp_path, monkeypatch):
    img_dir = tmp_path / "img"; img_dir.mkdir()
    security = SimpleNamespace(ensure_write=MagicMock())
    filesystem = SimpleNamespace(
        get_runtime_dir=MagicMock(return_value=str(img_dir)),
        make_local=MagicMock(side_effect=lambda p, ctx=None: f"local:{p}"),
    )
    config = SimpleNamespace(get_user_dir=MagicMock(return_value=str(img_dir)))
    window = SimpleNamespace(core=SimpleNamespace(config=config, security=security, filesystem=filesystem))
    monkeypatch.setattr(mod.requests, "get", MagicMock(return_value=SimpleNamespace(content=b"PNG")))
    out = Helpers(window).download_image("https://example.test/a.png")
    written = img_dir / "example.test_a.png"
    assert written.read_bytes() == b"PNG"
    security.ensure_write.assert_called_once_with(str(written), sandbox=False, ctx=None)
    assert out == f"local:{written}"
