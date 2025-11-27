# Standard Library
import base64
import datetime
import json
import logging
import os
import pathlib
import random
import re

# Third Party
import jinja2
import requests
from bs4 import BeautifulSoup

# Project
from bookmarks import constants
from bookmarks.utils.urls import USER_AGENTS

logger = logging.getLogger(__name__)


def is_twitter_url(url: str) -> bool:
    """Check if URL is from Twitter/X."""
    return any(domain in url.lower() for domain in ["twitter.com", "https://x.com"])


def process_twitter_url(url: str, html_content: str = None, screenshot_data: str = None) -> str:
    """Process Twitter/X URLs by extracting data from HTML content."""
    # Ensure directories exist
    os.makedirs(constants.TWITTER_MEDIA_PATH, exist_ok=True)
    os.makedirs(constants.TWITTER_JSON_PATH, exist_ok=True)
    os.makedirs(constants.TWITTER_NOTES_PATH, exist_ok=True)

    # Get tweet ID from URL
    tweet_id = extract_tweet_id(url)
    logger.info(f"Processing tweet {tweet_id}")

    try:
        if not html_content:
            raise ValueError("HTML content is required for processing Twitter/X URLs")

        # Save screenshot if provided
        screenshot_filename = None
        if screenshot_data:
            # Remove the data URL prefix if present
            if screenshot_data.startswith("data:image/png;base64,"):
                screenshot_data = screenshot_data.split(",")[1]

            screenshot_bytes = base64.b64decode(screenshot_data)
            screenshot_path = (
                pathlib.Path(constants.TWITTER_MEDIA_PATH) / f"tweet_{tweet_id}_screenshot.png"
            )
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)
            screenshot_filename = screenshot_path.name

        # Parse the HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Find the tweet content
        tweet_data = extract_tweet_data_from_html(soup, tweet_id)
        if screenshot_filename:
            tweet_data["screenshot"] = screenshot_filename

        # Save the processed data
        json_path = os.path.join(constants.TWITTER_JSON_PATH, f"{tweet_id}.json")
        with open(json_path, "w") as f:
            json.dump(tweet_data, f, indent=2)

        # Create markdown
        env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
        template = env.get_template("twitter.md")
        markdown = template.render(**tweet_data)

        # Create a sanitized filename and save markdown
        filename = f"tweet-{tweet_id}.md"
        markdown_path = os.path.join(constants.TWITTER_NOTES_PATH, filename)

        logger.info(f"Writing markdown to {markdown_path}")
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        return markdown

    except Exception as e:
        logger.error(f"Failed to process tweet {tweet_id}: {str(e)}")
        raise


def extract_tweet_data_from_html(soup: BeautifulSoup, tweet_id: str) -> dict:
    """Extract tweet data from HTML."""
    # Find the main tweet article
    tweet_article = soup.find("article", attrs={"data-testid": "tweet"})
    if not tweet_article:
        raise ValueError("Could not find tweet content")

    # Get tweet text
    text_div = tweet_article.find("div", attrs={"data-testid": "tweetText"})
    tweet_text = text_div.get_text(strip=True) if text_div else ""
    logger.info(f"Found tweet text: {tweet_text}")

    # Get media
    media = []
    media_container = tweet_article.find("div", attrs={"data-testid": "tweetPhoto"})
    if media_container:
        logger.info("Found photo container")
        # Handle images
        images = media_container.find_all("img")
        logger.info(f"Found {len(images)} images")
        for img in images:
            if "src" in img.attrs:
                img_url = img["src"]
                logger.info(f"Found image URL: {img_url}")
                # Filter out small thumbnails and emoji
                if "emoji" not in img_url and "thumb" not in img_url:
                    filename = download_media(img_url, tweet_id, constants.TWITTER_MEDIA_PATH)
                    media.append(filename)
    else:
        logger.info("No photo container found")

    # Handle videos
    video_url = None
    video_container = tweet_article.find("div", attrs={"data-testid": "videoPlayer"})
    if video_container:
        logger.info("Found video container")
        # Get video thumbnail
        poster = video_container.find("img")
        if poster and "src" in poster.attrs:
            img_url = poster["src"]
            logger.info(f"Found video thumbnail URL: {img_url}")
            filename = download_media(img_url, tweet_id, constants.TWITTER_MEDIA_PATH)
            media.append(filename)

        # Add video URL to the tweet data
        video_element = video_container.find("video")
        if video_element and "src" in video_element.attrs:
            video_url = video_element["src"]
        elif video_container.find("a"):  # Fallback to link if direct video not found
            video_url = video_container.find("a").get("href")

    else:
        logger.info("No video container found")

    # Let's also log the HTML structure around media elements
    logger.debug("Tweet HTML structure:")
    logger.debug(tweet_article.prettify())

    # Get author info
    author_link = tweet_article.find("a", attrs={"role": "link", "tabindex": "-1"})
    author = {
        "name": author_link.get_text(strip=True) if author_link else "Unknown",
        "username": (
            extract_username_from_link(author_link["href"])
            if author_link and "href" in author_link.attrs
            else "unknown"
        ),
    }
    logger.info(f"Found author: {author}")

    # Get tweet date (you may need to adjust the selector based on the HTML structure)
    time_element = soup.find("time")
    tweet_date = (
        time_element.get("datetime", datetime.datetime.now().strftime("%Y-%m-%d"))
        if time_element
        else datetime.datetime.now().strftime("%Y-%m-%d")
    )

    tweet_data = {
        "id": tweet_id,
        "url": f"https://twitter.com/{author['username']}/status/{tweet_id}",
        "text": tweet_text,
        "media": media,
        "author": author,
        "today": datetime.datetime.now().strftime("%Y-%m-%d"),
        "tweet_date": tweet_date,
    }
    if video_url:
        logger.info(f"Found video URL: {video_url}")
        tweet_data["video_url"] = video_url

    logger.info(f"Final tweet data: {tweet_data}")
    return tweet_data


def extract_username_from_link(href: str) -> str:
    """Extract username from Twitter profile link."""
    parts = href.strip("/").split("/")
    return parts[-1] if parts else "unknown"


def download_media(url: str, tweet_id: str, output_dir: pathlib.Path) -> str:
    """Download media from URL and return the filename."""
    logger.info(f"Downloading media from {url}")

    # Extract extension from URL or default to .jpg
    ext = pathlib.Path(url).suffix or ".jpg"
    filename = f"tweet_{tweet_id}_{hash(url)}{ext}"
    output_path = pathlib.Path(os.path.join(output_dir, filename))

    logger.info(f"Saving to {output_path}")

    if not output_path.exists():
        try:
            response = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)})
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded media to {filename}")
        except Exception as e:
            logger.error(f"Failed to download media: {str(e)}")
            return None

    return filename


def extract_tweet_id(url: str) -> str:
    """Extract tweet ID from Twitter/X URL."""
    patterns = [
        r"(?:twitter\.com|x\.com)/\w+/status/(\d+)",
        r"(?:twitter\.com|x\.com)/\w+/statuses/(\d+)",
    ]

    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    raise ValueError(f"Could not extract Tweet ID from URL: {url}")


def clear_twitter_cache(older_than_days: int = None):
    """Clear cached Twitter API responses.

    Args:
        older_than_days: If provided, only clear cache entries older than this many days
    """
    if older_than_days is not None:
        cutoff = datetime.datetime.now() - datetime.timedelta(days=older_than_days)
        for path in constants.TWITTER_RAW_PATH.glob("*.json"):
            if datetime.datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink()
                logger.info(f"Removed old cache file: {path}")
    else:
        for path in constants.TWITTER_RAW_PATH.glob("*.json"):
            path.unlink()
            logger.info(f"Removed cache file: {path}")
