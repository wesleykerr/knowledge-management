# Standard Library
import hashlib
import json
import subprocess
from pathlib import Path
from unittest import mock

# Third Party
import pytest


@pytest.fixture(autouse=True)
def patch_paths(tmp_path, monkeypatch):
    from knowledge import constants

    monkeypatch.setattr(constants, "WEB_PAGE_PATH", str(tmp_path / "web-pages"))
    monkeypatch.setattr(constants, "STAGED_PATH", str(tmp_path / "staged"))


@pytest.fixture(autouse=True)
def mock_readability():
    with mock.patch("readabilipy.simple_json_from_html_string") as m:
        m.return_value = {"plain_content": "<p>Test article content.</p>"}
        yield m


@pytest.fixture(autouse=True)
def mock_images():
    with mock.patch("knowledge.utils.images.process_article_images") as m:
        m.side_effect = lambda url_hash, html, url: html
        yield m


@pytest.fixture
def mock_subprocess():
    with mock.patch("subprocess.run") as m:
        yield m


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def test_process_url_writes_staged_json(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    staged_file = tmp_path / "staged" / f"{url_hash}.json"

    assert staged_file.exists(), "staged JSON file was not written"
    data = json.loads(staged_file.read_text())

    assert data["url"] == url
    assert data["url_hash"] == url_hash
    assert "readability_markdown" in data
    assert len(data["readability_markdown"]) > 0
    assert "web_page_dir" in data
    assert Path(data["web_page_dir"]).is_absolute(), "web_page_dir must be an absolute path"
    assert "staged_at" in data


def test_process_url_invokes_claude_with_staged_path(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    staged_path = str(tmp_path / "staged" / f"{url_hash}.json")

    mock_subprocess.assert_called_once()
    cmd = mock_subprocess.call_args[0][0]
    kwargs = mock_subprocess.call_args[1]

    assert cmd[0] == "claude"
    assert cmd[1] == "-p"
    assert staged_path in cmd[2]
    assert "web-article" in cmd[2]
    assert kwargs.get("check") is True


def test_process_url_writes_web_page_files(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    web_page_dir = tmp_path / "web-pages" / url_hash

    assert (web_page_dir / "raw.html").exists()
    assert (web_page_dir / "readability.md").exists()
    assert (web_page_dir / "article.md").exists()
