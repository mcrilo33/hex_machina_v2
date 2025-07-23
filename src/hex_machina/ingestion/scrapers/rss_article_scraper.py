"""Base RSS article scraper for Hex Machina v2."""

import logging
import os
from abc import abstractmethod
from typing import Optional

import feedparser
import yaml

from ..models import ArticleModel
from .base_article_scraper import BaseArticleScraper


class RSSArticleScraper(BaseArticleScraper):
    """Base RSS scraper that handles RSS parsing logic."""

    def __init__(self, *args, config_path: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(f"hex_machina.scraper.{self.name}")
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "../../../config/scraping_config.yaml"
        )
        self.scraper_config = self._load_scraper_config()

    def _load_scraper_config(self) -> dict:
        """Load per-scraper config from YAML file based on class name."""
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        # Use the class name as the key (lowercase)
        key = self.__class__.__name__.lower()
        # Try both class name and explicit name attribute
        config_section = config.get(key) or config.get(getattr(self, "name", key)) or {}
        return config_section

    async def parse_start_url(self, response, **kwargs) -> None:
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
                return

            self._logger.info(f"Found {len(feed.entries)} entries in feed: {feed_url}")

            for entry_index, entry in enumerate(feed.entries, 1):
                try:
                    # Extract basic info from RSS
                    title = self.parser.parse_title(entry.get("title", ""))
                    url = self.parser.parse_url(entry.get("link", entry.get("url")))
                    url_domain = self.parser.parse_url_domain(url)

                    if not title or not url:
                        self._logger.debug(
                            f"Skipping entry {entry_index}: missing title or URL"
                        )
                        continue

                    # Check published date
                    published_date = self.parser.parse_published_date(
                        entry.get("published", entry.get("updated", ""))
                    )
                    if not self.check_published_date(published_date):
                        self._logger.debug(
                            f"Skipping old article: '{title}' from {url_domain}"
                        )
                        continue

                    # Create article with RSS data
                    article = ArticleModel(
                        title=title,
                        url=url,
                        source_url=feed_url,
                        url_domain=url_domain,
                        published_date=published_date,
                        html_content="",  # Will be filled by parse_article
                        text_content="",  # Will be filled by parse_article
                        author=self.parser.parse_author(
                            entry.get("author", entry.get("dc_creator", ""))
                        ),
                        article_metadata={
                            "summary": self.parser.parse_summary(
                                entry.get("summary", entry.get("description", ""))
                            ),
                            "tags": self.parser.parse_tags(
                                entry.get("tags", entry.get("category", ""))
                            ),
                        },
                    )

                    self._logger.debug(
                        f"Processing entry {entry_index}: '{title}' from {url_domain}"
                    )
                    async for item in self.parse_article(article):
                        yield item

                except Exception as e:
                    self._logger.error(
                        f"Error processing entry {entry_index} from feed {feed_url}: {e}"
                    )
                    raise ValueError(f"RSS feed processing error {e}")
                    continue

        except Exception as e:
            self._logger.error(f"Error parsing RSS feed {feed_url}: {e}")
            raise ValueError(f"RSS feed parsing error {e}")

    @abstractmethod
    async def parse_article(self, article: ArticleModel) -> Optional[ArticleModel]:
        """Parse individual article content.

        Args:
            article: Article object with RSS data already populated
            user_agent: User agent string to use for browser context (optional)

        Returns:
            Enriched scraped article with content
        """
        pass
