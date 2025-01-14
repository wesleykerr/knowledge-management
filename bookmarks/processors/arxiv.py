# Standard Library
import datetime
import enum
import os
import pathlib
import re
from typing import Dict
from typing import List

# Third Party
import arxiv
import click
import jinja2
import peewee
import PIL
import pydantic
from bs4 import BeautifulSoup
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

# Project
from bookmarks import constants
from bookmarks import models
from bookmarks.processors import base
from bookmarks.utils import llm


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


def is_arxiv_url(url: str) -> bool:
    return "arxiv.org" in url.lower()


def extract_arxiv_id(url: str) -> str:
    # Handle both new and old style arxiv URLs
    patterns = [
        r"arxiv\.org/abs/(\d+\.\d+)",
        r"arxiv\.org/pdf/(\d+\.\d+)",
    ]

    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    raise ValueError(f"Could not extract arXiv ID from URL: {url}")


def extract_pdf_link(soup, arxiv_id: str = None) -> str:
    """Extract the PDF link from an arXiv page.

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        str: The PDF URL or empty string if not found
    """
    # Try the direct PDF link first
    pdf_link = soup.find("a", title="Download PDF")
    if pdf_link and pdf_link.get("href"):
        return f"https://arxiv.org{pdf_link['href']}"

    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return ""


def save_images(images: dict[str, PIL.Image], output_dir: pathlib.Path) -> None:
    """Save dictionary of images to specified directory."""
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save each image
    for filename, image in images.items():
        # Create full path and save
        image_path = pathlib.Path(output_dir, filename)
        image.save(str(image_path))


def convert_pdf_to_markdown_marker(arxiv_id: str) -> str:
    pdf_file = os.path.join(constants.RESEARCH_PAPERS_PATH, f"{arxiv_id}.pdf")
    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(pdf_file)
    text, _, images = text_from_rendered(rendered)

    # model_lst = marker.models.load_all_models()
    # full_text, images, out_meta = marker.convert.convert_single_pdf(pdf_file, model_lst)

    markdown_path = pathlib.Path(constants.RESEARCH_MARKDOWN_PATH, arxiv_id, f"{arxiv_id}.md")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(text)

    save_images(images, pathlib.Path(constants.RESEARCH_MARKDOWN_PATH, arxiv_id))
    return text


def create_markdown(paper: arxiv.Result, data: Dict[str, str]) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("academic.md")
    markdown = template.render(**data)

    safe_title = paper.title.replace(":", "-")
    # safe_title = sanitize_filename(paper.title)
    note_path = pathlib.Path(constants.RESEARCH_NOTES_PATH, f"{safe_title}.md")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(markdown)


def process_arxiv_url(url: str, html_content: str = None, metadata: dict = dict()) -> str:
    arxiv_id = extract_arxiv_id(url)
    client = arxiv.Client()

    search = arxiv.Search(id_list=[arxiv_id])
    results = client.results(search)
    paper = next(results)

    arxiv_id = paper.entry_id.split("/")[-1]

    # Download PDF
    os.makedirs(constants.RESEARCH_PAPERS_PATH, exist_ok=True)
    pdf_path = os.path.join(constants.RESEARCH_PAPERS_PATH, f"{arxiv_id}.pdf")
    if not os.path.exists(pdf_path):
        paper.download_pdf(dirpath=constants.RESEARCH_PAPERS_PATH, filename=f"{arxiv_id}.pdf")

    # Extract Markdown
    markdown_text = convert_pdf_to_markdown_marker(arxiv_id)

    # Create Metadata and Summary

    data = {"folders": constants.FOLDER_STRUCTURE}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("prompts/arxiv.md")

    system = template.render(**data)
    user = "Here is the content: {content}"

    _, output_obj = llm.call_structured_llm(arxiv_id, markdown_text, system, user, ExpectedOutput)
    print(output_obj.tags)
    normalized_tags = [base.normalize_tag(tag) for tag in output_obj.tags]

    # Move the PDF to the output_obj.folder_classification.path and store the new file name
    output_dir = os.path.join(constants.KNOWLEDGE_BASE_PATH, output_obj.folder_classification.path)
    os.makedirs(output_dir, exist_ok=True)

    # Move the markdown folder to the output_dir and store the new file name
    markdown_dir = os.path.join(constants.RESEARCH_MARKDOWN_PATH, arxiv_id)
    os.rename(markdown_dir, os.path.join(output_dir, arxiv_id))

    pdf_path = os.path.join(constants.RESEARCH_PAPERS_PATH, f"{arxiv_id}.pdf")
    os.rename(pdf_path, os.path.join(output_dir, f"{arxiv_id}.pdf"))

    data = {
        "title": paper.title,
        "abstract": paper.summary,
        "added_date": metadata.get("added_date", datetime.datetime.now()),
        "published_date": paper.published,
        "arxiv_url": url,
        "arxiv_id": arxiv_id,
        "authors": [author.name for author in paper.authors],
        "summary": output_obj.summary,
        "key_points": "\n".join(f"* {point}" for point in output_obj.key_points),
        "tags": "\n".join([f" - {tag}" for tag in normalized_tags]),
        "output_path": output_obj.folder_classification.path,
        "read": metadata.get("read", False),
        "read_date": metadata.get("read_date", ""),
        "notes": metadata.get("notes", ""),
    }
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("academic.md")
    markdown = template.render(**data)

    filename = base.get_filename(paper.title, llm.get_url_hash(url))
    note_path = pathlib.Path(output_dir, f"{arxiv_id}-{filename}")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(markdown)


@click.command()
@click.argument("url")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(url: str, verbose: bool):
    """Process an arXiv URL to download and organize papers."""
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    try:
        if verbose:
            click.echo(f"Processing {url}...")

        process_arxiv_url(url)
        click.echo(f"Successfully processed {url}")
    except Exception as e:
        click.echo(f"Error processing URL: {e}", err=True)
        raise


if __name__ == "__main__":
    main()
