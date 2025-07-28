"""Content validation utilities for detecting blocked or invalid content."""

import re
from typing import Dict, List, Tuple


class ContentValidator:
    """Validates HTML content for blocked pages, anti-bot detection, and invalid responses."""

    # Anti-bot detection patterns - More specific with word boundaries and limited distance
    ANTI_BOT_PATTERNS = [
        # CAPTCHA patterns - specific phrases and HTML attributes
        r"\bcaptcha\s+required\b",
        r"\brecaptcha\s+required\b",
        r'class\s*=\s*["\'][^"\']*captcha[^"\']*["\']',  # captcha in class attributes
        r'id\s*=\s*["\'][^"\']*captcha[^"\']*["\']',  # captcha in id attributes
        r'<[^>]*class\s*=\s*["\'][^"\']*captcha[^"\']*["\'][^>]*>',  # captcha in any HTML tag class
        r"\bprove\s+you\s+are\s+human\b",
        r"\bverify\s+you\s+are\s+human\b",
        r"\bhuman\s+verification\s+required\b",
        r"\brobot\s+check\s+required\b",
        r"\bbot\s+detection\s+page\b",
        # Block patterns - specific phrases
        r"\baccess\s+denied.*?\bbot\b",
        r"\bforbidden.*?\bbot\b",
        r"\bblocked.*?\bbot\b",
        r"\brestricted.*?\bbot\b",
        r"\bunauthorized.*?\bbot\b",
        r"\bnot\s+authorized.*?\bbot\b",
        # Rate limiting patterns - specific phrases
        r"\btoo\s+many\s+requests\b",
        r"\brate\s+limit\s+exceeded\b",
        r"\brequest\s+limit\s+exceeded\b",
        r"\bplease\s+wait\s+before\s+making\s+more\s+requests\b",
        r"\bplease\s+wait\s+\d+\s+seconds\b",
        r"\btry\s+again\s+later.*?\brate\s+limit\b",
        # Geographic blocks - specific phrases
        r"\bnot\s+available\s+in\s+your\s+region\b",
        r"\bgeographic\s+restriction\s+applies\b",
        r"\bcontent\s+blocked\s+in\s+your\s+country\b",
        # JavaScript requirements - specific phrases
        r"\bjavascript\s+required\s+to\s+access\s+this\s+page\b",
        r"\benable\s+javascript\s+to\s+continue\b",
        r"\bjavascript\s+must\s+be\s+enabled\b",
        # Security checks - specific phrases
        r"\bsecurity\s+check\s+required\s+for\s+your\s+browser\b",
        r"\bbrowser\s+security\s+check\s+failed\b",
        r"\bplease\s+complete\s+security\s+check\b",
        # Suspicious activity - specific phrases
        r"\bsuspicious\s+activity\s+detected\b",
        r"\bunusual\s+traffic\s+detected\b",
        r"\bautomated\s+access\s+detected\b",
        r"\bbot\s+activity\s+detected\b",
        # Error page patterns - specific phrases
        r"\bpage\s+not\s+found\b",
        r"\bthe\s+page\s+you\s+are\s+looking\s+for\s+does\s+not\s+exist\b",
    ]

    # Empty content patterns - more specific
    EMPTY_CONTENT_PATTERNS = [
        r"<html>\s*<body>\s*</body>\s*</html>",
        r"<html>\s*<head>\s*</head>\s*<body>\s*</body>\s*</html>",
        r"<html>\s*</html>",
    ]

    # Suspicious redirect patterns - more specific
    REDIRECT_PATTERNS = [
        r"window\.location",
        r"location\.href",
        r"meta.*?refresh",
        r"\bredirect\b",
    ]

    def __init__(self):
        """Initialize the content validator with compiled patterns."""
        self.anti_bot_regex = re.compile(
            "|".join(self.ANTI_BOT_PATTERNS), re.IGNORECASE
        )
        self.empty_content_regex = re.compile(
            "|".join(self.EMPTY_CONTENT_PATTERNS), re.IGNORECASE | re.DOTALL
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

        # Check for Cloudflare-style challenges - more specific
        if (
            "cloudflare" in html_content.lower()
            and "checking your browser" in html_content.lower()
        ):
            indicators.append("Cloudflare DDoS protection detected")

        # Check for JavaScript challenges - more specific
        if (
            "javascript" in html_content.lower()
            and "enable" in html_content.lower()
            and any(
                phrase in html_content.lower()
                for phrase in [
                    "enable javascript",
                    "javascript required",
                    "javascript must be enabled",
                ]
            )
        ):
            indicators.append("JavaScript challenge detected")

        # Check for suspicious title patterns - more specific
        title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).lower()
            # Only flag if the entire title is suspicious, not just contains words
            suspicious_titles = [
                "access denied",
                "forbidden",
                "blocked",
                "captcha required",
                "bot detected",
                "unauthorized",
                "not found",
            ]
            if any(suspicious in title for suspicious in suspicious_titles):
                # Add "error" to the message if it's an error-related title
                if any(
                    error_word in title
                    for error_word in ["error", "not found", "404", "500", "403", "401"]
                ):
                    indicators.append(f"Error page detected: {title_match.group(1)}")
                else:
                    indicators.append(f"Suspicious page title: {title_match.group(1)}")

        # Check for suspicious meta descriptions - more specific
        meta_match = re.search(
            r'<meta.*?name="description".*?content="(.*?)"', html_content, re.IGNORECASE
        )
        if meta_match:
            description = meta_match.group(1).lower()
            # Only flag if the description is clearly about blocking
            blocking_phrases = [
                "access denied",
                "forbidden",
                "blocked",
                "captcha required",
                "bot detected",
                "unauthorized",
            ]
            if any(phrase in description for phrase in blocking_phrases):
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
