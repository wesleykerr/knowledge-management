# Standard Library
from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Tuple


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
