# Standard Library
import datetime
import enum
import os
import pathlib
import typing
from urllib.parse import parse_qs
from urllib.parse import urlparse

# Third Party
import click
import jinja2
import peewee
import pydantic
import youtube_transcript_api as yta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Project
from bookmarks import constants
from bookmarks import models
from bookmarks.processors import base
from bookmarks.utils import llm


class VideoType(str, enum.Enum):
    TUTORIAL = "tutorial"
    REVIEW = "review"
    VLOG = "vlog"
    DOCUMENTARY = "documentary"
    NEWS = "news"
    ENTERTAINMENT = "entertainment"
    LECTURE = "lecture"
    PRODUCT_DEMO = "product_demo"
    INTERVIEW = "interview"
    COMMENTARY = "commentary"
    GAMING = "gaming"
    MUSIC = "music"
    PODCAST = "podcast"
    EVENT_COVERAGE = "event_coverage"
    RESEARCH = "research"


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


class ExpectedOutput(pydantic.BaseModel):
    folder_classification: Folder = pydantic.Field(description="The folder classification")
    document_type: VideoType = pydantic.Field(description="The type of video")
    summary: str = pydantic.Field(description="A summary of the text in 3-5 paragraphs.")
    key_points: list[str] = pydantic.Field(description="Up to 5 key points")
    tags: list[str] = pydantic.Field(description="Up to 10 tags")

    class Config:
        extra = "forbid"


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url.lower()


def extract_video_id(url: str) -> str:
    print("Extracting video ID from URL:", url)
    parsed_url = urlparse(url)
    video_id = parse_qs(parsed_url.query).get("v")
    return video_id[0] if video_id else None


def get_transcript(video_id: str) -> str:
    try:
        transcript = yta.YouTubeTranscriptApi.get_transcript(video_id)
        return "\n".join([t["text"] for t in transcript])
    except Exception as e:
        print(f"Error getting transcript: {e}")
        return ""


def get_video_metadata(video_id: str) -> typing.Dict[str, str]:
    """Fetch video metadata using YouTube Data API v3."""
    print("Getting video metadata using YouTube API video_id:", video_id)

    # You should be logged in to Google Cloud
    api_key = os.getenv("YOUTUBE_API_KEY")
    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        # Updated parameters format - no list brackets for id
        video_response = (
            youtube.videos()
            .list(
                part="snippet,contentDetails",
                id=video_id,
            )
            .execute()
        )

        if not video_response["items"]:
            raise ValueError(f"No video found for ID: {video_id}")

        video_data = video_response["items"][0]["snippet"]

        metadata = {
            "title": video_data["title"],
            "channel": video_data["channelTitle"],
            "published_date": video_data["publishedAt"],
            "description": video_data["description"],
        }

        print("Extracted metadata:", metadata)
        return metadata

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        raise


def process_youtube_url(url: str, html_content: str = None) -> str:
    video_id = extract_video_id(url)
    # Get the video metadata
    metadata = get_video_metadata(video_id)
    transcript = get_transcript(video_id)

    data = {"folders": constants.FOLDER_STRUCTURE}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("prompts/youtube.md")

    system = template.render(**data)
    user = "Here is the content: {content}"

    # Combine metadata and transcript for LLM input
    content = f"""Title: {metadata["title"]}
Channel: {metadata["channel"]}
Published: {metadata["published_date"]}
Description: {metadata["description"]}

Transcript:
{transcript}"""
    _, output_obj = llm.call_structured_llm(video_id, content, system, user, ExpectedOutput)
    normalized_tags = [base.normalize_tag(tag) for tag in output_obj.tags]

    output_dir = os.path.join(constants.KNOWLEDGE_BASE_PATH, output_obj.folder_classification.path)
    os.makedirs(output_dir, exist_ok=True)

    data = {
        "title": metadata["title"],
        "channel": metadata["channel"],
        "summary": output_obj.summary,
        "today": datetime.datetime.now(),
        "published_date": metadata["published_date"],
        "url": url,
        "video_id": video_id,
        "key_points": "\n".join(f"* {point}" for point in output_obj.key_points),
        "tags": "\n".join([f" - {tag}" for tag in normalized_tags]),
        "output_path": output_obj.folder_classification.path,
    }
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("youtube.md")
    markdown = template.render(**data)

    filename = base.get_filename(metadata["title"], llm.get_url_hash(url))
    note_path = pathlib.Path(output_dir, f"{video_id}-{filename}")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(markdown)
    return transcript


@click.command()
@click.argument("url")
def main(url: str):
    """Extract and display YouTube video transcript."""
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    try:
        with open("data/youtube.html", "r") as input_io:
            html_content = input_io.read()
        _ = process_youtube_url(url, html_content)
        # click.echo(transcript)
    except Exception as e:
        click.echo(f"Error processing URL: {str(e)}", err=True)


if __name__ == "__main__":
    main()
