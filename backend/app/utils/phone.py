"""Phone normalization utilities."""

import re

def normalize_phone(phone: str) -> str:
    """Normalize phone numbers to canonical E.164-like format.

    For Indian phone numbers:
    - 10 digits -> +91XXXXXXXXXX
    - 91XXXXXXXXXX -> +91XXXXXXXXXX
    - +91XXXXXXXXXX -> +91XXXXXXXXXX
    - Strips spaces, hyphens, parentheses, etc.
    """
    if not phone:
        return ""

    # Remove all non-digits except leading '+'
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # If starts with +, strip and process digits
    has_plus = cleaned.startswith("+")
    digits_only = cleaned.lstrip("+")

    # Handle Indian numbers
    if len(digits_only) == 10:
        return f"+91{digits_only}"
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        return f"+{digits_only}"
    elif has_plus and len(digits_only) >= 10:
        return f"+{digits_only}"

    # Return as standard string if it doesn't match above patterns but is digit-based
    return f"+{digits_only}" if has_plus else digits_only