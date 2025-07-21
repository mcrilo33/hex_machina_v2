"""Logging utilities for Hex Machina v2."""

import logging
import re


class TruncatingLogFormatter(logging.Formatter):
    """Custom log formatter that truncates long field values in logs.

    This is particularly useful for Scrapy logs that contain long HTML content
    or other verbose data that clutters the log output.
    """

    def __init__(self, max_field_length: int = 200):
        """Initialize the formatter.

        Args:
            max_field_length: Maximum length for field values in logs
        """
        super().__init__()
        self.max_field_length = max_field_length

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, truncating long field values.

        Args:
            record: Log record to format

        Returns:
            Formatted log message with truncated fields
        """
        # Check if this is a Scrapy scraped item log
        if hasattr(record, "msg") and isinstance(record.msg, str):
            if "Scraped from" in record.msg:
                # Truncate long field values in the message
                record.msg = self._truncate_scraped_item(record.msg)

        return super().format(record)

    def _truncate_scraped_item(self, message: str) -> str:
        """Truncate long field values in scraped item messages.

        Args:
            message: Original log message

        Returns:
            Message with truncated field values
        """
        # Use regex to find and truncate field values
        # Pattern: field_name='value' or field_name=value
        pattern = r"(\w+)='([^']*)'|(\w+)=([^'\s,)]+)"

        def replace_match(match):
            field_name = match.group(1) or match.group(3)
            field_value = match.group(2) or match.group(4)

            # Skip certain fields that should not be truncated
            if field_name in [
                "title",
                "url",
                "source_url",
                "url_domain",
                "published_date",
            ]:
                return match.group(0)

            # Truncate long values
            if len(field_value) > self.max_field_length:
                if match.group(2):  # Quoted value
                    return f"{field_name}='{field_value[:self.max_field_length]}...[truncated]'"
                else:  # Unquoted value
                    return f"{field_name}={field_value[:self.max_field_length]}...[truncated]"

            return match.group(0)

        return re.sub(pattern, replace_match, message)


def setup_truncating_logger(
    logger_name: str, max_field_length: int = 200, level: int = logging.INFO
) -> logging.Logger:
    """Set up a logger with truncating formatter.

    Args:
        logger_name: Name of the logger to configure
        max_field_length: Maximum length for field values
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create new handler with truncating formatter
    handler = logging.StreamHandler()
    handler.setFormatter(TruncatingLogFormatter(max_field_length=max_field_length))
    logger.addHandler(handler)

    return logger


def configure_scrapy_logging(max_field_length: int = 100):
    """Configure Scrapy logging to truncate long field values.

    Args:
        max_field_length: Maximum length for field values in logs
    """
    # Get the Scrapy logger
    scrapy_logger = logging.getLogger("scrapy")

    # Remove existing handlers
    for handler in scrapy_logger.handlers[:]:
        scrapy_logger.removeHandler(handler)

    # Create new handler with truncating formatter
    handler = logging.StreamHandler()
    handler.setFormatter(TruncatingLogFormatter(max_field_length=max_field_length))
    scrapy_logger.addHandler(handler)

    # Also configure the core scraper logger specifically
    scraper_logger = logging.getLogger("scrapy.core.scraper")
    for handler in scraper_logger.handlers[:]:
        scraper_logger.removeHandler(handler)

    scraper_handler = logging.StreamHandler()
    scraper_handler.setFormatter(
        TruncatingLogFormatter(max_field_length=max_field_length)
    )
    scraper_logger.addHandler(scraper_handler)
