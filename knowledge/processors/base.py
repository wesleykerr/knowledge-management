# Standard Library
import re
from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Tuple


def normalize_tag(tag: str) -> str:
    """Normalize a tag by converting to lowercase and replacing spaces with hyphens."""
    return tag.lower().strip().replace(" ", "-")


def sanitize_filename(title: str) -> str:
    """Convert title to a clean filename without spaces or punctuation."""
    # Remove any non-alphanumeric characters (except hyphens and underscores)
    clean = re.sub(r"[^\w\s-]", "", title.lower())
    # Replace spaces with hyphens
    clean = re.sub(r"\s+", "-", clean)
    # Remove any repeated hyphens
    clean = re.sub(r"-+", "-", clean)
    return clean.strip("-")


def get_filename(title: str, url_hash: str) -> str:
    base_name = sanitize_filename(title[:50])  # Limit length to 50 chars

    # Add unique suffix (last 4 chars of hash)
    unique_suffix = url_hash[-4:]
    filename = f"{base_name}-{unique_suffix}.md"
    return filename


class BaseProcessor:
    """Base class for domain-specific processors."""

    def __init__(self):
        self.template = "default"  # Template name for markdown generation

    @abstractmethod
    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        """Extract domain-specific metadata from HTML content."""
        pass

    @abstractmethod
    def generate_markdown(self, content: str, metadata: Dict[str, str]) -> str:
        """Returns the markdown data that represents this content."""
        pass
