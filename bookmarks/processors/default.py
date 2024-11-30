# Standard Library
import datetime
from typing import Dict
from typing import List

# Third Party
import jinja2
import openai
import peewee
import pydantic
import tiktoken

# Project
from bookmarks.processors import base
from bookmarks.utils import llm


class SummaryAndTags(pydantic.BaseModel):
    summary: str
    key_points: list[str]
    tags: list[str]


def normalize_tag(tag: str) -> str:
    """Normalize a tag by converting to lowercase and replacing spaces with hyphens."""
    return tag.lower().strip().replace(" ", "-")


SYSTEM = """You are a highly skilled Research Information Specialist with expertise in library science, academic research, and knowledge management. Your background includes:

* Advanced training in information architecture and taxonomy development
* Experience as a research librarian at leading academic institutions
* Expertise in metadata schemas and controlled vocabularies
* Deep understanding of academic writing across multiple disciplines

Core Responsibilities

SUMMARIZATION

* Create concise yet comprehensive summaries that preserve key findings and methodology
* Highlight statistical significance and limitations of research
* Identify and extract central arguments and supporting evidence
* Maintain academic rigor while making content accessible


KNOWLEDGE ORGANIZATION

* Apply consistent taxonomic principles to classify information
* Generate relevant tags using controlled vocabulary terms
* Create structured metadata including:
    * Research methodology
    * Field of study
    * Key findings
    * Limitations and gaps

CONTEXTUAL ANALYSIS

* Place findings within broader academic discourse
* Identify connections to related research
* Flag potential conflicts with existing literature
* Note implications for future research

Follow the format:

{
  "summary": "A summary of the text in 3-5 paragraphs.",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3",
    "... up to 5 key points"
  ],
  "tags": [
    "tag1",
    "tag2",
    "tag3",
    "... up to 10 tags"
  ]
}
"""

USER = "Here is the content: {content}"


def get_markdown(url, url_hash, title, summary, tags):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("article.md")

    data = {
        "tags": "\n".join([f" - {tag}" for tag in tags]),
        "date_time": datetime.datetime.today().strftime("%Y-%m-%dT%H:%M"),
        "url": url,
        "url_hash": url_hash,
        "title": title,
        "summary": summary,
    }

    rendered_markdown = template.render(data)
    return rendered_markdown


class DefaultProcessor(base.BaseProcessor):
    """Default processor for handling generic web pages using readability content."""

    def __init__(self):
        super().__init__()

        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
        self.template = self.env.get_template("article.md")

    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        """Extract metadata from readability content.

        For the default processor, we don't extract additional metadata since
        readability and the LLM will handle the content processing.

        Args:
            html_content: Raw HTML content of the page

        Returns:
            Empty dict as we rely on readability for content extraction
        """
        return {}

    def generate_markdown(
        self, url: str, url_hash: str, title: str, content: str, metadata: Dict[str, str]
    ) -> str:
        """Generate prompt for summarizing webpage content.

        Args:
            content: Main content text from readability
            metadata: Empty dict (unused in default processor)

        Returns:
            Formatted prompt string
        """
        _, output_obj = llm.call_structured_llm(
            url_hash, content, SYSTEM, USER, SummaryAndTags
        )

        # Normalize all tags
        normalized_tags = [normalize_tag(tag) for tag in output_obj.tags]

        data = {
            "tags": "\n".join([f" - {tag}" for tag in normalized_tags]),
            "date_time": datetime.datetime.today().strftime("%Y-%m-%dT%H:%M"),
            "url": url,
            "url_hash": url_hash,
            "title": title,
            "summary": output_obj.summary,
            "key_points": "\n".join(f"* {point}" for point in output_obj.key_points),
        }

        rendered_markdown = self.template.render(data)
        return rendered_markdown
