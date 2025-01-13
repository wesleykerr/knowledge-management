# Standard Library
import hashlib
import logging
import os
from urllib.parse import urljoin
from urllib.parse import urlparse

# Third Party
import requests
from bs4 import BeautifulSoup

# Project
from bookmarks import constants

logger = logging.getLogger(__name__)


def download_and_localize_images(html_content: str, base_url: str, output_dir: str) -> str:
    """
    Downloads all images from an HTML document and updates references to be local.

    Args:
        html_content: The HTML content containing images
        base_url: The base URL of the page (for resolving relative URLs)
        output_dir: Directory where images should be saved

    Returns:
        Updated HTML content with local image references
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Create images directory if it doesn't exist
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Find all img tags
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue

        try:
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, src)

            # Skip data URLs
            if absolute_url.startswith("data:"):
                continue

            # Generate filename from URL
            url_hash = hashlib.md5(absolute_url.encode()).hexdigest()
            extension = os.path.splitext(urlparse(absolute_url).path)[1]
            if not extension:
                extension = ".jpg"  # Default extension
            filename = f"{url_hash}{extension}"
            local_path = os.path.join(images_dir, filename)

            # Download image if it doesn't exist
            if not os.path.exists(local_path):
                logger.info(f"Downloading image: {absolute_url}")
                response = requests.get(absolute_url, timeout=10)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(response.content)

            # Update image source to local path
            img["src"] = f"images/{filename}"

        except Exception as e:
            logger.error(f"Failed to download image {src}: {str(e)}")
            # Optionally remove failed images
            # img.decompose()
            continue

    return str(soup)


def process_article_images(url_hash: str, html_content: str, base_url: str) -> str:
    """
    Process article images and return updated HTML content.

    Args:
        url_hash: Hash of the URL for creating unique directories
        html_content: Original HTML content
        base_url: Base URL for resolving relative image URLs

    Returns:
        Updated HTML content with local image references
    """
    # Create article-specific directory
    article_dir = os.path.join(constants.WEB_PAGE_PATH, url_hash)
    os.makedirs(article_dir, exist_ok=True)

    # Download images and update HTML
    updated_html = download_and_localize_images(
        html_content=html_content, base_url=base_url, output_dir=article_dir
    )

    return updated_html
