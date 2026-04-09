# Standard Library
import datetime
import json
import logging
import os
import subprocess

# Third Party
import click
import markdownify
import peewee
import readabilipy

# Project
from knowledge import constants
from knowledge import models
from knowledge.utils import images
from knowledge.utils import llm
from knowledge.utils import urls

logger = logging.getLogger(__name__)


def process_url(url: str, html_content: str = None) -> None:
    os.makedirs(constants.WEB_PAGE_PATH, exist_ok=True)

    url_hash = llm.get_url_hash(url)
    web_page_dir = os.path.join(constants.WEB_PAGE_PATH, url_hash)
    os.makedirs(web_page_dir, exist_ok=True)

    # 1. HTML content
    if not html_content:
        html_content = urls.get_content(url)

    with open(os.path.join(web_page_dir, "raw.html"), "w") as f:
        f.write(html_content)

    # 2. Readability extraction
    readability_obj = readabilipy.simple_json_from_html_string(html_content, use_readability=True)
    plain_content = readability_obj["plain_content"]
    readability_markdown = markdownify.markdownify(plain_content)
    with open(os.path.join(web_page_dir, "readability.md"), "w") as f:
        f.write(readability_markdown)

    # 3. Full article markdown with localized images
    processed_html = images.process_article_images(url_hash, html_content, url)
    article_markdown = markdownify.markdownify(processed_html)
    with open(os.path.join(web_page_dir, "article.md"), "w") as f:
        f.write(article_markdown)

    # 4. Stage for Claude
    os.makedirs(constants.STAGED_PATH, exist_ok=True)
    staged_path = os.path.join(constants.STAGED_PATH, f"{url_hash}.json")
    staged_data = {
        "url": url,
        "url_hash": url_hash,
        "readability_markdown": readability_markdown,
        "web_page_dir": os.path.abspath(web_page_dir),
        "staged_at": datetime.datetime.now().isoformat(),
    }
    with open(staged_path, "w") as f:
        json.dump(staged_data, f, indent=2)

    # 5. Invoke Claude to classify, summarize, and write vault note
    subprocess.run(
        [
            os.path.expanduser("~/.local/bin/claude"),
            "-p",
            f"Process the web article staged at {staged_path} using the web-article skill",
        ],
        check=True,
    )


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
        process_url(url, html_content)
        click.echo(f"Successfully processed URL: {url}")
    except Exception as e:
        click.echo(f"Error processing URL: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    process()
