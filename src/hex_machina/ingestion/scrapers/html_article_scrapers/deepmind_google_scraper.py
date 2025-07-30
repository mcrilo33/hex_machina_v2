"""DeepMind Google scraper for Hex Machina v2."""

import re
from typing import List, Optional

from src.hex_machina.ingestion.scrapers.html_article_scraper import (
    ScrapyHtmlArticleScraper,
)
from src.hex_machina.utils.date_parser import DateParser


class DeepMindGoogleScraper(ScrapyHtmlArticleScraper):
    """Scraper for DeepMind Google articles using ScrapyHtmlArticleScraper base."""

    name = "deepmind_google_scraper"

    def extract_article_links(self, selector) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags and filters for DeepMind blog articles.
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links
        article_links = selector.css("a::attr(href)").getall()

        # Filter and clean the links
        cleaned_links = []

        for link in article_links:
            if not link:
                continue

            # Handle localhost test URLs
            if link.startswith("http://localhost:8000/"):
                # For test URLs, accept any localhost article
                if "article" in link and link.endswith(".html"):
                    full_url = selector.urljoin(link)
                    cleaned_links.append(full_url)
                    continue

            # Handle research.google URLs
            if link.startswith("https://research.google/blog/"):
                # Skip navigation and non-article links
                if any(
                    skip in link for skip in ["#page-content", "/rss", "javascript(0)"]
                ):
                    continue

                parts = link.rstrip("/").split("/")
                if len(parts) == 5 and not parts[4].isdigit():
                    full_url = selector.urljoin(link)
                    cleaned_links.append(full_url)

        logger.info(f"Found {len(cleaned_links)} article links")
        return cleaned_links

    def load_more_articles(self, selector) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            selector: parsel selector object
        """
        # DeepMind Google blog doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.glue-headline.

        Args:
            selector: parsel selector object

        Returns:
            Title string or None if not found
        """
        title = selector.css("h1::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from all div.author-obj a elements.

        Args:
            selector: parsel selector object

        Returns:
            Author string or None if not found
        """
        author_elements = selector.css("div.author-obj a::text").getall()
        if author_elements:
            authors = [author.strip() for author in author_elements if author.strip()]
            return ", ".join(authors)
        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for div.published_date element.

        Args:
            selector: parsel selector object

        Returns:
            Published date string in RFC 2822 format or None if not found
        """
        logger = self._logger
        match = re.search(r'date="(.*?)"', selector.get())
        date_element = match.group(1) if match else None

        if date_element:
            date_str = date_element.strip()
            try:
                formatted_date = DateParser.parse_published_date(date_str)
                return formatted_date
            except ValueError as e:
                logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None
