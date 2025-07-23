"""Centralized date parsing utilities for Hex Machina v2."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Union


class DateParser:
    """Centralized date parser using ISO 8601 format."""

    # Common date formats to support
    DATE_FORMATS = [
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without timezone
        "%Y-%m-%d %H:%M:%S%z",  # ISO-like with space
        "%Y-%m-%d %H:%M:%S",  # ISO-like without timezone
        "%Y-%m-%d",  # Date only
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 (RSS standard)
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
        "%a, %d %b %Y %H:%M:%S",  # RFC 822 without timezone
        "%d %b %Y %H:%M:%S %z",  # RFC 822 without day name
        "%d %b %Y %H:%M:%S",  # RFC 822 without timezone
        "%Y/%m/%d %H:%M:%S",  # Slash format
        "%Y/%m/%d",  # Slash date only
        "%m/%d/%Y %H:%M:%S",  # US format
        "%m/%d/%Y",  # US date only
    ]

    @classmethod
    def parse_date(cls, date_input: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse date from various formats to ISO 8601 datetime.

        Args:
            date_input: Date string, datetime object, or None

        Returns:
            Parsed datetime object in UTC timezone, or None if parsing fails

        Examples:
            >>> DateParser.parse_date("2024-01-15T10:30:00Z")
            datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

            >>> DateParser.parse_date("Mon, 15 Jan 2024 10:30:00 +0000")
            datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

            >>> DateParser.parse_date("2024-01-15")
            datetime.datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        """
        if date_input is None:
            return None

        # If already a datetime object, ensure it's in UTC
        if isinstance(date_input, datetime):
            return cls._ensure_utc(date_input)

        if not isinstance(date_input, str):
            return None

        date_str = date_input.strip()
        if not date_str:
            return None

        # Try our custom format parsing
        parsed_date = cls._parse_custom_formats(date_str)
        if parsed_date:
            return parsed_date

        # Try to extract date from common patterns
        parsed_date = cls._extract_date_patterns(date_str)
        if parsed_date:
            return parsed_date

        return None

    @classmethod
    def parse_published_date(cls, date_str: str) -> Optional[datetime]:
        """Parse published date from RSS feed entries.

        Args:
            date_str: Date string from RSS feed

        Returns:
            Parsed datetime object in UTC timezone, or None if parsing fails
        """
        return cls.parse_date(date_str)

    @classmethod
    def compare_dates(
        cls, date1: Union[str, datetime, None], date2: Union[str, datetime, None]
    ) -> int:
        """Compare two dates with proper timezone handling.

        Args:
            date1: First date (string, datetime, or None)
            date2: Second date (string, datetime, or None)

        Returns:
            -1 if date1 < date2, 0 if date1 == date2, 1 if date1 > date2
            Returns 0 if either date is None or invalid
        """
        parsed_date1 = cls.parse_date(date1)
        parsed_date2 = cls.parse_date(date2)

        if parsed_date1 is None or parsed_date2 is None:
            return 0

        if parsed_date1 < parsed_date2:
            return -1
        elif parsed_date1 > parsed_date2:
            return 1
        else:
            return 0

    @classmethod
    def is_date_after_threshold(
        cls, date: Union[str, datetime, None], threshold: Union[str, datetime, None]
    ) -> bool:
        """Check if a date is after (or equal to) a threshold date.

        Args:
            date: Date to check
            threshold: Threshold date

        Returns:
            True if date is after or equal to threshold, False otherwise
        """
        if date is None or threshold is None:
            return True  # Allow dates without threshold comparison

        comparison = cls.compare_dates(date, threshold)
        return comparison >= 0

    @classmethod
    def _parse_custom_formats(cls, date_str: str) -> Optional[datetime]:
        """Parse date using predefined format patterns."""
        for fmt in cls.DATE_FORMATS:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return cls._ensure_utc(parsed)
            except ValueError:
                continue

        return None

    @classmethod
    def _extract_date_patterns(cls, date_str: str) -> Optional[datetime]:
        """Extract date from common patterns using regex."""

        # ISO 8601 pattern with optional timezone
        iso_pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\.\d+)?(?:Z|([+-]\d{2}:?\d{2})?)"
        match = re.match(iso_pattern, date_str)
        if match:
            try:
                year, month, day, hour, minute, second = map(int, match.groups()[:6])
                tz_str = match.group(7)

                dt = datetime(year, month, day, hour, minute, second)
                if tz_str:
                    dt = cls._apply_timezone(dt, tz_str)

                return cls._ensure_utc(dt)
            except (ValueError, TypeError):
                pass

        # Date-only pattern (YYYY-MM-DD)
        date_pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})"
        match = re.match(date_pattern, date_str)
        if match:
            try:
                year, month, day = map(int, match.groups())
                dt = datetime(year, month, day)
                return cls._ensure_utc(dt)
            except (ValueError, TypeError):
                pass

        return None

    @classmethod
    def _apply_timezone(cls, dt: datetime, tz_str: str) -> datetime:
        """Apply timezone offset to datetime."""
        if tz_str == "Z":
            return dt.replace(tzinfo=timezone.utc)

        # Parse timezone offset (+/-HH:MM or +/-HHMM)
        tz_str = tz_str.replace(":", "")
        sign = tz_str[0]
        hours = int(tz_str[1:3])
        minutes = int(tz_str[3:5]) if len(tz_str) > 3 else 0

        offset = hours * 3600 + minutes * 60
        if sign == "-":
            offset = -offset

        tz = timezone(offset=timedelta(seconds=offset))
        return dt.replace(tzinfo=tz)

    @classmethod
    def _ensure_utc(cls, dt: datetime) -> datetime:
        """Ensure datetime is in UTC timezone."""
        if dt.tzinfo is None:
            # Assume local timezone if none specified
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            # Convert to UTC
            dt = dt.astimezone(timezone.utc)

        return dt

    @classmethod
    def format_date(cls, dt: datetime, format_type: str = "iso") -> str:
        """Format datetime to string using specified format.

        Args:
            dt: Datetime object to format
            format_type: Format type ('iso', 'rss', 'date_only')

        Returns:
            Formatted date string
        """
        if dt is None:
            return ""

        # Ensure UTC
        dt = cls._ensure_utc(dt)

        if format_type == "iso":
            return dt.isoformat()
        elif format_type == "rss":
            return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
        elif format_type == "date_only":
            return dt.strftime("%Y-%m-%d")
        else:
            return dt.isoformat()

    @classmethod
    def is_valid_date(cls, date_input: Union[str, datetime, None]) -> bool:
        """Check if date input can be parsed successfully.

        Args:
            date_input: Date string, datetime object, or None

        Returns:
            True if date can be parsed, False otherwise
        """
        return cls.parse_date(date_input) is not None


def format_datetime_for_report(dt: datetime) -> str:
    """Format a datetime object in a European readable format (DD/MM/YYYY HH:MM:SS).

    Args:
        dt: Datetime object to format
    Returns:
        Formatted string or '-' if dt is None
    """
    if dt is None:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M:%S")
