import re

INDIAN_PHONE_REGEX = re.compile(r"^(?:\+91|91)?[6-9]\d{9}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

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

def validate_email_format(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))
