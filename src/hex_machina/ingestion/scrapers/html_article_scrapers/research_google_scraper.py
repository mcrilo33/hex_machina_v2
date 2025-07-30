"""Google Research blog scraper for Hex Machina v2."""

from datetime import datetime
from typing import List, Optional

from src.hex_machina.ingestion.scrapers.html_article_scraper import (
    ScrapyHtmlArticleScraper,
)


class ResearchGoogleScraper(ScrapyHtmlArticleScraper):
    """Scraper for Google Research blog articles using ScrapyHtmlArticleScraper base."""

    name = "research_google_scraper"

    def extract_article_links(self, response) -> List[str]:
        """
        Extract article links from the main page.
        Looks for all <a> tags within div.list-wrapper
        """
        # Logger is inherited from BaseArticleScraper
        logger = self._logger

        # Select all article links within the list-wrapper div
        article_links = response.css("div.list-wrapper a::attr(href)").getall()

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
        Google Research articles contain /blog/ in the URL
        """
        return "/blog/" in link

    def load_more_articles(self, response) -> None:
        """Load more articles if needed (pagination, infinite scroll, etc.).

        Args:
            response: Scrapy response object
        """
        # Google Research doesn't typically need pagination
        # This method can be left empty or implement pagination if needed
        pass

    def get_title(self, selector) -> Optional[str]:
        """
        Extract the title from the article page.
        Gets the text from h1.headline-1
        """
        title = selector.css("h1.headline-1::text").get()
        if title:
            return title.strip()
        return None

    def get_author(self, selector) -> Optional[str]:
        """
        Extract the author from the article page.
        Gets the text from the second <p> in div.basic-hero--blog-detail__description
        """
        # Get the second <p> element within the description div
        author_elements = selector.css(
            "div.basic-hero--blog-detail__description p::text"
        ).getall()
        if len(author_elements) >= 2:
            author = author_elements[1].strip()
            return author
        return None

    def get_published_date(self, selector) -> Optional[str]:
        """
        Extract the published date from the article page.
        Gets the text from the first <p> in div.basic-hero--blog-detail__description
        """
        # Get the first <p> element within the description div
        date_elements = selector.css(
            "div.basic-hero--blog-detail__description p::text"
        ).getall()
        if date_elements:
            date_str = date_elements[0].strip()
            try:
                # Parse date in format 'June 23, 2025'
                parsed_date = datetime.strptime(date_str, "%B %d, %Y")
                formatted_date = parsed_date.strftime("%a, %d %b %Y 12:00:01 +0000")
                return formatted_date
            except ValueError as e:
                self._logger.warning(f"Failed to parse date '{date_str}': {e}")
                return date_str
        return None
