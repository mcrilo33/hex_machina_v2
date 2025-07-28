import re

# Test the current regex pattern
test_html = "<html><body><div class='captcha'>Verify</div></body></html>"

# Current pattern from the validator
pattern = r'class\s*=\s*["\'][^"\']*captcha[^"\']*["\']'
regex = re.compile(pattern, re.IGNORECASE)

print(f"Testing HTML: {test_html}")
print(f"Pattern: {pattern}")
print(f"Match found: {bool(regex.search(test_html))}")
print(f"All matches: {regex.findall(test_html)}")

# Test with a simpler pattern
simple_pattern = r'class\s*=\s*["\'][^"\']*captcha[^"\']*["\']'
simple_regex = re.compile(simple_pattern, re.IGNORECASE)
print(f"\nSimple pattern: {simple_pattern}")
print(f"Match found: {bool(simple_regex.search(test_html))}")
print(f"All matches: {simple_regex.findall(test_html)}")

# Test with the new pattern I added
new_pattern = r'<[^>]*class\s*=\s*["\'][^"\']*captcha[^"\']*["\'][^>]*>'
new_regex = re.compile(new_pattern, re.IGNORECASE)
print(f"\nNew pattern: {new_pattern}")
print(f"Match found: {bool(new_regex.search(test_html))}")
print(f"All matches: {new_regex.findall(test_html)}")

# Test with a very simple pattern
very_simple = r"captcha"
very_simple_regex = re.compile(very_simple, re.IGNORECASE)
print(f"\nVery simple pattern: {very_simple}")
print(f"Match found: {bool(very_simple_regex.search(test_html))}")
print(f"All matches: {very_simple_regex.findall(test_html)}")
