# Standard Library
import json
import os
import sys

# Third Party
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api_server


@pytest.fixture
def client():
    api_server.app.config["TESTING"] = True
    # Override API key for tests
    api_server.API_KEY = "test-key"
    with api_server.app.test_client() as client:
        yield client


def auth_headers():
    return {"Authorization": "Bearer test-key", "Content-Type": "application/json"}


def test_arxiv_url_is_skipped(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://arxiv.org/abs/2410.21228", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["skipped"] is True
    assert list(tmp_path.iterdir()) == []  # no file written


def test_youtube_url_is_skipped(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["skipped"] is True
    assert list(tmp_path.iterdir()) == []


def test_regular_url_is_queued(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://example.com/article", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data.get("skipped") is None
    assert len(list(tmp_path.iterdir())) == 1  # file was written


def test_missing_api_key_returns_401(client):
    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_missing_url_returns_400(client):
    response = client.post(
        "/api/bookmark",
        data=json.dumps({"html_content": "<html/>"}),
        headers=auth_headers(),
    )
    assert response.status_code == 400
