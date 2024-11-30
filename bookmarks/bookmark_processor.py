# Standard Library
import datetime
import logging
import os
import pathlib
import random
import re
import traceback
from urllib import parse
import json
import time

# Third Party
import arxiv
import jinja2
import marker.convert
import marker.models
import peewee
import PIL
import pymupdf4llm
import readabilipy
import requests
import tweepy
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Project
from bookmarks import constants
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


def get_webpage(url_hash: str, url : str, html_content: str = None) -> str:
    os.makedirs(constants.WEB_PAGE_PATH, exist_ok=True)

    html_path = os.path.join(constants.WEB_PAGE_PATH, f"{url_hash}.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            html_content = f.read()
            return html_content

    if html_content:
        with open(html_path, "w") as f:
            f.write(html_content)
        return html_content

    logger.info(f"url: {url}")
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        html_content = response.text
    elif response.status_code == 403:
        raise ValueError(f"Status=403 {url}")
    elif response.status_code == 404:
        raise ValueError(f"URL Missing: {url}")
    elif response.status_code == 500:
        raise ValueError(f"Service problem: {url}")
    else:
        logger.error(f"StatusCode: {response.status_code} URL: {url}")
        raise ValueError(f"StatusCode: {response.status_code} URL: {url}")

    with open(html_path, "w") as f:
        f.write(html_content)
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


def get_webpage_backup(url_hash, url):
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


def get_readability_backup(url_hash, url, html_content) -> models.ReadabilityPage:
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


def process_bookmark(url: str, html_content: str = None):
    os.makedirs(constants.WEB_SUMMARY_PATH, exist_ok=True)

    url_hash = llm.get_url_hash(url)

    html_content = get_webpage(url_hash, url, html_content)
    readability = get_readability(url_hash, html_content)
    print(readability.keys())

    processor = processors.get_processor(url)
    markdown = processor.generate_markdown(url, url_hash, readability['title'], readability['plain_content'], {})

    # Write the file
    title = readability['title']
    base_name = sanitize_filename(title[:50])  # Limit length to 50 chars

    # Add unique suffix (last 4 chars of hash)
    unique_suffix = url_hash[-4:]
    filename = f"{base_name}-{unique_suffix}.md"
    file_path = os.path.join(constants.WEB_SUMMARY_PATH, filename)

    with open(file_path, "w") as f:
        f.write(markdown)
    logger.info(f"Wrote markdown to {file_path}")




def bookmark(url, html_content=None, screenshot=None) -> str:
    if is_arxiv_url(url):
        return process_arxiv_url(url, html_content)
    elif is_twitter_url(url):
        return process_twitter_url(url, html_content, screenshot)
    return process_bookmark(url, html_content)


def is_arxiv_url(url: str) -> bool:
    return "arxiv.org" in url.lower()


def process_arxiv_url(url: str, html_content: str = None) -> str:
    arxiv_id = extract_arxiv_id(url)
    client = arxiv.Client()

    search = arxiv.Search(id_list=[arxiv_id])
    results = client.results(search)
    paper = next(results)

    arxiv_id = paper.entry_id.split("/")[-1]
    paper.download_pdf(dirpath=constants.RESEARCH_PAPERS_PATH, filename=f"{arxiv_id}.pdf")
    data = {
        "title": paper.title,
        "abstract": paper.summary,
        "today": datetime.datetime.now(),
        "arxiv_url": url,
        "arxiv_id": arxiv_id,
    }
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = env.get_template("academic.md")
    markdown = template.render(**data)

    safe_title = paper.title.replace(":", "-")
    # safe_title = sanitize_filename(paper.title)
    note_path = pathlib.Path(constants.RESEARCH_NOTES_PATH, f"{safe_title}.md")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(markdown)

    # Convert PDF to Markdown and store in Obsidian
    # convert_pdf_to_markdown_pymudf(arxiv_id)
    markdown_text = convert_pdf_to_markdown_marker(arxiv_id)

    # save the


def convert_pdf_to_markdown_pymudf(arxiv_id: str) -> None:
    pdf_file = os.path.join(constants.RESEARCH_PAPERS_PATH, f"{arxiv_id}.pdf")
    full_text = pymupdf4llm.to_markdown(pdf_file)

    markdown_path = pathlib.Path(constants.RESEARCH_MARKDOWN_PATH, arxiv_id, f"{arxiv_id}.md")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(full_text)


def convert_pdf_to_markdown_marker(arxiv_id: str) -> str:
    pdf_file = os.path.join(constants.RESEARCH_PAPERS_PATH, f"{arxiv_id}.pdf")
    model_lst = marker.models.load_all_models()
    full_text, images, out_meta = marker.convert.convert_single_pdf(pdf_file, model_lst)

    markdown_path = pathlib.Path(constants.RESEARCH_MARKDOWN_PATH, arxiv_id, f"{arxiv_id}.md")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(full_text)

    save_images(images, pathlib.Path(constants.RESEARCH_MARKDOWN_PATH, arxiv_id))
    return full_text


def save_images(images: dict[str, PIL.Image], output_dir: pathlib.Path) -> None:
    """Save dictionary of images to specified directory."""
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save each image
    for filename, image in images.items():
        # Create full path and save
        image_path = pathlib.Path(output_dir, filename)
        image.save(str(image_path))


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


def process_generic_url(url: str, html_content: str = None) -> str:
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


def is_twitter_url(url: str) -> bool:
    """Check if URL is from Twitter/X."""
    return any(domain in url.lower() for domain in ["twitter.com", "x.com"])


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
            if screenshot_data.startswith('data:image/png;base64,'):
                screenshot_data = screenshot_data.split(',')[1]

            # Decode base64 data
            import base64
            screenshot_bytes = base64.b64decode(screenshot_data)

            screenshot_path = pathlib.Path(constants.TWITTER_MEDIA_PATH) / f"tweet_{tweet_id}_screenshot.png"
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_bytes)
            screenshot_filename = screenshot_path.name

        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the tweet content
        tweet_data = extract_tweet_data_from_html(soup, tweet_id)
        if screenshot_filename:
            tweet_data['screenshot'] = screenshot_filename

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
        with open(markdown_path, "w", encoding='utf-8') as f:
            f.write(markdown)

        return markdown

    except Exception as e:
        logger.error(f"Failed to process tweet {tweet_id}: {str(e)}")
        raise

def extract_tweet_data_from_html(soup: BeautifulSoup, tweet_id: str) -> dict:
    """Extract tweet data from HTML."""
    # Find the main tweet article
    tweet_article = soup.find('article', attrs={'data-testid': 'tweet'})
    if not tweet_article:
        raise ValueError("Could not find tweet content")

    # Get tweet text
    text_div = tweet_article.find('div', attrs={'data-testid': 'tweetText'})
    tweet_text = text_div.get_text(strip=True) if text_div else ""
    logger.info(f"Found tweet text: {tweet_text}")

    # Get media
    media = []
    media_container = tweet_article.find('div', attrs={'data-testid': 'tweetPhoto'})
    if media_container:
        logger.info("Found photo container")
        # Handle images
        images = media_container.find_all('img')
        logger.info(f"Found {len(images)} images")
        for img in images:
            if 'src' in img.attrs:
                img_url = img['src']
                logger.info(f"Found image URL: {img_url}")
                # Filter out small thumbnails and emoji
                if 'emoji' not in img_url and 'thumb' not in img_url:
                    filename = download_media(img_url, tweet_id, constants.TWITTER_MEDIA_PATH)
                    media.append(filename)
    else:
        logger.info("No photo container found")

    # Handle videos
    video_container = tweet_article.find('div', attrs={'data-testid': 'videoPlayer'})
    if video_container:
        logger.info("Found video container")
        # Get video thumbnail
        poster = video_container.find('img')
        if poster and 'src' in poster.attrs:
            img_url = poster['src']
            logger.info(f"Found video thumbnail URL: {img_url}")
            filename = download_media(img_url, tweet_id, constants.TWITTER_MEDIA_PATH)
            media.append(filename)

        # Add video URL to the tweet data
        video_url = None
        video_element = video_container.find('video')
        if video_element and 'src' in video_element.attrs:
            video_url = video_element['src']
        elif video_container.find('a'):  # Fallback to link if direct video not found
            video_url = video_container.find('a').get('href')

        if video_url:
            logger.info(f"Found video URL: {video_url}")
            tweet_data['video_url'] = video_url
    else:
        logger.info("No video container found")

    # Let's also log the HTML structure around media elements
    logger.debug("Tweet HTML structure:")
    logger.debug(tweet_article.prettify())

    # Get author info
    author_link = tweet_article.find('a', attrs={'role': 'link', 'tabindex': '-1'})
    author = {
        'name': author_link.get_text(strip=True) if author_link else "Unknown",
        'username': extract_username_from_link(author_link['href']) if author_link and 'href' in author_link.attrs else "unknown"
    }
    logger.info(f"Found author: {author}")

    # Get tweet date (you may need to adjust the selector based on the HTML structure)
    time_element = soup.find('time')
    tweet_date = time_element.get('datetime', datetime.datetime.now().strftime('%Y-%m-%d')) if time_element else datetime.datetime.now().strftime('%Y-%m-%d')

    tweet_data = {
        'id': tweet_id,
        'url': f'https://twitter.com/{author["username"]}/status/{tweet_id}',
        'text': tweet_text,
        'media': media,
        'author': author,
        'today': datetime.datetime.now().strftime('%Y-%m-%d'),
        'tweet_date': tweet_date
    }

    logger.info(f"Final tweet data: {tweet_data}")
    return tweet_data

def extract_username_from_link(href: str) -> str:
    """Extract username from Twitter profile link."""
    parts = href.strip('/').split('/')
    return parts[-1] if parts else "unknown"

def download_media(url: str, tweet_id: str, output_dir: pathlib.Path) -> str:
    """Download media from URL and return the filename."""
    logger.info(f"Downloading media from {url}")

    # Extract extension from URL or default to .jpg
    ext = pathlib.Path(url).suffix or '.jpg'
    filename = f"tweet_{tweet_id}_{hash(url)}{ext}"
    output_path = output_dir / filename

    logger.info(f"Saving to {output_path}")

    if not output_path.exists():
        try:
            response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)})
            response.raise_for_status()

            with open(output_path, 'wb') as f:
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
        r"(?:twitter\.com|x\.com)/\w+/statuses/(\d+)"
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
        for path in TWITTER_RAW_PATH.glob("*.json"):
            path.unlink()
            logger.info(f"Removed cache file: {path}")

