# Standard Library
import logging
import pathlib
import random
import re
import traceback
from urllib import parse

# Third Party
import peewee
import readabilipy
import requests

# Project
from bookmarks import models
from bookmarks import processors
from bookmarks.utils import llm

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(name)s: %(message)s [%(process)d]",
    level=logging.WARN,
)
logger = logging.getLogger("bookmark_processor")
logger.setLevel(logging.INFO)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]


def sanitize_filename(title: str) -> str:
    """Convert title to a clean filename without spaces or punctuation."""
    # Remove any non-alphanumeric characters (except hyphens and underscores)
    clean = re.sub(r"[^\w\s-]", "", title.lower())
    # Replace spaces with hyphens
    clean = re.sub(r"\s+", "-", clean)
    # Remove any repeated hyphens
    clean = re.sub(r"-+", "-", clean)
    return clean.strip("-")


def get_filename(bookmark: models.Bookmark) -> str:
    base_name = sanitize_filename(bookmark.title[:50])  # Limit length to 50 chars

    # Add unique suffix (last 4 chars of hash)
    unique_suffix = bookmark.url_hash[-4:]
    filename = f"{base_name}-{unique_suffix}.md"
    return filename


def write_markdown(
    summary: models.Summary, filename: str, output_dir: pathlib.Path
) -> pathlib.Path:
    """Write markdown to file with sanitized title and unique suffix."""
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write the file
    file_path = output_dir / filename
    file_path.write_text(summary.markdown)
    logger.info(f"Wrote markdown to {file_path}")

    return file_path


def get_webpage(url_hash, url):
    try:
        webpage = models.WebPage.get(models.WebPage.url_hash == url_hash)
        return webpage.content
    except peewee.DoesNotExist:
        pass

    logger.info(f"url_hash: {url_hash} url: {url}")
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = response.text

        webpage = models.WebPage.create(url_hash=url_hash, url=url, content=content)
        webpage.save()

        return content
    elif response.status_code == 403:
        raise ValueError(f"Status=403 {url}")
    elif response.status_code == 404:
        raise ValueError(f"URL Missing: {url}")
    elif response.status_code == 500:
        raise ValueError(f"Service problem: {url}")
    else:
        logger.error(f"StatusCode: {response.status_code} URL: {url}")
        raise ValueError(f"StatusCode: {response.status_code} URL: {url}")


def get_readability(url_hash, url, html_content) -> models.ReadabilityPage:
    try:
        readability = models.ReadabilityPage.get(models.ReadabilityPage.url_hash == url_hash)
        return readability
    except peewee.DoesNotExist:
        pass

    logger.info("HTML Content Length: %s", len(html_content))
    content_obj = readabilipy.simple_json_from_html_string(html_content, use_readability=True)
    content = content_obj["plain_content"]
    if content is None:
        raise ValueError("No content")

    readability = models.ReadabilityPage.create(url_hash=url_hash, url=url, content=content_obj)
    readability.save()

    html_content = readabilipy.simple_tree_from_html_string(html_content)
    readability_html = models.ReadabilityHTMLPage.create(
        url_hash=url_hash, url=url, content=html_content
    )
    readability_html.save()
    return readability


def process_bookmark(bookmark: models.Bookmark):
    try:
        webpage = get_webpage(bookmark.url_hash, bookmark.url)
        readability = get_readability(bookmark.url_hash, bookmark.url, webpage)

        processor = processors.get_processor(bookmark.url)
        markdown = processor.generate_markdown(bookmark, readability.content["plain_content"], {})

        filename = get_filename(bookmark)
        summary_obj, created = models.Summary.get_or_create(url_hash=bookmark.url_hash)
        summary_obj.url = bookmark.url
        summary_obj.markdown = markdown
        summary_obj.filename = filename
        summary_obj.save()

        bookmark.title = readability.content["title"]
        bookmark.status = 2
        bookmark.save()

        output_dir = pathlib.Path("obsidian/summary")
        file_path = write_markdown(summary_obj, filename, output_dir)

    except FileExistsError:
        logging.debug("File exists...")
    except Exception as e:
        logger.error(f"Failed to process: {bookmark.title}")
        try:
            error = models.Error.create(
                url_hash=bookmark.url_hash,
                url=bookmark.url,
                title=bookmark.title,
                exception=repr(e),
                stack_trace=traceback.format_exc(),
            )
            error.save()
        except peewee.IntegrityError:
            pass
        bookmark.status = 1
        bookmark.save()
        raise e


def bookmark(url, html_content=None) -> str:
    url_hash = llm.get_url_hash(url)
    try:
        bookmark = models.Bookmark.create(url_hash=url_hash, url=url, title="", status=0)
        bookmark.save()

        if html_content:
            webpage = models.WebPage.create(url_hash=url_hash, url=url, content=html_content)
            webpage.save()
    except (peewee.IntegrityError, peewee.DatabaseError) as e:
        try:
            summary = models.Summary.get(models.Summary.url_hash == url_hash)
            logger.info(f"Bookmark and Summary exists: {url}")
            return summary.markdown
        except peewee.DoesNotExist:
            logger.info(f"Bookmark exists so reprocessing: {url}")
            return reprocess(url, html_content)

    markdown = process_bookmark(bookmark)
    return markdown


def reprocess(url: str, html_content: str = None) -> str:
    """Reprocess this URL with the expectation that it exists in the database.

    The assumption here is that the URL failed at some point to be processed and we want
    to try again.
    """
    url_hash = llm.get_url_hash(url)
    bookmark = models.Bookmark.get(models.Bookmark.url_hash == url_hash)
    if html_content:
        logger.info(f"HTML Content provided so saving: {url}")
        try:
            webpage = models.WebPage.create(url_hash=url_hash, url=url, content=html_content)
            webpage.save()
        except peewee.IntegrityError:
            logger.info(f"WebPage already exists: {url}")

    markdown = process_bookmark(bookmark)
    return markdown