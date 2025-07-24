"""Base RSS article scraper for Hex Machina v2."""

from abc import abstractmethod
from typing import Optional

import feedparser

from src.hex_machina.ingestion.article_models import ArticleModel, RSSArticlePreview
from src.hex_machina.ingestion.scrapers.base_article_scraper import BaseArticleScraper
from src.hex_machina.utils.logging_utils import get_logger


class RSSArticleScraper(BaseArticleScraper):
    """Base RSS scraper that handles RSS parsing logic."""

    def __init__(
        self,
        scraper_config,
        start_urls: Optional[list] = None,
        **kwargs,
    ):
        """Initialize the RSSArticleScraper.

        Args:
            scraper_config: The configuration object for this scraper (from parent).
            start_urls: List of URLs to start scraping from.
        """
        super().__init__(scraper_config=scraper_config, start_urls=start_urls, **kwargs)
        self._logger = get_logger(f"hex_machina.scraper.{self.name}")

    @abstractmethod
    async def parse_article(self, article):
        """Parse individual article content.

        Args:
            article: Article object with RSS data already populated
        Yields:
            Enriched scraped article(s) with content
        """
        pass

    async def parse_start_url(self, response, **kwargs):
        """Parse the response and extract article content from the start/feed URL.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        """
        feed_url = response.meta.get("feed_url", response.url)
        self._logger.info(f"Parsing RSS feed: {feed_url}")
        self._logger.info(f"Scraper config: {self.scraper_config}")

        try:
            # Parse RSS feed from response text
            feed = feedparser.parse(response.text)

            if not feed.entries:
                self._logger.warning(f"No entries found in feed: {feed_url}")

            self._logger.info(f"Found {len(feed.entries)} entries in feed: {feed_url}")

            for entry_index, entry in enumerate(feed.entries, 1):
                try:
                    # Map entry to RSSArticlePreview using the classmethod
                    rss_article_preview = RSSArticlePreview.from_feed_entry(entry)

                    if not rss_article_preview.title or not rss_article_preview.url:
                        self._logger.debug(
                            f"Skipping entry {entry_index}: missing title or URL"
                        )
                        continue

                    # Check published date
                    if not self.check_published_date(
                        rss_article_preview.published_date
                    ):
                        self._logger.debug(
                            f"Skipping old article: '{rss_article_preview.title}' from {rss_article_preview.url}"
                        )
                        continue

                    # Create article with RSS data
                    article = ArticleModel(
                        title=rss_article_preview.title,
                        url=rss_article_preview.url,
                        source_url=feed_url,
                        url_domain=rss_article_preview.url_domain,
                        published_date=rss_article_preview.published_date,
                        html_content="",  # Will be filled by parse_article
                        text_content="",  # Will be filled by parse_article
                        author=rss_article_preview.author,
                        article_metadata={
                            "summary": rss_article_preview.summary,
                            "tags": rss_article_preview.tags,
                        },
                    )

                    self._logger.debug(
                        f"Processing entry {entry_index}: '{rss_article_preview.title}' from {rss_article_preview.url_domain}"
                    )
                    async for item in self.parse_article(article):
                        yield item

                except Exception as e:
                    self._logger.error(
                        f"Error processing entry {entry_index} from feed {feed_url}: {e}"
                    )

        except Exception as e:
            self._logger.error(f"Error parsing RSS feed {feed_url}: {e}")
