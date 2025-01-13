# Standard Library
import datetime
import enum
import json
import logging
import os
import pathlib
from typing import Dict
from typing import List

# Third Party
import click
import jinja2
import markdownify
import peewee
import pydantic
import readabilipy

# Project
from bookmarks import constants
from bookmarks import models
from bookmarks.processors import base
from bookmarks.utils import images
from bookmarks.utils import llm
from bookmarks.utils import urls

logger = logging.getLogger(__name__)


class DocumentType(str, enum.Enum):
    RESEARCH_PAPER = "research_paper"
    NEWS_ARTICLE = "news_article"
    INDUSTRY_REPORT = "industry_report"
    CASE_STUDY = "case_study"
    TECHNICAL_DOCUMENT = "technical_document"
    OPINION_PIECE = "opinion_piece"
    SURVEY = "survey"
    WHITEPAPER = "whitepaper"


class SourceType(str, enum.Enum):
    ACADEMIC = "academic"
    INDUSTRY = "industry"
    NEWS = "news"
    GOVERNMENT = "government"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Folder(pydantic.BaseModel):
    path: str = pydantic.Field(description="The local path to the folder")
    reason: str = pydantic.Field(description="The reason for the folder classification")

    class Config:
        extra = "forbid"


class PublicationInfo(pydantic.BaseModel):
    date: str = pydantic.Field(description="The date of the publication in YYYY-MM-DD format")
    source_type: SourceType = pydantic.Field(description="The type of source")
    confidence_level: ConfidenceLevel = pydantic.Field(
        description="The confidence level of the publication"
    )

    class Config:
        extra = "forbid"


class Metadata(pydantic.BaseModel):
    title: str = pydantic.Field(description="The title of the document")
    document_type: DocumentType = pydantic.Field(description="The type of document")
    publication_info: PublicationInfo = pydantic.Field(description="The publication information")

    class Config:
        extra = "forbid"


class ExpectedOutput(pydantic.BaseModel):
    folder_classification: Folder = pydantic.Field(description="The folder classification")
    metadata: Metadata = pydantic.Field(description="The metadata")
    summary: str = pydantic.Field(description="A summary of the text in 3-5 paragraphs.")
    key_points: list[str] = pydantic.Field(description="Up to 5 key points")
    tags: list[str] = pydantic.Field(description="Up to 10 tags")

    class Config:
        extra = "forbid"


def get_webpage(url_hash: str, url: str, html_content: str = None) -> str:
    html_content = urls.get_content(url)
    return html_content


def get_readability(url_hash, html_content) -> str:
    os.makedirs(constants.WEB_READABILITY_PATH, exist_ok=True)
    os.makedirs(constants.WEB_READABILITY_HTML_PATH, exist_ok=True)

    readability_path = os.path.join(constants.WEB_READABILITY_PATH, f"{url_hash}.json")
    if os.path.exists(readability_path):
        with open(readability_path, "r") as f:
            content_obj = json.load(f)
    else:
        logger.info("HTML Content Length: %s", len(html_content))
        content_obj = readabilipy.simple_json_from_html_string(html_content, use_readability=True)
        content = content_obj["plain_content"]
        if content is None:
            raise ValueError("No content")

        with open(readability_path, "w") as f:
            json.dump(content_obj, f)

    readability_html_path = os.path.join(constants.WEB_READABILITY_HTML_PATH, f"{url_hash}.html")
    if os.path.exists(readability_html_path):
        with open(readability_html_path, "r") as input_io:
            content = input_io.read()
    else:
        content = readabilipy.simple_tree_from_html_string(html_content)
        with open(readability_html_path, "w") as output_io:
            output_io.write(str(content))

    return content_obj


def process_url(url: str, html_content: str = None) -> str:
    os.makedirs(constants.WEB_SUMMARY_PATH, exist_ok=True)
    os.makedirs(constants.WEB_MARKDOWN_PATH, exist_ok=True)
    os.makedirs(constants.WEB_PAGE_PATH, exist_ok=True)

    url_hash = llm.get_url_hash(url)
    os.makedirs(os.path.join(constants.WEB_PAGE_PATH, url_hash), exist_ok=True)

    # with open(os.path.join(constants.WEB_PAGE_PATH, url_hash, f"raw.html"), "r") as f:
    #     html_content = f.read()

    # For an article there are thre important pieces of information.
    # 1. HTML Content - we either get this provided to us or have to download it.
    if not html_content:
        html_content = urls.get_content(url)

    with open(os.path.join(constants.WEB_PAGE_PATH, url_hash, f"raw.html"), "w") as f:
        f.write(html_content)

    # 2. Readability - we use readability to extract the content and metadata
    readability_obj = readabilipy.simple_json_from_html_string(html_content, use_readability=True)
    plain_content = readability_obj["plain_content"]
    markdown_content = markdownify.markdownify(plain_content)
    with open(os.path.join(constants.WEB_PAGE_PATH, url_hash, f"readability.md"), "w") as f:
        f.write(markdown_content)

    # 3. Markdown - we use markdownify to convert the HTML to markdown
    html_content = images.process_article_images(url_hash, html_content, url)
    markdown_content = markdownify.markdownify(html_content)
    with open(os.path.join(constants.WEB_PAGE_PATH, url_hash, f"article.md"), "w") as f:
        f.write(markdown_content)

    # Create Metadata and Summary

    data = {"folders": constants.FOLDER_STRUCTURE}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("prompts/default.md")

    system = template.render(**data)
    user = "Here is the content: {content}"

    _, output_obj = llm.call_structured_llm(
        url_hash, markdown_content, system, user, ExpectedOutput
    )
    normalized_tags = [base.normalize_tag(tag) for tag in output_obj.tags]

    output_dir = os.path.join(constants.KNOWLEDGE_BASE_PATH, output_obj.folder_classification.path)
    os.makedirs(output_dir, exist_ok=True)

    data = {
        "url": url,
        "url_hash": url_hash,
        "title": output_obj.metadata.title,
        "today": datetime.datetime.now(),
        "published_date": output_obj.metadata.publication_info.date,
        "summary": output_obj.summary,
        "key_points": "\n".join(f"* {point}" for point in output_obj.key_points),
        "tags": "\n".join([f" - {tag}" for tag in normalized_tags]),
        "output_path": output_obj.folder_classification.path,
    }
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("article.md")
    markdown = template.render(**data)

    filename = base.get_filename(output_obj.metadata.title, url_hash)
    note_path = pathlib.Path(output_dir, filename)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(markdown)

    # Move the other contents to the new outputdir.
    os.rename(os.path.join(constants.WEB_PAGE_PATH, url_hash), os.path.join(output_dir, url_hash))


@click.command()
@click.argument("url")
@click.option(
    "--html-content", default=None, help="Optional HTML content to process instead of downloading"
)
def process(url: str, html_content: str = None):
    """Process a URL and generate a markdown summary."""
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    try:
        result = process_url(url, html_content)
        click.echo(f"Successfully processed URL: {url}")
        return result
    except Exception as e:
        click.echo(f"Error processing URL: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    process()
