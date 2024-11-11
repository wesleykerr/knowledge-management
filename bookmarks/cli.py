# Standard Library
import logging
import traceback
from urllib import parse

# Third Party
import click
import peewee

# Project
from bookmarks import bookmark_processor
from bookmarks import models
from bookmarks.utils import llm

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(name)s: %(message)s [%(process)d]",
    level=logging.WARN,
)

logger = logging.getLogger("bookmarks")
logger.setLevel(logging.INFO)


@click.group()
def main():
    pass


@main.command()
@click.option("--url", help="What url to process")
def bookmark(url):
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    markdown = bookmark_processor.bookmark(url)
    print(markdown)


@main.command()
@click.option("--url", help="What url to process")
def reprocess(url):
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    markdown = bookmark_processor.reprocess(url)
    print(markdown)


@main.command()
@click.option("--url", help="What url to process")
def hash(url):
    url_hash = llm.get_url_hash(url)
    print(url_hash)


if __name__ == "__main__":
    main()
