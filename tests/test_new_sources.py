"""Unit tests for HuggingFace and AwesomeLists discovery sources."""
from unittest.mock import patch, MagicMock
from src.discovery.huggingface_source import HuggingFaceSource
from src.discovery.awesome_lists_source import AwesomeListsSource


def test_huggingface_source_parsing():
    source = HuggingFaceSource(limit_per_page=5, max_pages=1)
    mock_spaces = [
        {
            "id": "test-author/awesome-llm-chat",
            "likes": 1250,
            "sdk": "gradio",
            "tags": ["chat", "llm", "dialog"],
        },
        {
            "id": "diffusers/sd-image-generator",
            "likes": 3400,
            "sdk": "streamlit",
            "tags": ["diffusion", "image", "art"],
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_spaces
    mock_resp.headers = {}

    with patch("src.discovery.huggingface_source._session.get", return_value=mock_resp):
        candidates = source.discover()

    assert len(candidates) == 2
    c1 = candidates[0]
    assert c1.name == "Awesome Llm Chat"
    assert "https://huggingface.co/spaces/test-author/awesome-llm-chat" in c1.url
    assert c1.category_hint == "Chat & Assistant"
    assert c1.pricing == "Free"
    assert c1.open_source is True

    c2 = candidates[1]
    assert c2.name == "Sd Image Generator"
    assert c2.category_hint == "Generative AI"


def test_awesome_lists_source_parsing():
    source = AwesomeListsSource()
    markdown_sample = """
    # Awesome AI
    - [Cursor](https://cursor.com) - The AI Code Editor built for programming.
    - [Midjourney](https://midjourney.com) - Generative text to image AI platform.
    - [Bad Link](https://twitter.com/bad) - Twitter editorial link to ignore.
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = markdown_sample

    with patch("src.discovery.awesome_lists_source._session.get", return_value=mock_resp):
        candidates = source.discover()

    # twitter link is excluded, only Cursor and Midjourney
    assert len(candidates) >= 2
    names = [c.name for c in candidates]
    assert "Cursor" in names
    assert "Midjourney" in names
