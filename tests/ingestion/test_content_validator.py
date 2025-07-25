"""Unit tests for content validation functionality."""

from pathlib import Path

import pytest

from src.hex_machina.ingestion.content_validator import create_content_validator


class TestContentValidator:
    """Test cases for ContentValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = create_content_validator()

    def test_captcha_detection(self):
        """Test that CAPTCHA content is properly detected."""
        # Load the test CAPTCHA HTML file
        captcha_file = (
            Path(__file__).parent.parent
            / "integration"
            / "data"
            / "article_captcha.html"
        )

        if not captcha_file.exists():
            pytest.skip(f"CAPTCHA test file not found: {captcha_file}")

        with open(captcha_file, "r", encoding="utf-8") as f:
            captcha_html = f.read()

        # Test CAPTCHA detection
        is_valid, validation_result = self.validator.validate_content(
            html_content=captcha_html,
            url="http://localhost:8000/article_captcha.html",
            status_code=200,
        )

        # Should detect CAPTCHA and mark as invalid
        assert not is_valid, "CAPTCHA content should be marked as invalid"
        assert "issues" in validation_result, "Validation result should contain issues"
        assert len(validation_result["issues"]) > 0, "Should have at least one issue"

        # Check for CAPTCHA-related issues
        issues_text = " ".join(validation_result["issues"]).lower()
        assert (
            "captcha" in issues_text or "anti-bot" in issues_text
        ), f"Expected CAPTCHA detection, got: {validation_result['issues']}"

        print(f"CAPTCHA detection result: {validation_result}")

    def test_normal_content(self):
        """Test that normal content passes validation."""
        normal_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Normal Article</title></head>
        <body>
            <h1>Article Title</h1>
            <p>This is normal article content.</p>
        </body>
        </html>
        """

        is_valid, validation_result = self.validator.validate_content(
            html_content=normal_html,
            url="http://example.com/article.html",
            status_code=200,
        )

        assert is_valid, "Normal content should be marked as valid"
        assert validation_result["is_valid"], "Validation result should be valid"
        assert len(validation_result["issues"]) == 0, "Should have no issues"

    def test_empty_content(self):
        """Test that empty content is detected."""
        empty_html = ""

        is_valid, validation_result = self.validator.validate_content(
            html_content=empty_html,
            url="http://example.com/empty.html",
            status_code=200,
        )

        assert not is_valid, "Empty content should be marked as invalid"
        assert (
            "Empty content" in validation_result["issues"][0]
        ), "Should detect empty content"

    def test_minimal_html(self):
        """Test that minimal HTML is detected."""
        minimal_html = "<html><body></body></html>"

        is_valid, validation_result = self.validator.validate_content(
            html_content=minimal_html,
            url="http://example.com/minimal.html",
            status_code=200,
        )

        assert not is_valid, "Minimal HTML should be marked as invalid"
        assert (
            "Empty or minimal HTML content" in validation_result["issues"][0]
        ), "Should detect minimal HTML"

    def test_error_page_detection(self):
        """Test that error pages are detected."""
        error_html = """
        <!DOCTYPE html>
        <html>
        <head><title>404 Page Not Found</title></head>
        <body>
            <h1>404 Error</h1>
            <p>The page you are looking for does not exist.</p>
        </body>
        </html>
        """

        is_valid, validation_result = self.validator.validate_content(
            html_content=error_html,
            url="http://example.com/notfound.html",
            status_code=200,
        )

        assert not is_valid, "Error page should be marked as invalid"
        issues_text = " ".join(validation_result["issues"]).lower()
        assert (
            "error" in issues_text
        ), f"Should detect error page, got: {validation_result['issues']}"

    def test_rate_limit_detection(self):
        """Test that rate limit pages are detected."""
        rate_limit_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Too Many Requests</title></head>
        <body>
            <h1>Rate Limit Exceeded</h1>
            <p>Please wait 60 seconds before trying again.</p>
        </body>
        </html>
        """

        is_valid, validation_result = self.validator.validate_content(
            html_content=rate_limit_html,
            url="http://example.com/ratelimit.html",
            status_code=200,
        )

        assert not is_valid, "Rate limit page should be marked as invalid"
        issues_text = " ".join(validation_result["issues"]).lower()
        assert (
            "too many requests" in issues_text
        ), f"Should detect rate limit, got: {validation_result['issues']}"

    def test_cloudflare_detection(self):
        """Test that Cloudflare protection is detected."""
        cloudflare_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Checking your browser</title></head>
        <body>
            <h1>Checking your browser</h1>
            <p>Cloudflare is checking your browser before proceeding.</p>
        </body>
        </html>
        """

        is_valid, validation_result = self.validator.validate_content(
            html_content=cloudflare_html,
            url="http://example.com/cloudflare.html",
            status_code=200,
        )

        assert not is_valid, "Cloudflare page should be marked as invalid"
        issues_text = " ".join(validation_result["issues"]).lower()
        assert (
            "cloudflare" in issues_text
        ), f"Should detect Cloudflare protection, got: {validation_result['issues']}"

    def test_validation_summary(self):
        """Test that validation summary is properly formatted."""
        # Test valid content
        normal_html = "<html><body><h1>Test</h1></body></html>"
        is_valid, validation_result = self.validator.validate_content(
            html_content=normal_html,
            url="http://example.com/test.html",
            status_code=200,
        )

        summary = self.validator.extract_validation_summary(validation_result)
        assert "PASSED" in summary, "Valid content should show PASSED"
        # Use the actual content length from the validation result
        expected_length = validation_result.get("content_length", 0)
        assert (
            f"Length: {expected_length} chars" in summary
        ), f"Should show content length {expected_length}"

        # Test invalid content
        captcha_html = "<html><body><div class='captcha'>Verify</div></body></html>"
        is_valid, validation_result = self.validator.validate_content(
            html_content=captcha_html,
            url="http://example.com/captcha.html",
            status_code=200,
        )

        summary = self.validator.extract_validation_summary(validation_result)
        assert "FAILED" in summary, "Invalid content should show FAILED"
        assert "captcha" in summary.lower(), "Should mention CAPTCHA in summary"
