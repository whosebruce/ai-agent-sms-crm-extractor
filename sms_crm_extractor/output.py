from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from html import escape

from .models import CrmContact, CrmResult, JobSignal, Message, PaymentSignal, ReviewItem

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


def write_dashboard(path: Path, result: CrmResult) -> None:
    top_contacts = sorted(result.contacts, key=lambda c: (c.customer_confidence, c.message_count), reverse=True)[:200]
    top_payments = sorted(result.payments, key=lambda p: p.confidence, reverse=True)[:200]
    def table(headers, rows):
        out = ["<table><thead><tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr></thead><tbody>"]
        for row in rows:
            out.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>")
        out.append("</tbody></table>")
        return "\n".join(out)
    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>SMS CRM Dashboard</title>
<style>body{{font-family:Inter,Arial,sans-serif;margin:32px;background:#f8fafc;color:#0f172a}} .card{{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px;margin:16px 0;box-shadow:0 1px 3px #0001}} table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid #e2e8f0;text-align:left;padding:8px;vertical-align:top}} th{{background:#f1f5f9}} .warn{{color:#b45309}}</style>
</head><body>
<h1>SMS CRM Dashboard</h1>
<p class='warn'><strong>Privacy:</strong> local report. Payment status is inferred and must be reviewed before business decisions.</p>
<div class='card'><h2>Summary</h2><pre>{escape(json.dumps(result.summary, indent=2))}</pre></div>
<div class='card'><h2>Top Contacts</h2>{table(['Name','Phone','Saved Address','Messages','Customer','Confidence','Tags','Review'], [[c.name,c.primary_phone,c.saved_addresses,c.message_count,c.likely_customer,f'{c.customer_confidence:.2f}',c.tags,c.needs_review] for c in top_contacts])}</div>
<div class='card'><h2>Payment Signals</h2>{table(['Contact','Phone','Status','Confidence','Amount','Method','Evidence'], [[p.contact_name,p.primary_phone,p.status_guess,f'{p.confidence:.2f}',p.amount,p.payment_method,p.evidence] for p in top_payments])}</div>
</body></html>"""
    path.write_text(html, encoding="utf-8")


def write_outputs(outdir: str | Path, result: CrmResult) -> None:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "contacts.csv", result.contacts, SCHEMAS["contacts"])
    write_csv(out / "messages.csv", result.messages, SCHEMAS["messages"])
    write_csv(out / "jobs.csv", result.jobs, SCHEMAS["jobs"])
    write_csv(out / "payments.csv", result.payments, SCHEMAS["payments"])
    write_csv(out / "review_needed.csv", result.review, SCHEMAS["review_needed"])
    write_sqlite(out / "crm.sqlite", result)
    write_dashboard(out / "dashboard.html", result)
    (out / "audit_log.json").write_text(json.dumps(result.summary, indent=2), encoding="utf-8")
