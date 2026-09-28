"""Hand-off to Client Intel Dashboard (https://github.com/whosebruce/client-intel-dashboard).

Turns the CRM result into rows in the dashboard's import schema, so likely and
possible customers can go onto its map, status tiles and follow-up queue.
Rows carry derived labels only (status, amount, job type, score), never
message text.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .models import ContactSeed, CrmContact, JobSignal, PaymentSignal

REPO_URL = "https://github.com/whosebruce/client-intel-dashboard"
FIELDS = ["id", "name", "address", "city", "lat", "lng", "status", "phone", "last_contact", "value", "follow_up", "notes", "confidence"]
INCLUDED = {"likely_customer", "possible_customer"}
DROP_NAME = "sms-crm-extractor.csv"

# Latest payment clue -> dashboard status. "mentioned" is too weak to count.
STATUS_MAP = {
    "paid_likely": "paid",
    "partial_payment_possible": "unpaid",
    "invoice_sent": "unpaid",
    "overdue_possible": "unpaid",
    "quoted": "lead",
}


def client_intel_rows(
    contacts: list[CrmContact],
    jobs: list[JobSignal],
    payments: list[PaymentSignal],
    seeds: list[ContactSeed],
) -> tuple[list[dict[str, str]], int]:
    """Return (rows, skipped) where skipped counts contacts without enough customer evidence."""
    seed_by_id = {s.contact_id: s for s in seeds}
    job_by_contact = {j.contact_id: j for j in jobs}
    pays_by_contact: dict[str, list[PaymentSignal]] = {}
    for p in payments:
        pays_by_contact.setdefault(p.contact_id, []).append(p)

    rows: list[dict[str, str]] = []
    skipped = 0
    for c in contacts:
        if c.likely_customer not in INCLUDED:
            skipped += 1
            continue
        seed = seed_by_id.get(c.contact_id)
        job = job_by_contact.get(c.contact_id)
        signals = sorted(pays_by_contact.get(c.contact_id, []), key=lambda p: p.timestamp)
        status_signal = next((p for p in reversed(signals) if p.status_guess in STATUS_MAP), None)
        amount = next((p.amount for p in reversed(signals) if p.amount), "")

        # A saved contact address is structured (street, city, state, zip) and
        # geocodes better than an address spotted inside a text.
        saved = seed.addresses[0] if seed and seed.addresses else None
        address = saved.formatted if saved else (job.address if job else "")
        city = saved.city if saved else ""

        notes = [f"From SMS CRM extractor: {c.likely_customer.replace('_', ' ')} ({c.customer_confidence:.2f})."]
        if job and job.job_type != "unknown":
            notes.append(f"Job: {job.job_type}.")
        if status_signal:
            method = f" via {status_signal.payment_method}" if status_signal.payment_method else ""
            notes.append(f"Payment clue: {status_signal.status_guess.replace('_', ' ')}{method}.")
        notes.append(f"{c.message_count} texts. Check against real records before acting.")

        rows.append({
            "id": c.contact_id,
            "name": c.name,
            "address": address,
            "city": city,
            "lat": "",
            "lng": "",
            "status": STATUS_MAP[status_signal.status_guess] if status_signal else "lead",
            "phone": c.primary_phone.split(" | ")[0],
            "last_contact": c.last_seen_at[:10],
            "value": amount,
            "follow_up": "",
            "notes": " ".join(notes),
            "confidence": "sms " + ("likely" if c.likely_customer == "likely_customer" else "possible"),
        })
    return rows, skipped


def write_client_intel_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def resolve_checkout(checkout: str | Path) -> Path:
    """Return the checkout root, or raise if it isn't a client-intel-dashboard clone."""
    root = Path(checkout).expanduser().resolve()
    if not (root / "scripts" / "ingest.py").is_file():
        raise FileNotFoundError(f"{root} doesn't look like a client-intel-dashboard checkout (no scripts/ingest.py). Clone {REPO_URL} first.")
    return root


def drop_into_checkout(root: Path, rows: list[dict[str, str]]) -> Path:
    """Write the rows into the checkout's CSV drop zone and return the file path."""
    target = root / "data" / "raw" / "csv" / DROP_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    write_client_intel_csv(target, rows)
    return target
