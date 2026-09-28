from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path

from .client_intel import write_client_intel_csv
from .models import CrmContact, CrmResult, JobSignal, Message, PaymentSignal, ReviewItem
from .report import write_report

SCHEMAS = {
    "contacts": [f.name for f in fields(CrmContact)],
    "messages": [f.name for f in fields(Message)],
    "jobs": [f.name for f in fields(JobSignal)],
    "payments": [f.name for f in fields(PaymentSignal)],
    "review_needed": [f.name for f in fields(ReviewItem)],
}


def _rows(items):
    return [asdict(x) if is_dataclass(x) else x for x in items]


def write_csv(path: Path, items, schema: list[str]) -> None:
    rows = _rows(items)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in schema})


def write_sqlite(path: Path, result: CrmResult) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        datasets = {
            "contacts": result.contacts,
            "messages": result.messages,
            "jobs": result.jobs,
            "payments": result.payments,
            "review_needed": result.review,
        }
        for name, schema in SCHEMAS.items():
            col_defs = ", ".join([f'"{c}" TEXT' for c in schema])
            con.execute(f'CREATE TABLE "{name}" ({col_defs})')
            rows = _rows(datasets[name])
            if rows:
                placeholders = ", ".join(["?"] * len(schema))
                con.executemany(
                    f'INSERT INTO "{name}" ({", ".join(schema)}) VALUES ({placeholders})',
                    [[str(r.get(c, "")) for c in schema] for r in rows],
                )
        con.commit()
    finally:
        con.close()


def write_outputs(outdir: str | Path, result: CrmResult) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "contacts.csv", result.contacts, SCHEMAS["contacts"])
    write_csv(out / "messages.csv", result.messages, SCHEMAS["messages"])
    write_csv(out / "jobs.csv", result.jobs, SCHEMAS["jobs"])
    write_csv(out / "payments.csv", result.payments, SCHEMAS["payments"])
    write_csv(out / "review_needed.csv", result.review, SCHEMAS["review_needed"])
    write_client_intel_csv(out / "client_intel.csv", result.client_intel)
    write_sqlite(out / "crm.sqlite", result)
    write_report(out / "dashboard.html", result)
    (out / "audit_log.json").write_text(json.dumps(result.summary, indent=2), encoding="utf-8")
