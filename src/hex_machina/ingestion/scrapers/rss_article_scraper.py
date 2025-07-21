"""Base RSS article scraper for Hex Machina v2."""

from abc import abstractmethod
from typing import Optional

import feedparser

from ..models import ScrapedArticle
from .base_article_scraper import BaseArticleScraper


class RSSArticleScraper(BaseArticleScraper):
    """Base RSS scraper that handles RSS parsing logic."""

    async def parse(self, response, **kwargs):
        """Parse the response and extract article content.

        Args:
            response: Scrapy response object
            **kwargs: Additional keyword arguments
        """
        feed_url = response.meta.get("feed_url", response.url)
        self.logger.info(f"Parsing RSS feed: {feed_url}")

        try:
            # Parse RSS feed from response text
            feed = feedparser.parse(response.text)

            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {feed_url}")
                return

            self.logger.info(f"Found {len(feed.entries)} entries in feed: {feed_url}")

            for entry_index, entry in enumerate(feed.entries, 1):
                if self.check_limit():
                    self.logger.info(
                        f"Article limit reached after processing {entry_index-1} entries from feed"
                    )
                    break

                try:
                    # Extract basic info from RSS
                    title = self.parser.parse_title(entry.get("title", ""))
                    url = self.parser.parse_url(entry.get("link", entry.get("url")))
                    url_domain = self.parser.parse_url_domain(url)

                    if not title or not url:
                        self.logger.debug(
                            f"Skipping entry {entry_index}: missing title or URL"
                        )
                        continue

                    self.logger.debug(
                        f"Processing entry {entry_index}: '{title}' from {url_domain}"
                    )

                    # Check published date
                    published_date = self.parser.parse_published_date(
                        entry.get("published", entry.get("updated", ""))
                    )
                    if not self.check_published_date(published_date):
                        self.logger.debug(
                            f"Skipping old article: '{title}' from {url_domain}"
                        )
                        continue

                    # Create article with RSS data
                    article = ScrapedArticle(
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

                    # Scrape article content
                    try:
                        self.logger.debug(
                            f"Scraping article content: '{title}' from {url}"
                        )
                        enriched_article = await self.parse_article(article)
                        if enriched_article:
                            # TODO: Implement DB logic here
                            self.logger.debug(
                                f"Successfully scraped: '{title}' from {url_domain}"
                            )
                            # Increment processed_counter when yielding an article
                            self.processed_counter += 1
                            # Yield the article for Scrapy's item pipeline
                            yield enriched_article
                        else:
                            self.logger.warning(
                                f"Failed to scrape article: '{title}' from {url}"
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Error scraping article '{title}' from {url}: {e}"
                        )
                        continue

                except Exception as e:
                    self.logger.error(
                        f"Error processing entry {entry_index} from feed {feed_url}: {e}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Error parsing RSS feed {feed_url}: {e}")

    @abstractmethod
    async def parse_article(self, article: ScrapedArticle) -> Optional[ScrapedArticle]:
        """Parse individual article content.

        Args:
            article: Article object with RSS data already populated

        Returns:
            Enriched scraped article with content
        """
        pass
