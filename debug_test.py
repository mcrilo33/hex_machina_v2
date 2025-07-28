import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hex_machina.ingestion.content_validator import create_content_validator

# Create validator
validator = create_content_validator()

# Test the captcha HTML from the test
captcha_html = "<html><body><div class='captcha'>Verify</div></body></html>"

print("Testing captcha detection...")
print(f"HTML: {captcha_html}")

is_valid, validation_result = validator.validate_content(
    html_content=captcha_html,
    url="http://example.com/captcha.html",
    status_code=200,
)

print(f"Is valid: {is_valid}")
print(f"Validation result: {validation_result}")

summary = validator.extract_validation_summary(validation_result)
print(f"Summary: {summary}")

# Check if the regex is working
import re

pattern = r'class\s*=\s*["\'][^"\']*captcha[^"\']*["\']'
regex = re.compile(pattern, re.IGNORECASE)
matches = regex.findall(captcha_html)
print(f"Regex matches: {matches}")
print(f"Regex working: {bool(matches)}")
