import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Set
from app.models.document import DocumentCategory


REQUIRED_FIELDS_BY_CATEGORY: Dict[DocumentCategory, Set[str]] = {
    DocumentCategory.PASSPORT: {
        "passport_number",
        "surname",
        "date_of_birth",
        "date_of_expiry",
    },
    DocumentCategory.INVOICE: {
        "invoice_number",
        "invoice_date",
        "total_amount",
        "vendor_name",
    },
    DocumentCategory.CONTRACT: {
        "document_title",
        "effective_date",
    },
    DocumentCategory.GENERAL_DOCUMENT: {
        "document_title",
    },
    DocumentCategory.BUSINESS_DOCUMENT: {
        "document_title",
    },
    DocumentCategory.IDENTITY_DOCUMENT: {
        "passport_number",
        "surname",
    },
    DocumentCategory.UNKNOWN: set(),
}


def normalize_date(date_str: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Parse and normalize varied date representations into standard ISO 8601 (YYYY-MM-DD).
    Returns (is_valid, normalized_iso_date, error_message).
    """
    if not date_str or not date_str.strip():
        return False, None, "Empty date value."

    cleaned = date_str.strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %b %Y",     # 14 Apr 1988
        "%d %B %Y",     # 14 April 1988
        "%b %d, %Y",    # Apr 14, 1988
        "%B %d, %Y",    # April 14, 1988
        "%d/%m/%Y",     # 14/04/1988
        "%m/%d/%Y",     # 04/14/1988
        "%d-%m-%Y",
        "%m-%d-%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            # Plausibility sanity check: year between 1900 and 2100
            if 1900 <= dt.year <= 2100:
                return True, dt.strftime("%Y-%m-%d"), None
        except ValueError:
            continue

    return False, None, f"Date '{date_str}' does not match recognized formats."


def validate_numeric_amount(amount_str: Optional[str]) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate and parse monetary or numeric string into a float.
    Returns (is_valid, parsed_float, error_message).
    """
    if not amount_str or not amount_str.strip():
        return False, None, "Empty numeric amount."

    cleaned = re.sub(r"[^\d\.\-]", "", amount_str.strip())
    try:
        val = float(cleaned)
        if val < 0:
            return False, val, "Amount cannot be negative."
        return True, val, None
    except ValueError:
        return False, None, f"Cannot parse '{amount_str}' as a numeric amount."


def validate_email_format(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Verify standard email format RFC 5322 simplified."""
    if not email:
        return False, "Empty email."
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if re.match(pattern, email.strip()):
        return True, None
    return False, f"Invalid email format: '{email}'."


def check_invoice_math(
    subtotal: Optional[float], tax: Optional[float], total: Optional[float]
) -> Tuple[bool, Optional[str]]:
    """
    Assert that subtotal + tax equals total within a 0.05 currency tolerance.
    """
    if subtotal is None or total is None:
        return True, None  # Cannot perform full cross-check if components are absent

    calculated = subtotal + (tax or 0.0)
    difference = abs(calculated - total)

    if difference > 0.05:
        return (
            False,
            f"Invoice totals mismatch: Subtotal ({subtotal:.2f}) + Tax ({tax or 0.0:.2f}) = "
            f"{calculated:.2f}, but Total is {total:.2f} (diff: {difference:.2f}).",
        )
    return True, None


def check_passport_dates(
    birth_iso: Optional[str], expiry_iso: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """Assert that passport date of expiry is strictly after date of birth."""
    if not birth_iso or not expiry_iso:
        return True, None

    try:
        dt_birth = datetime.strptime(birth_iso, "%Y-%m-%d")
        dt_expiry = datetime.strptime(expiry_iso, "%Y-%m-%d")
        if dt_expiry <= dt_birth:
            return False, "Date of expiry must be after date of birth."
        return True, None
    except Exception as e:
        return False, f"Date comparison error: {e}"

