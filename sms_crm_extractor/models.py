from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Phone:
    raw: str
    normalized: str


@dataclass
class Address:
    formatted: str
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class ContactSeed:
    contact_id: str
    name: str
    phones: list[Phone] = field(default_factory=list)
    addresses: list[Address] = field(default_factory=list)
    notes: str = ""


@dataclass
class Message:
    message_id: str
    kind: str
    date_ms: int
    timestamp: str
    phone_raw: str
    phone_normalized: str
    direction: str
    body: str
    contact_name: str = ""


@dataclass
class CrmContact:
    contact_id: str
    name: str
    primary_phone: str
    normalized_phone: str
    saved_addresses: str
    source: str
    first_seen_at: str = ""
    last_seen_at: str = ""
    message_count: int = 0
    incoming_count: int = 0
    outgoing_count: int = 0
    likely_customer: str = "not_enough_evidence"
    customer_confidence: float = 0.0
    tags: str = ""
    last_message_preview: str = ""
    needs_review: bool = True


@dataclass
class JobSignal:
    job_id: str
    contact_id: str
    primary_phone: str
    contact_name: str
    job_type: str
    address: str
    first_mentioned_at: str
    last_mentioned_at: str
    confidence: float
    evidence: str
    evidence_message_ids: str
    needs_review: bool


@dataclass
class PaymentSignal:
    payment_id: str
    contact_id: str
    primary_phone: str
    contact_name: str
    status_guess: str
    confidence: float
    amount: str
    payment_method: str
    timestamp: str
    evidence: str
    evidence_message_id: str
    needs_review: bool


@dataclass
class ReviewItem:
    review_id: str
    contact_id: str
    primary_phone: str
    contact_name: str
    reason: str
    suggested_action: str
    confidence: float
    evidence: str
    evidence_message_id: str = ""


@dataclass
class CrmResult:
    contacts: list[CrmContact]
    messages: list[Message]
    jobs: list[JobSignal]
    payments: list[PaymentSignal]
    review: list[ReviewItem]
    summary: dict[str, Any]
