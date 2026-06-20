from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib

from .models import ContactSeed, CrmContact, CrmResult, JobSignal, Message, PaymentSignal, ReviewItem
from .phone import display_phone, stable_id
from .rules import CUSTOMER_KEYWORDS, SPAM_KEYWORDS, classify_job, detect_addresses, detect_amount, detect_payment_method, payment_status, text_contains_any


def file_sha256(path: str | Path | None) -> str:
    if not path:
        return ""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _snippet(text: str, limit: int = 160) -> str:
    one = " ".join((text or "").split())
    return one[:limit] + ("…" if len(one) > limit else "")


def _contact_maps(seeds: list[ContactSeed]):
    by_phone = {}
    for c in seeds:
        for p in c.phones:
            if p.normalized and p.normalized not in by_phone:
                by_phone[p.normalized] = c
    return by_phone


def _score_customer(seed: ContactSeed | None, messages: list[Message], saved_addresses: list[str]) -> tuple[str, float, list[str]]:
    text = "\n".join(m.body for m in messages).lower()
    tags: set[str] = set()
    score = 0.0
    if seed:
        score += 0.15
        tags.add("in_contacts")
    if saved_addresses:
        score += 0.2
        tags.add("saved_address")
    if text_contains_any(text, CUSTOMER_KEYWORDS):
        score += 0.3
        tags.add("business_keywords")
    if any(detect_addresses(m.body) for m in messages):
        score += 0.2
        tags.add("address_in_messages")
    if any(payment_status(m.body, m.direction)[0] for m in messages):
        score += 0.15
        tags.add("payment_signal")
    if len(messages) >= 4 and any(m.direction == "incoming" for m in messages) and any(m.direction == "outgoing" for m in messages):
        score += 0.1
        tags.add("two_way_thread")
    if text_contains_any(text, SPAM_KEYWORDS):
        score -= 0.45
        tags.add("possible_automation_or_spam")
    score = max(0.0, min(1.0, score))
    label = "likely_customer" if score >= 0.75 else "possible_customer" if score >= 0.45 else "not_enough_evidence"
    return label, score, sorted(tags)


def _phone_label(phone: str, raw: str = "") -> str:
    return display_phone(phone, raw)


def _build_entities(seeds: list[ContactSeed], grouped: dict[str, list[Message]]):
    by_phone = _contact_maps(seeds)
    entities = []
    used_phones: set[str] = set()
    for seed in seeds:
        phones = [p.normalized for p in seed.phones if p.normalized]
        used_phones.update(phones)
        messages = []
        for phone in phones:
            messages.extend(grouped.get(phone, []))
        messages.sort(key=lambda m: m.date_ms)
        entities.append((seed.contact_id, seed, phones, messages))
    for phone, msgs in grouped.items():
        if phone not in used_phones:
            # If two VCF contacts accidentally shared the phone, the first seed owns it; otherwise sms-only.
            seed = by_phone.get(phone)
            if not seed:
                entities.append((stable_id("contact", phone), None, [phone], msgs))
    return entities


def build_crm(seeds: list[ContactSeed], messages: list[Message], sms_path: str | Path | None = None, contacts_path: str | Path | None = None) -> CrmResult:
    grouped: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        if m.phone_normalized:
            grouped[m.phone_normalized].append(m)
    for phone in list(grouped):
        grouped[phone].sort(key=lambda m: m.date_ms)

    contacts_out: list[CrmContact] = []
    jobs: list[JobSignal] = []
    payments: list[PaymentSignal] = []
    review: list[ReviewItem] = []

    for contact_id, seed, phones, thread in _build_entities(seeds, grouped):
        primary_norm = phones[0] if phones else ""
        primary_raw = thread[-1].phone_raw if thread else ""
        name = seed.name if seed else (thread[-1].contact_name if thread else "Unknown")
        saved_addresses = [a.formatted for a in seed.addresses] if seed else []
        label, conf, tags = _score_customer(seed, thread, saved_addresses)
        first_seen = thread[0].timestamp if thread else ""
        last_seen = thread[-1].timestamp if thread else ""
        incoming = sum(1 for m in thread if m.direction == "incoming")
        outgoing = sum(1 for m in thread if m.direction == "outgoing")
        phone_values = [_phone_label(p, primary_raw if p == primary_norm else "") for p in phones]
        primary_phone = " | ".join(phone_values) if phone_values else ""
        last_preview = _snippet(thread[-1].body) if thread else ""
        needs_review = conf < 0.8 or "payment_signal" in tags or "possible_automation_or_spam" in tags
        contacts_out.append(CrmContact(
            contact_id=contact_id,
            name=name,
            primary_phone=primary_phone,
            normalized_phone=" | ".join(phones),
            saved_addresses=" | ".join(saved_addresses),
            source="contacts+sms" if seed and thread else "contacts" if seed else "sms_only",
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            message_count=len(thread),
            incoming_count=incoming,
            outgoing_count=outgoing,
            likely_customer=label,
            customer_confidence=round(conf, 3),
            tags=", ".join(tags),
            last_message_preview=last_preview,
            needs_review=needs_review,
        ))

        job_msgs = []
        msg_addresses = []
        best_job = ("unknown", 0.0)
        for m in thread:
            jt, jc = classify_job(m.body)
            addrs = detect_addresses(m.body)
            if jt != "unknown" or addrs:
                job_msgs.append(m)
                msg_addresses.extend(addrs)
                if jc > best_job[1]:
                    best_job = (jt, jc)
            status, pc = payment_status(m.body, m.direction)
            if status:
                amount = detect_amount(m.body)
                method = detect_payment_method(m.body)
                payments.append(PaymentSignal(
                    payment_id=stable_id("pay", contact_id, m.message_id, status),
                    contact_id=contact_id,
                    primary_phone=primary_phone,
                    contact_name=name,
                    status_guess=status,
                    confidence=round(pc, 3),
                    amount=amount,
                    payment_method=method,
                    timestamp=m.timestamp,
                    evidence=_snippet(m.body),
                    evidence_message_id=m.message_id,
                    needs_review=pc < 0.9,
                ))
        if job_msgs:
            address = (msg_addresses or saved_addresses or [""])[0]
            evidence = _snippet(" | ".join(m.body for m in job_msgs[:3]), 240)
            jobs.append(JobSignal(
                job_id=stable_id("job", contact_id, address, evidence[:80]),
                contact_id=contact_id,
                primary_phone=primary_phone,
                contact_name=name,
                job_type=best_job[0],
                address=address,
                first_mentioned_at=job_msgs[0].timestamp,
                last_mentioned_at=job_msgs[-1].timestamp,
                confidence=round(max(best_job[1], 0.55 if address else 0.4), 3),
                evidence=evidence,
                evidence_message_ids=", ".join(m.message_id for m in job_msgs[:10]),
                needs_review=True,
            ))
        elif seed and saved_addresses and thread and label in {"likely_customer", "possible_customer"}:
            jobs.append(JobSignal(
                job_id=stable_id("job", contact_id, saved_addresses[0]),
                contact_id=contact_id,
                primary_phone=primary_phone,
                contact_name=name,
                job_type="unknown",
                address=saved_addresses[0],
                first_mentioned_at=first_seen,
                last_mentioned_at=last_seen,
                confidence=0.5,
                evidence="Saved contact address; no explicit job phrase detected in SMS.",
                evidence_message_ids="",
                needs_review=True,
            ))
        if seed and not thread:
            review.append(ReviewItem(stable_id("review", contact_id, "no_sms"), contact_id, primary_phone, name, "contact_has_no_sms_thread", "Keep as seeded contact or archive if not a customer.", 0.4, ""))
        if not seed and label != "not_enough_evidence":
            review.append(ReviewItem(stable_id("review", contact_id, "unknown_contact"), contact_id, primary_phone, name, "possible_customer_not_in_contacts", "Review and add to contacts/CRM if real customer.", conf, last_preview, thread[-1].message_id if thread else ""))
        if any(p.contact_id == contact_id for p in payments):
            review.append(ReviewItem(stable_id("review", contact_id, "payment"), contact_id, primary_phone, name, "payment_signal_needs_human_review", "Confirm against real payment records before marking paid/unpaid.", conf, last_preview, thread[-1].message_id if thread else ""))

    summary = {
        "messages_processed": len(messages),
        "contacts_seeded_from_vcf": len(seeds),
        "unique_sms_threads": len(grouped),
        "crm_contacts": len(contacts_out),
        "jobs_detected": len(jobs),
        "payment_signals_detected": len(payments),
        "review_items": len(review),
        "sms_xml_sha256": file_sha256(sms_path) if sms_path else "",
        "contacts_vcf_sha256": file_sha256(contacts_path) if contacts_path else "",
        "network_used": False,
        "llm_used": False,
        "privacy_note": "Local rule-based extraction only. Contacts with multiple phone numbers are one CRM contact. Payment status is inferred and requires human review.",
    }
    return CrmResult(sorted(contacts_out, key=lambda c: (c.customer_confidence, c.message_count), reverse=True), messages, jobs, payments, review, summary)
