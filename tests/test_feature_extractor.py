from bs4 import BeautifulSoup
from src.extraction.feature_extractor import extract_pricing, extract_social_links, extract_features
from src.extraction.logo_extractor import extract_logo


def test_extract_pricing_freemium():
    html = """
    <html>
        <body>
            <a href="/pricing">Pricing Plans</a>
            <p>Start your free trial today with our starter plan.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    pricing = extract_pricing(soup, html)
    assert pricing == "Freemium"


def test_extract_pricing_open_source():
    html = """
    <html>
        <body>
            <h1>Self-hostable LLM agent</h1>
            <p>Licensed under Apache 2.0 open source license.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    pricing = extract_pricing(soup, html)
    assert pricing == "Open Source"


def test_extract_social_links():
    html = """
    <html>
        <body>
            <a href="https://github.com/myorg/mytool">Source Code</a>
            <a href="https://discord.gg/invite123">Community</a>
            <a href="https://twitter.com/mytool">Twitter</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    socials = extract_social_links(soup, "https://mytool.ai")
    assert socials.get("github") == "https://github.com/myorg/mytool"
    assert "discord.gg" in socials.get("discord", "")
    assert "twitter.com" in socials.get("twitter", "")


def test_extract_logo_fallback():
    html = "<html><head></head><body>No logo here</body></html>"
    soup = BeautifulSoup(html, "lxml")
    logo = extract_logo(soup, "https://example.com")
    assert "google.com/s2/favicons" in logo or logo.endswith("/favicon.ico")
