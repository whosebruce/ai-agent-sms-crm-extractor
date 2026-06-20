from __future__ import annotations

import hashlib
import re


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.lower() in {"null", "unknown", "(unknown)"}:
        return ""
    if "~" in value:
        value = value.split("~", 1)[0]
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def display_phone(normalized: str, raw: str = "") -> str:
    if len(normalized) == 10:
        return f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"
    return raw or normalized


def stable_id(prefix: str, *parts: str) -> str:
    data = "|".join(parts).encode("utf-8", errors="ignore")
    return f"{prefix}_{hashlib.sha1(data).hexdigest()[:12]}"


def clean_null(value: str | None) -> str:
    if value is None:
        return ""
    value = value.strip()
    if value.lower() in {"null", "(unknown)", "unknown", "none"}:
        return ""
    return value
