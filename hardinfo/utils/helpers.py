"""Helper functions for string cleaning and system formatting.
"""

import re


def clean_system_string(text: str) -> str:
    """Removes mojibake, invalid control characters, and normalizes whitespaces."""
    if not text:
        return ""
    cleaned = re.sub(r'[^\w\s\-\(\)\.,:/\*™®+\x00-\x7F\u0400-\u04FF]', '', str(text))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned
