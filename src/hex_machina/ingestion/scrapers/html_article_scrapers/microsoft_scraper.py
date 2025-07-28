"""Microsoft AI news scraper for Hex Machina v2."""

import re
from datetime import datetime
from typing import List, Optional

from src.hex_machina.ingestion.scrapers.html_article_scraper import (
    PlaywrightHtmlArticleScraper,
)


class MicrosoftScraper(PlaywrightHtmlArticleScraper):
    """Scraper for Microsoft AI news articles using PlaywrightHtmlArticleScraper base."""

    name = "microsoft_scraper"

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags in the second div.wp-block-columns
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links in the second div.wp-block-columns
        article_links = response.css(
            "div.wp-block-columns:nth-of-type(2) a::attr(href)"
        ).getall()

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
        Microsoft news articles should be valid URLs
        """
        return link and link.startswith(("http", "/")) and "/topics/" not in link

    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            response: Scrapy response object
        """
        # Microsoft news doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from the first h2 in <article>
        """
        # Get the first h2 element specifically
        first_h2 = selector.css("article h2").get()

        if not first_h2:
            return None

        # Create a new selector from just the first h2 element
        from parsel import Selector

        h2_selector = Selector(text=first_h2)

        # Get all span text from within this specific h2 only
        title_spans = h2_selector.css("split-text span::text").getall()

        if title_spans:
            # Join all span text to form the complete title
            title = " ".join([span.strip() for span in title_spans if span.strip()])
            return title if title else None

        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        Searches for pattern 'written by {author}' in span::text within
        first div[role="paragraph"]
        """
        # Get all span text from the first div[role="paragraph"]
        paragraph_spans = selector.css(
            'div[role="paragraph"] split-text::text'
        ).getall()

        if paragraph_spans:
            # Join all span text and search for 'written by' pattern
            full_text = " ".join(
                [span.strip() for span in paragraph_spans if span.strip()]
            )

            # Search for 'written by {author}' pattern
            match = re.search(r"written by\s+([^,\.]+)", full_text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                return author

        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Searches for pattern 'June 16 2025' in span::text within
        first div[role="paragraph"]
        """
        # Get all span text from the first div[role="paragraph"]
        paragraph_spans = selector.css(
            'div[role="paragraph"] split-text::text'
        ).getall()

        if paragraph_spans:
            # Join all span text and search for date pattern
            full_text = " ".join(
                [span.strip() for span in paragraph_spans if span.strip()]
            )

            # Search for date pattern like 'June 16 2025'
            date_pattern = r"([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})"
            match = re.search(date_pattern, full_text)

            if match:
                month, day, year = match.groups()
                try:
                    # Parse date in format 'June 16 2025'
                    date_str = f"{month} {day}, {year}"
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                    return formatted_date
                except ValueError as e:
                    self._logger.warning(f"Failed to parse date '{date_str}': {e}")

        self._logger.warning("No valid date found in paragraph spans")
        return None
