"""Test single URL scraping endpoint in FastAPI server."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_scrape_single_url_validation():
    # Missing URL
    resp = client.post("/api/pipeline/scrape-url", json={"url": ""})
    assert resp.status_code == 400
    assert "required" in resp.json().get("error", "").lower()

    # Invalid URL
    resp2 = client.post("/api/pipeline/scrape-url", json={"url": "not-a-valid-url"})
    assert resp2.status_code == 400


def test_scrape_single_url_success():
    sample_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>CodePilot AI - Autonomous AI Coding Assistant</title>
        <meta name="description" content="CodePilot is a powerful AI coding copilot for teams.">
        <link rel="icon" href="/favicon.png">
      </head>
      <body>
        <h1>CodePilot AI</h1>
        <h2>Features</h2>
        <ul>
          <li>Real-time code completion</li>
          <li>Automated unit test generation</li>
        </ul>
        <p>Free plan available. Try for $19/mo.</p>
      </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://codepilot.ai"
    mock_resp.text = sample_html
    mock_resp.headers = {"content-type": "text/html"}

    with patch("src.utils.http_client._session.get", return_value=mock_resp), \
         patch("server.export_to_supabase", return_value="run_123"):
        resp = client.post("/api/pipeline/scrape-url", json={
            "url": "https://codepilot.ai",
            "name": "CodePilot AI",
            "category_hint": "Coding"
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "CodePilot AI"
    assert data["url"].rstrip("/") == "https://codepilot.ai"
    assert data["verified"] is True
    assert data["http_status"] == 200
    assert "Coding" in data["categories"]
