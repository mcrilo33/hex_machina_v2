"""Content validation utilities for detecting blocked or invalid content."""

import re
from typing import Dict, List, Tuple


class ContentValidator:
    """Validates HTML content for blocked pages, anti-bot detection, and invalid responses."""

    # Anti-bot detection patterns
    ANTI_BOT_PATTERNS = [
        # CAPTCHA patterns
        r"captcha",
        r"recaptcha",
        r"prove.*human",
        r"verify.*human",
        r"human.*verification",
        r"robot.*check",
        r"bot.*detection",
        # Block patterns
        r"access.*denied",
        r"forbidden",
        r"blocked",
        r"restricted",
        r"unauthorized",
        r"not.*authorized",
        # Rate limiting patterns
        r"too.*many.*requests",
        r"rate.*limit",
        r"request.*limit",
        r"please.*wait",
        r"try.*again.*later",
        # Geographic blocks
        r"not.*available.*region",
        r"geographic.*restriction",
        r"content.*unavailable",
        r"region.*blocked",
        # Maintenance patterns
        r"under.*maintenance",
        r"temporarily.*unavailable",
        r"service.*unavailable",
        r"down.*for.*maintenance",
        # Cloudflare and CDN blocks
        r"cloudflare",
        r"checking.*browser",
        r"ddos.*protection",
        r"security.*check",
        # JavaScript challenges
        r"javascript.*required",
        r"enable.*javascript",
        r"browser.*check",
        r"security.*verification",
    ]

    # Empty content patterns
    EMPTY_CONTENT_PATTERNS = [
        r"<html>\s*<body>\s*</body>\s*</html>",
        r"<html>\s*<head>\s*</head>\s*<body>\s*</body>\s*</html>",
        r"<html>\s*</html>",
    ]

    # Error page patterns
    ERROR_PAGE_PATTERNS = [
        r"page.*not.*found",
        r"404.*error",
        r"error.*404",
        r"page.*does.*not.*exist",
        r"content.*not.*found",
        r"article.*not.*found",
        r"post.*not.*found",
    ]

    # Suspicious redirect patterns
    REDIRECT_PATTERNS = [
        r"window\.location",
        r"location\.href",
        r"meta.*refresh",
        r"redirect",
    ]

    def __init__(self):
        """Initialize the content validator with compiled patterns."""
        self.anti_bot_regex = re.compile(
            "|".join(self.ANTI_BOT_PATTERNS), re.IGNORECASE
        )
        self.empty_content_regex = re.compile(
            "|".join(self.EMPTY_CONTENT_PATTERNS), re.IGNORECASE | re.DOTALL
        )
        self.error_page_regex = re.compile(
            "|".join(self.ERROR_PAGE_PATTERNS), re.IGNORECASE
        )
        self.redirect_regex = re.compile(
            "|".join(self.REDIRECT_PATTERNS), re.IGNORECASE
        )

    def validate_content(
        self, html_content: str, url: str, status_code: int = 200
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Validate HTML content for various issues.

        Args:
            html_content: The HTML content to validate
            url: The URL that was requested
            status_code: HTTP status code

        Returns:
            Tuple of (is_valid, validation_details)
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "content_length": len(html_content) if html_content else 0,
            "status_code": status_code,
        }

        if not html_content or html_content.strip() == "":
            validation_result["is_valid"] = False
            validation_result["issues"].append("Empty content")
            return False, validation_result

        # Check for anti-bot patterns
        anti_bot_matches = self.anti_bot_regex.findall(html_content)
        if anti_bot_matches:
            validation_result["is_valid"] = False
            validation_result["issues"].append(
                f"Anti-bot detection: {', '.join(set(anti_bot_matches))}"
            )

        # Check for empty content patterns
        if self.empty_content_regex.search(html_content):
            validation_result["is_valid"] = False
            validation_result["issues"].append("Empty or minimal HTML content")

        # Check for error pages
        error_matches = self.error_page_regex.findall(html_content)
        if error_matches:
            validation_result["is_valid"] = False
            validation_result["issues"].append(
                f"Error page detected: {', '.join(set(error_matches))}"
            )

        # Check for suspicious redirects
        redirect_matches = self.redirect_regex.findall(html_content)
        if redirect_matches:
            validation_result["warnings"].append(
                f"Suspicious redirect patterns: {', '.join(set(redirect_matches))}"
            )

        # Check content length (too short might indicate blocking)
        if len(html_content) < 100:
            validation_result["warnings"].append(
                "Very short content (potential blocking)"
            )

        # Check for common blocking indicators
        blocking_indicators = self._check_blocking_indicators(html_content, url)
        if blocking_indicators:
            validation_result["issues"].extend(blocking_indicators)
            validation_result["is_valid"] = False

        return validation_result["is_valid"], validation_result

    def _check_blocking_indicators(self, html_content: str, url: str) -> List[str]:
        """Check for specific blocking indicators."""
        indicators = []

        # Check for Cloudflare-style challenges
        if (
            "cloudflare" in html_content.lower()
            and "checking your browser" in html_content.lower()
        ):
            indicators.append("Cloudflare DDoS protection detected")

        # Check for JavaScript challenges
        if "javascript" in html_content.lower() and "enable" in html_content.lower():
            indicators.append("JavaScript challenge detected")

        # Check for suspicious title patterns
        title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).lower()
            if any(
                pattern in title
                for pattern in ["blocked", "forbidden", "denied", "captcha"]
            ):
                indicators.append(f"Suspicious page title: {title_match.group(1)}")

        # Check for suspicious meta descriptions
        meta_match = re.search(
            r'<meta.*?name="description".*?content="(.*?)"', html_content, re.IGNORECASE
        )
        if meta_match:
            description = meta_match.group(1).lower()
            if any(
                pattern in description
                for pattern in ["blocked", "forbidden", "denied", "captcha"]
            ):
                indicators.append(f"Suspicious meta description: {meta_match.group(1)}")

        return indicators

    def extract_validation_summary(self, validation_result: Dict[str, any]) -> str:
        """Extract a human-readable summary of validation results."""
        if validation_result["is_valid"]:
            summary = "Content validation: PASSED"
            if validation_result["warnings"]:
                summary += f" (Warnings: {', '.join(validation_result['warnings'])})"
        else:
            summary = (
                f"Content validation: FAILED - {', '.join(validation_result['issues'])}"
            )

        summary += f" (Length: {validation_result['content_length']} chars)"
        return summary


def create_content_validator() -> ContentValidator:
    """Factory function to create a content validator instance."""
    return ContentValidator()
