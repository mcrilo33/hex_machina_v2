"""Synced Review scraper for Hex Machina v2."""

import re
from datetime import datetime
from typing import List, Optional

from src.hex_machina.ingestion.scrapers.html_article_scraper import (
    PlaywrightHtmlArticleScraper,
)


class SyncedReviewScraper(PlaywrightHtmlArticleScraper):
    """Scraper for Synced Review articles using PlaywrightHtmlArticleScraper base."""

    name = "synced_review_scraper"

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div#primary
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links within the primary div
        article_links = response.css("div#primary a::attr(href)").getall()

        # Filter and clean the links
        cleaned_links = []
        for link in article_links:
            if link and self.is_article_link(link):
                full_url = response.urljoin(link)
                cleaned_links.append(full_url)

        logger.info(f"Found {len(cleaned_links)} article links")
        return cleaned_links

    def is_article_link(self, link: str) -> bool:
        """
        Determine if a link points to an article.
        Synced Review articles have URLs like /YYYY/MM/DD/
        """
        # Synced Review article pattern: /YYYY/MM/DD/
        pattern = r"/20\d{2}/\d{2}/\d{2}/"
        return bool(re.search(pattern, link)) and "#comments" not in link

    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            response: Scrapy response object
        """
        # Synced Review doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.entry-title
        """
        title = selector.css("h1.entry-title::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from span.author a
        """
        author = selector.css("span.author a::text").get()
        if author:
            return author.strip()
        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for time.published element
        """
        date_element = selector.css("time.published::text").get()
        if date_element:
            date_str = date_element.strip()
            try:
                # Parse date in format '2025-06-16'
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                return formatted_date
            except ValueError as e:
                self._logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None
