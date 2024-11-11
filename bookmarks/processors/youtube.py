# Standard Library
import re
from typing import Dict
from typing import List

# Third Party
from bs4 import BeautifulSoup

from .base import BaseProcessor


class YouTubeProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.template = "video"

    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        soup = BeautifulSoup(html_content, "html.parser")

        metadata = {
            "duration": self._extract_duration(soup),
            "channel": self._extract_channel(soup),
            "publish_date": self._extract_date(soup),
            "views": self._extract_views(soup),
        }

        return metadata

    def generate_prompt(self, content: str, metadata: Dict[str, str]) -> str:
        return f"""Summarize this YouTube video:
Duration: {metadata.get('duration', 'unknown')}
Channel: {metadata.get('channel', 'unknown')}
Published: {metadata.get('publish_date', 'unknown')}

Key points to address:
1. Main topic or thesis
2. Key arguments or demonstrations
3. Notable timestamps
4. Practical takeaways

Content:
{content}
"""

    def process_tags(self, tags: List[str]) -> List[str]:
        # Always include video tag
        tags = list(set(tags + ["video", "youtube"]))
        return tags
