"""HAI scraper for Hex Machina v2."""

from datetime import datetime
from typing import List, Optional

from parsel import Selector

from src.hex_machina.ingestion.scrapers.base.html_article_scraper import (
    ScrapyHtmlArticleScraper,
)


class HAIScraper(ScrapyHtmlArticleScraper):
    """Scraper for Stanford HAI articles using ScrapyHtmlArticleScraper base."""

    name = "hai_scraper"

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags with href containing /news/
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links with /news/ pattern
        article_links = response.css("a[href*='/news/']::attr(href)").getall()

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
        Stanford HAI articles contain /news/ in the URL
        """
        return "/news/" in link and "filterBy" not in link

    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            response: Scrapy response object
        """
        # Stanford HAI blog doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from the first h1
        """
        title = selector.css("h1:first-of-type::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        No author information available for Stanford HAI articles
        """
        return None

    def get_text_content(self, html_content) -> Optional[str]:
        """
        Extract the main text content from the article page.
        Gets all text from p elements
        """
        selector = Selector(text=html_content)
        # Get all text from p elements
        p_divs = selector.css("p::text").getall()

        if p_divs:
            # Join all paragraph text with newlines
            content = "\n\n".join([text.strip() for text in p_divs if text.strip()])
            return content if content else None

        self._logger.warning("No text content found in p elements")
        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Looks for div element with date format 'June 23, 2025'
        """
        # Look for div elements that might contain dates
        date_divs = selector.css("div::text").getall()

        for div_text in date_divs:
            if div_text:
                date_str = div_text.strip()
                try:
                    # Parse date in format 'June 23, 2025'
                    parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                    formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                    return formatted_date
                except ValueError:
                    # Continue checking other divs if this one doesn't match the format
                    continue

        self._logger.warning("No valid date found in div elements")
        return None
