"""Meta scraper for Hex Machina v2."""

from datetime import datetime
from typing import List, Optional

from src.hex_machina.ingestion.scrapers.base.html_article_scraper import (
    ScrapyHtmlArticleScraper,
)


class MetaScraper(ScrapyHtmlArticleScraper):
    """Scraper for Meta AI blog articles using ScrapyHtmlArticleScraper base."""

    name = "meta_scraper"

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags with pattern /blog/
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links with /blog/ pattern
        article_links = response.css("a[href*='/blog/']::attr(href)").getall()

        # Filter and clean the links
        cleaned_links = []
        for link in article_links:
            if link and self.is_article_link(link):
                full_url = response.urljoin(link)
                cleaned_links.append(full_url)

        logger.info(f"Found {len(cleaned_links)} article links")
        return cleaned_links[1:]  # Skip first link as it's typically the main blog page

    def is_article_link(self, link: str) -> bool:
        """
        Determine if a link points to an article.
        Meta AI blog articles contain /blog/ in the URL
        """
        return "/blog/" in link and "https://ai.meta.com/blog/" != link

    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            response: Scrapy response object
        """
        # Meta AI blog doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1 span
        """
        title = selector.css("h1 span::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        No author information available for Meta AI blog articles
        """
        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for span element with date format 'June 4, 2025'
        """
        # Look for span elements that might contain dates
        date_spans = selector.css("span::text").getall()

        for span_text in date_spans:
            if span_text:
                date_str = span_text.strip()
                try:
                    # Parse date in format 'June 4, 2025'
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                    return formatted_date
                except ValueError:
                    # Continue checking other spans if this one doesn't match the format
                    continue

        self._logger.warning("No valid date found in span elements")
        return None
