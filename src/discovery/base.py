"""Abstract base for all discovery sources."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Candidate:
    name: str
    url: str = ""
    description: str = ""
    category_hint: str = ""
    source_name: str = ""
    source_url: str = ""
    extra: dict = field(default_factory=dict)
    # populated later during extraction
    verified: bool = False
    http_status: int = 0
    logo_url: str = ""
    pricing: str = ""
    features: list = field(default_factory=list)
    social_links: dict = field(default_factory=dict)
    open_source: bool = False


class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def discover(self) -> list:
        """Return a list of raw Candidate objects."""
