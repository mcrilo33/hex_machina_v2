"""Custom log formatter for Hex Machina v2 that truncates long field values."""

import logging

from scrapy import logformatter


class TruncatingLogFormatter(logformatter.LogFormatter):
    """Custom log formatter that truncates long field values in scraped items."""

    def __init__(self, max_field_length: int = 100):
        """Initialize the formatter.

        Args:
            max_field_length: Maximum length for field values in logs
        """
        super().__init__()
        self.max_field_length = max_field_length

    def scraped(self, item, response, spider):
        """Log a message when an item is scraped by a spider.

        Args:
            item: The scraped item
            response: The response that was used to scrape the item
            spider: The spider that scraped the item

        Returns:
            Dictionary with level, msg, and args for logging
        """
        # Create a truncated version of the item for logging
        truncated_item = self._truncate_item_fields(item)

        return {
            "level": logging.DEBUG,
            "msg": "Scraped from %(response)s\n%(item)s",
            "args": {
                "response": response,
                "item": truncated_item,
            },
        }

    def _truncate_item_fields(self, item):
        """Truncate long field values in an item.

        Args:
            item: The item to truncate

        Returns:
            Item with truncated field values
        """
        if hasattr(item, "fields"):
            # For ScrapedArticle objects
            truncated_item = type(item)(
                title=getattr(item, "title", ""),
                url=getattr(item, "url", ""),
                source_url=getattr(item, "source_url", ""),
                url_domain=getattr(item, "url_domain", ""),
                published_date=getattr(item, "published_date", ""),
                html_content=self._truncate_content(getattr(item, "html_content", "")),
                text_content=self._truncate_content(getattr(item, "text_content", "")),
                author=getattr(item, "author", ""),
                metadata=self._truncate_nested_dict(getattr(item, "metadata", {})),
            )
        else:
            # For dictionary-like items
            truncated_item = dict(item)
            if "html_content" in truncated_item:
                truncated_item["html_content"] = self._truncate_content(
                    truncated_item["html_content"]
                )
            if "text_content" in truncated_item:
                truncated_item["text_content"] = self._truncate_content(
                    truncated_item["text_content"]
                )
            if "metadata" in truncated_item:
                truncated_item["metadata"] = self._truncate_nested_dict(
                    truncated_item["metadata"]
                )

        return truncated_item

    def _truncate_content(self, content: str) -> str:
        """Truncate content if it's too long.

        Args:
            content: Content to truncate

        Returns:
            Truncated content with indicator
        """
        if not content:
            return content
        if len(content) > self.max_field_length:
            return content[: self.max_field_length] + "...[truncated]"
        return content

    def _truncate_nested_dict(self, data):
        """Recursively truncate long string values in nested dictionaries and lists.

        Args:
            data: Data structure to truncate (dict, list, or primitive)

        Returns:
            Truncated data structure
        """
        if isinstance(data, dict):
            return {
                key: self._truncate_nested_dict(value) for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._truncate_nested_dict(item) for item in data]
        elif isinstance(data, str):
            return self._truncate_content(data)
        else:
            return data
