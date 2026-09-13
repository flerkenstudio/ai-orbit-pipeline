"""Keyword-based classification against the approved taxonomy."""
import re

from src.config import TAXONOMY

KEYWORDS = {
    "Coding": ["code", "developer", "ide", "programming", "copilot", "editor"],
    "Writing": ["writing", "copywriter", "blog", "essay", "content"],
    "Image Generation": ["image", "art", "photo", "diffusion", "text-to-image"],
    "Video Generation": ["video", "film", "animation", "text-to-video"],
    "Audio & Music": ["voice", "music", "audio", "speech synthesis", "tts"],
    "Chat & Assistant": ["chatbot", "assistant", "chat", "conversation", "gpt"],
    "Search": ["search", "answer engine", "semantic search"],
    "Design": ["design", "presentation", "ui", "figma", "slide"],
    "Marketing": ["marketing", "seo", "ads", "copywriting"],
    "Developer Tools": ["api", "sdk", "framework", "open source", "llm"],
    "Translation": ["translate", "translation", "localization"],
    "Speech Recognition": ["transcription", "transcribe", "asr", "meeting"],
    "Agent Framework": ["agent", "autonomous", "orchestration", "multi-agent"],
    "Automation": ["automation", "workflow", "zapier", "integration"],
    "Research": ["research", "papers", "academic", "literature"],
}


def _contains_keyword(text: str, keyword: str) -> bool:
    """Word-boundary match so short keywords (e.g. 'ide') don't false-positive
    inside unrelated words (e.g. 'worldwide')."""
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def categorize(entity) -> list:
    text = f"{entity.name} {entity.description}".lower()
    scores = {}
    for cat, words in KEYWORDS.items():
        score = sum(1 for w in words if _contains_keyword(text, w))
        if score:
            scores[cat] = score
    if not scores:
        return entity.categories or ["Other"]
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    cats = [c for c, _ in ranked[:2]]
    result = [c for c in cats if c in TAXONOMY]
    return result or (entity.categories or ["Other"])
