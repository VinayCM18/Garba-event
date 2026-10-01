import re
from typing import Optional

INDIAN_PHONE_REGEX = re.compile(r"^(?:\+91|91)?[6-9]\d{9}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

PLACEHOLDER_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.org",
    "invalid",
    "localhost",
    "none.com",
}

PLACEHOLDER_EMAILS = {
    "booker@example.com",
    "admin@example.com",
    "test@example.com",
    "user@example.com",
    "tester@example.com",
    "placeholder@example.com",
    "missing@example.com",
    "fail@example.com",
}

def validate_indian_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-]", "", phone)
    return bool(INDIAN_PHONE_REGEX.match(cleaned))

def normalize_indian_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-]", "", phone)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    return f"+91{cleaned}"

def validate_email_format(email: Optional[str]) -> bool:
    if not email:
        return False
    clean = email.strip()
    return bool(EMAIL_REGEX.match(clean)) and len(clean) <= 254

def is_placeholder_email(email: Optional[str]) -> bool:
    if not email:
        return True
    clean = email.strip().lower()
    if clean in PLACEHOLDER_EMAILS:
        return True
    if "@" in clean:
        domain = clean.split("@")[-1].strip()
        if domain in PLACEHOLDER_DOMAINS or domain.endswith(".example.com") or domain.endswith(".example.org"):
            return True
    return False
