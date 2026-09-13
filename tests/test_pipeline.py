from src.cleaning.url_normalizer import normalize_url, canonical_domain
from src.cleaning.text_cleaner import clean_text, clean_description
from src.normalization.entity_normalizer import canonical_name
from src.utils.uuid_generator import stable_uuid


def test_url_normalization():
    assert normalize_url("http://www.OpenAI.com/?utm_source=x") == "https://openai.com/"


def test_url_normalization_no_scheme():
    assert normalize_url("cursor.com").startswith("https://cursor.com")


def test_canonical_name():
    assert canonical_name("OpenAI, Inc.") == "openai"
    assert canonical_name("Cursor LLC") == canonical_name("Cursor")


def test_stable_uuid_deterministic():
    a = stable_uuid("Tool", "https://cursor.com")
    b = stable_uuid("Tool", "https://cursor.com")
    assert a == b


def test_stable_uuid_differs_by_url():
    a = stable_uuid("Tool", "https://cursor.com")
    b = stable_uuid("Tool", "https://windsurf.com")
    assert a != b


def test_canonical_domain():
    assert canonical_domain("https://www.elevenlabs.io/pricing") == "elevenlabs.io"


def test_clean_text_strips_html_and_urls():
    dirty = "<p>Great tool!</p> see https://example.com &amp; more"
    cleaned = clean_text(dirty)
    assert "<p>" not in cleaned
    assert "https://" not in cleaned


def test_clean_description_clamps_length():
    long_text = "word " * 200
    result = clean_description(long_text)
    assert len(result) <= 401  # DESCRIPTION_MAX + ellipsis
