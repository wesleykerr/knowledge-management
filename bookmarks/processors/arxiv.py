# Standard Library
import base64
import re
from typing import Dict
from typing import List

# Third Party
import anthropic
import httpx
from bs4 import BeautifulSoup

# Project
from bookmarks.processors import base


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


class ArxivProcessor(base.BaseProcessor):
    def __init__(self):
        super().__init__()
        self.template = "academic"

    def extract_metadata(self, html_content: str) -> Dict[str, str]:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract arXiv ID from URL or page
        arxiv_id = self._extract_arxiv_id(soup)

        metadata = {
            "authors": self._extract_authors(soup),
            "title": self._extract_title(soup),
            "arxiv_id": arxiv_id,
            "published": self._extract_date(soup),
            "abstract": self._extract_abstract(soup),
            "pdf_url": extract_pdf_link(soup, arxiv_id),
        }

        return metadata

    def _extract_arxiv_id(self, soup) -> str:
        """Extract the arXiv ID from the page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            str: The arXiv ID or empty string if not found
        """
        # Try meta tag first (most reliable)
        meta_arxiv = soup.find("meta", {"name": "citation_arxiv_id"})
        if meta_arxiv and meta_arxiv.get("content"):
            return meta_arxiv["content"]

        # Try breadcrumbs
        breadcrumbs = soup.find("div", class_="header-breadcrumbs")
        if breadcrumbs:
            match = re.search(r"arXiv:(\d+\.\d+)", breadcrumbs.text)
            if match:
                return match.group(1)

        # Try URL path as fallback
        abs_link = soup.find("link", {"rel": "canonical"})
        if abs_link and abs_link.get("href"):
            match = re.search(r"/abs/(\d+\.\d+)", abs_link["href"])
            if match:
                return match.group(1)

        return ""

    def _extract_authors(self, soup) -> List[str]:
        authors_div = soup.find("div", class_="authors")
        if authors_div:
            authors = [a.text.strip() for a in authors_div.find_all("a")]
            return authors
        return []

    def _extract_abstract(self, soup) -> str:
        abstract_div = soup.find("blockquote", class_="abstract")
        if abstract_div:
            # Remove the "Abstract: " prefix if present
            text = abstract_div.text.strip()
            return re.sub(r"^Abstract:\s*", "", text)
        return ""

    def _extract_title(self, soup) -> str:
        """Extract the paper title from the arXiv page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            str: The paper title or empty string if not found
        """
        # Try the h1 title first (newer pages)
        title_h1 = soup.find("h1", class_="title")
        if title_h1:
            # Remove "Title:" prefix if present
            text = title_h1.text.strip()
            return re.sub(r"^Title:\s*", "", text)

        # Try alternative title location (older pages)
        title_div = soup.find("div", class_="title")
        if title_div:
            text = title_div.text.strip()
            return re.sub(r"^Title:\s*", "", text)

        return ""

    def _extract_date(self, soup) -> str:
        """Extract the publication date from the arXiv page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            str: The publication date in YYYY-MM-DD format or empty string if not found
        """
        # Try to find date in meta tags first (more reliable)
        meta_date = soup.find("meta", {"name": "citation_date"})
        if meta_date and meta_date.get("content"):
            return meta_date["content"]

        # Try to find date in submission history
        history = soup.find("div", class_="submission-history")
        if history:
            # Look for the first submission date
            date_match = re.search(r"\[v1\] ([A-Za-z]{3}, \d{1,2} [A-Za-z]{3} \d{4})", history.text)
            if date_match:
                try:
                    # Convert to YYYY-MM-DD format
                    # Standard Library
                    from datetime import datetime

                    date_str = date_match.group(1)
                    date_obj = datetime.strptime(date_str, "%a, %d %b %Y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        # Try dateline div as fallback
        dateline = soup.find("div", class_="dateline")
        if dateline:
            # Extract date pattern like "Submitted on 13 March 2024"
            date_match = re.search(r"Submitted on (\d{1,2} [A-Za-z]+ \d{4})", dateline.text)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    date_obj = datetime.strptime(date_str, "%d %B %Y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass

        return ""

    def generate_markdown(self, content: str, metadata: Dict[str, str]) -> str:
        # Use the abstract as the primary content for summarization
        abstract = metadata.get("abstract", content)
        authors = ", ".join(metadata.get("authors", []))
        categories = ", ".join(metadata.get("categories", []))

        return f"""Analyze this academic paper from arXiv:
Title: {metadata.get('title', 'Unknown')}
Authors: {authors}
Categories: {categories}
arXiv ID: {metadata.get('arxiv_id', 'Unknown')}
Published: {metadata.get('published', 'Unknown')}

Abstract:
{abstract}

Please provide:
1. Key research objectives
2. Main methodology/approach
3. Primary findings/contributions
4. Potential applications
5. Technical complexity level

Keep the summary technical but accessible to practitioners in the field.
"""

    def process_tags(self, tags: List[str]) -> List[str]:
        # Add academic and research tags, plus any arXiv categories
        base_tags = ["academic", "research", "arxiv"]
        return list(set(tags + base_tags))
