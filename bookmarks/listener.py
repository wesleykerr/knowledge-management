# Standard Library
import json
import logging
import os
import time
from pathlib import Path

# Third Party
import click
import peewee
from watchdog import events
from watchdog import observers

# Project
from bookmarks import models
from bookmarks.processors import arxiv
from bookmarks.processors import default
from bookmarks.processors import twitter
from bookmarks.processors import youtube

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)


def process_file(file_path: str):
    for attempt in range(3):
        try:
            with open(file_path, "r") as input_io:
                data = json.load(input_io)
        except json.JSONDecodeError:
            if attempt < 2:
                time.sleep(0.1)
                continue
            else:
                raise

    print(data["url"])
    if arxiv.is_arxiv_url(data["url"]):
        print("arxiv")
        arxiv.process_arxiv_url(data["url"])
    elif twitter.is_twitter_url(data["url"]):
        print("twitter")
        twitter.process_twitter_url(data["url"], data["html_content"], data["screenshot"])
    elif youtube.is_youtube_url(data["url"]):
        print("youtube")
        youtube.process_youtube_url(data["url"], data["html_content"])
    else:
        default.process_url(data["url"], data["html_content"])
    # TODO(wkerr): When we sucessfully process the file, we should delete it.
    os.remove(file_path)


class FileChangeHandler(events.FileSystemEventHandler):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def is_valid_file(self, path: str) -> bool:
        file_path = Path(path)
        return file_path.suffix.lower() == ".json" and file_path.name.startswith(self.prefix)

    def on_created(self, event):
        if event.is_directory:
            return

        if self.is_valid_file(event.src_path):
            logging.info(f"New valid file created: {event.src_path}")
            process_file(event.src_path)
        else:
            logging.debug(f"Ignoring non-matching file: {event.src_path}")

    def on_modified(self, event):
        if event.is_directory:
            return

        if self.is_valid_file(event.src_path):
            logging.info(f"Valid file modified: {event.src_path}")


def process_existing_files(directory: Path, prefix: str):
    """Process any existing files in the directory that match our prefix."""
    logging.info(f"Processing existing files in {directory}")
    for file_path in directory.glob(f"{prefix}*.json"):
        try:
            logging.info(f"Processing existing file: {file_path}")
            process_file(str(file_path))
        except Exception as e:
            logging.error(f"Error processing existing file {file_path}: {e}")


class DirectoryListener:
    def __init__(self, path_to_watch: Path, prefix: str):
        self.path_to_watch = path_to_watch
        self.prefix = prefix
        self.observer = observers.Observer()

    def start(self):
        try:
            if not self.path_to_watch.exists():
                self.path_to_watch.mkdir(parents=True)

            # Process existing files before starting the watch
            process_existing_files(self.path_to_watch, self.prefix)

            # Set up the file watcher
            event_handler = FileChangeHandler(self.prefix)
            self.observer.schedule(event_handler, str(self.path_to_watch), recursive=False)
            self.observer.start()
            logging.info(
                f"Started watching directory: {self.path_to_watch} "
                f"for JSON files with prefix: {self.prefix}"
            )

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.observer.stop()
                logging.info("Observer Stopped")

            self.observer.join()

        except Exception as e:
            logging.error(f"Error: {e}")
            self.observer.stop()


@click.command()
@click.argument("directory", type=click.Path(exists=False, file_okay=False, dir_okay=True))
@click.option("--create/--no-create", default=True, help="Create directory if it doesn't exist")
@click.option(
    "--prefix",
    required=True,
    help="File prefix to monitor (e.g., 'data_' will match 'data_123.json')",
)
def main(directory: str, create: bool, prefix: str):
    """Monitor a directory for new JSON files with a specific prefix.

    DIRECTORY: The path to the directory to monitor
    """
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    path = Path(directory)
    if not path.exists():
        if create:
            logging.info(f"Creating directory: {path}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise click.BadParameter(f"Directory does not exist: {path}")

    listener = DirectoryListener(path, prefix)
    listener.start()


if __name__ == "__main__":
    main()
