from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Job:
    title: str
    company: str
    url: str
    location: str = "Location not specified"
    work_mode: str = "Not specified"
    category: str = "Other Opportunities"
    description: str = ""
    source_name: str = "Unknown source"
    source_kind: str = "aggregator"
    official_url: str = ""
    published_at: str = ""
    verification_status: str = "needs_review"
    verification_note: str = "Not checked"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
