from __future__ import annotations

import re

CUSTOMER_KEYWORDS = {
    "estimate", "quote", "invoice", "payment", "pay", "paid", "deposit", "balance",
    "job", "repair", "install", "installation", "fix", "come by", "appointment",
    "schedule", "look at", "how much", "available", "permit", "inspection", "charger",
    "panel", "wire", "roof", "leak", "broken", "maintenance", "service", "cash", "zelle", "venmo",
}

SPAM_KEYWORDS = {
    "verification code", "your code is", "2fa", "unsubscribe", "stop to opt out",
    "otp", "one-time code", "security code", "do not share this code", "promo",
}

JOB_KEYWORDS = {
    "installation": ["install", "installation", "charger", "panel", "wire", "mount"],
    "repair": ["repair", "fix", "broken", "leak", "not working"],
    "estimate": ["estimate", "quote", "how much", "bid"],
    "permit": ["permit", "inspection", "city", "county"],
    "follow_up": ["follow up", "checking in", "still need", "available"],
}

PAYMENT_METHODS = ["zelle", "venmo", "cash app", "cashapp", "cash", "check", "credit card", "card", "square", "stripe", "paypal", "invoice"]
MONEY_RE = re.compile(r"(?<!\w)(?:\$\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d{2,6})(?:\s*dollars)?(?!\w)", re.I)
ADDRESS_RE = re.compile(r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+\s+(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|blvd|way|pl|place|terrace|ter|circle|cir)\b(?:[, ]+[A-Za-z .'-]+)?(?:[, ]+[A-Z]{2})?(?:\s+\d{5})?", re.I)


def text_contains_any(text: str, words: set[str] | list[str]) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def detect_addresses(text: str) -> list[str]:
    return [m.group(0).strip(" .,;:") for m in ADDRESS_RE.finditer(text or "")]


def detect_amount(text: str) -> str:
    text_l = (text or "").lower()
    candidates = []
    for m in MONEY_RE.finditer(text or ""):
        token = m.group(0).strip()
        n = re.sub(r"[^0-9.]", "", token)
        if not n:
            continue
        try:
            value = float(n.replace(",", ""))
        except ValueError:
            continue
        if "$" in token or "dollar" in text_l or value >= 50:
            candidates.append(token if "$" in token else f"${n}")
    return candidates[0] if candidates else ""


def detect_payment_method(text: str) -> str:
    t = (text or "").lower()
    for method in PAYMENT_METHODS:
        if method in t:
            return "cash app" if method == "cashapp" else method
    return ""


def payment_status(text: str, direction: str = "") -> tuple[str, float]:
    t = (text or "").lower()
    if any(p in t for p in ["got it", "received", "paid in full", "payment received", "thanks, got", "got the check"]):
        return "paid_likely", 0.9
    if any(p in t for p in ["just sent", "sent the zelle", "sent payment", "paid you", "i paid", "venmoed", "zelle"]):
        return "paid_likely", 0.8
    if any(p in t for p in ["deposit", "down payment"]):
        return "partial_payment_possible", 0.72
    if any(p in t for p in ["invoice", "sent invoice"]):
        return "invoice_sent", 0.72
    if any(p in t for p in ["balance", "remaining", "past due", "overdue"]):
        return "overdue_possible", 0.68
    if any(p in t for p in ["how much", "estimate", "quote", "total is"]):
        return "quoted", 0.64
    if any(p in t for p in ["pay", "payment", "cash", "check", "venmo", "cash app", "square", "stripe"]):
        return "mentioned", 0.55
    return "", 0.0


def classify_job(text: str) -> tuple[str, float]:
    t = (text or "").lower()
    best = ("unknown", 0.0)
    for job_type, words in JOB_KEYWORDS.items():
        hits = sum(1 for w in words if w in t)
        if hits:
            conf = min(0.55 + hits * 0.12, 0.9)
            if conf > best[1]:
                best = (job_type, conf)
    return best
