# Standard Library
from typing import Optional
from urllib.parse import urlparse

# Project
from bookmarks.processors import arxiv
from bookmarks.processors import base
from bookmarks.processors import default
from bookmarks.processors import youtube

# Registry of domain-specific processors
PROCESSORS = {
    "arxiv.org": arxiv.ArxivProcessor,
    "youtube.com": youtube.YouTubeProcessor,
}


def get_processor(url: str) -> base.BaseProcessor:
    """Factory function to get the appropriate processor for a given URL."""
    domain = urlparse(url).netloc.lower()
    processor_class = PROCESSORS.get(domain, default.DefaultProcessor)
    return processor_class()
