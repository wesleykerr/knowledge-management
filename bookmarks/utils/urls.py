# Standard Library
import logging
import random

# Third Party
import requests

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]


def get_content(url: str) -> str:
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

    return html_content
