"""dashboard.html: a single static report styled to match Client Intel Dashboard.

No scripts and no external requests. Fonts are embedded as data URIs from
assets/fonts/ (OFL), so the file looks the same offline and on any machine.
"""
from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from importlib import resources
from pathlib import Path

from .client_intel import REPO_URL
from .models import CrmResult

ROW_CAP = 200
FONTS = [
    ("Big Shoulders", 800, "big-shoulders-800.woff"),
    ("Barlow", 400, "barlow-400.woff"),
    ("Barlow", 600, "barlow-600.woff"),
    ("IBM Plex Mono", 500, "plex-mono-500.woff"),
]
PAYMENT_TONE = {
    "paid_likely": "paid",
    "partial_payment_possible": "due",
    "invoice_sent": "due",
    "overdue_possible": "due",
    "quoted": "lead",
}
CUSTOMER_LABEL = {"likely_customer": "Likely", "possible_customer": "Possible", "not_enough_evidence": "Not enough"}


def _font_faces() -> str:
    faces = []
    base = resources.files(__package__) / "assets" / "fonts"
    for family, weight, name in FONTS:
        try:
            data = base64.b64encode((base / name).read_bytes()).decode("ascii")
        except (FileNotFoundError, OSError):
            continue  # fall back to the system stacks below
        faces.append(f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff;base64,{data}) format('woff')}}")
    return "\n".join(faces)


CSS = """
:root{color-scheme:dark;--ground:#15181C;--panel:#1c2023;--panel-2:#22272a;--line:#3A4139;--line-soft:#2c322d;--text:#E8E4DA;--text-2:#b9bdc2;--text-3:#8A8F94;--signal:#FEB019;--alert-text:#F07563;--paid:#199e70;--due:#c98500;--lead:#3987e5;
--display:'Big Shoulders','Barlow Condensed',Impact,sans-serif;--body:'Barlow',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme:light){:root{color-scheme:light;--ground:#E0DBCE;--panel:#E8E4DA;--panel-2:#EFECE4;--line:#b9b3a4;--line-soft:#cdc7b8;--text:#15181C;--text-2:#3d4147;--text-3:#5b5f56;--alert-text:#A92E22;--paid:#1baf7a;--due:#eda100;--lead:#2a78d6}}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--text);font:400 15px/1.45 var(--body);-webkit-font-smoothing:antialiased}
.bar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:12px 20px;background:var(--panel);border-bottom:2px solid var(--line)}
.tile{width:38px;height:38px;display:grid;place-items:center;background:var(--signal);color:#15181C;font:800 19px/1 var(--display);letter-spacing:.5px}
h1{margin:0;font:800 25px/.95 var(--display);letter-spacing:1px;text-transform:uppercase}
.mono,.bar p,th,.lbl{font-family:var(--mono);font-size:11px;letter-spacing:1.4px;text-transform:uppercase}
.bar p{margin:4px 0 0;color:var(--text-3)}
.pill{margin-left:auto;display:inline-flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--line);background:var(--ground);color:var(--text-2)}
.pill i{width:8px;height:8px;background:var(--paid)}
main{max-width:1320px;margin:0 auto;padding:16px 20px 40px;display:grid;gap:14px}
.panel{background:var(--panel);border:2px solid var(--line);min-width:0}
.sec{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line-soft)}
.sec b{font:600 12px/1 var(--mono);color:var(--alert-text)}
.sec h2{margin:0;font:600 12px/1 var(--mono);letter-spacing:2.4px;text-transform:uppercase}
.sec span{flex:1;height:1px;background:var(--line-soft)}
.sec small{font:500 10px/1 var(--mono);letter-spacing:1.2px;color:var(--text-3);text-transform:uppercase}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;padding:12px}
.stat{background:var(--panel-2);border:1px solid var(--line-soft);padding:10px 12px}
.stat .lbl{color:var(--text-2);font-size:10px}
.stat strong{display:block;margin-top:6px;font:800 34px/.9 var(--display);font-variant-numeric:tabular-nums}
.handoff{border-left:4px solid var(--signal);padding:14px 16px;display:grid;gap:6px}
.handoff h3{margin:0;font:800 22px/1 var(--display);letter-spacing:1px;text-transform:uppercase}
.handoff p{margin:0;color:var(--text-2)}
code{font:500 12px/1.5 var(--mono);padding:1px 5px;background:var(--ground);border:1px solid var(--line-soft);overflow-wrap:anywhere}
a{color:var(--text)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th{position:sticky;top:0;background:var(--panel-2);color:var(--text-3);font-size:10px;text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--line-soft);vertical-align:top}
td.num,td.m{font-family:var(--mono);font-size:12px;white-space:nowrap}
td.ev{color:var(--text-2);max-width:420px}
tr:hover td{background:var(--panel-2)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:2px 7px;border:1px solid var(--line);background:var(--ground);font:500 11px/1.4 var(--mono);letter-spacing:.8px;text-transform:uppercase;white-space:nowrap}
.chip i{width:7px;height:7px;background:var(--text-3)}
.chip.paid i{background:var(--paid)}.chip.due i{background:var(--due)}.chip.lead i{background:var(--lead)}.chip.strong i{background:var(--text)}
.empty{padding:14px;color:var(--text-3)}
.note{padding:12px 14px;color:var(--text-2);font-size:14px;display:grid;gap:6px}
.note .m{font-family:var(--mono);font-size:11px;color:var(--text-3);overflow-wrap:anywhere}
@media (max-width:700px){.bar{padding:12px}.pill{margin-left:0}main{padding:12px}}
"""


def _chip(label: str, tone: str = "") -> str:
    return f'<span class="chip {tone}"><i></i>{escape(label)}</span>'


def _table(headers: list[tuple[str, str]], rows: list[list[str]], total: int) -> str:
    if not rows:
        return '<p class="empty mono">Nothing found</p>'
    head = "".join(f"<th>{escape(h)}</th>" for h, _ in headers)
    body = "".join(
        "<tr>" + "".join(f'<td class="{cls}">{cell}</td>' for (_, cls), cell in zip(headers, row)) + "</tr>"
        for row in rows
    )
    more = f'<p class="empty mono">Showing {len(rows)} of {total}. The CSV files have everything.</p>' if total > len(rows) else ""
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{more}'


def _section(n: str, title: str, meta: str, body: str) -> str:
    return f'<section class="panel"><div class="sec"><b>{n}</b><h2>{escape(title)}</h2><span></span><small>{escape(meta)}</small></div>{body}</section>'


def render_report(result: CrmResult) -> str:
    s = result.summary
    e = lambda v: escape(str(v))  # noqa: E731
    contacts = sorted(result.contacts, key=lambda c: (c.customer_confidence, c.message_count), reverse=True)
    payments = sorted(result.payments, key=lambda p: p.confidence, reverse=True)
    jobs = sorted(result.jobs, key=lambda j: j.confidence, reverse=True)
    likely = sum(1 for c in result.contacts if c.likely_customer == "likely_customer")

    stats = [
        ("Messages", s["messages_processed"]), ("Threads", s["unique_sms_threads"]), ("CRM contacts", s["crm_contacts"]),
        ("Likely customers", likely), ("Jobs", s["jobs_detected"]), ("Payment clues", s["payment_signals_detected"]),
        ("Review items", s["review_items"]),
    ]
    tiles = "".join(f'<div class="stat"><span class="lbl">{e(k)}</span><strong>{e(v)}</strong></div>' for k, v in stats)

    n_ci = s.get("client_intel_rows", len(result.client_intel))
    handoff = f"""<section class="panel handoff">
      <span class="mono">Next step // Client Intel</span>
      <h3>{n_ci} customers ready for the map</h3>
      <p><code>client_intel.csv</code> in this folder has every likely and possible customer in <a href="{REPO_URL}">Client Intel Dashboard</a>'s import format: status from the latest payment clue, amount, address and last contact. It holds no message text.</p>
      <p>Import it from Client Intel's <b>Import</b> button, or rerun with <code>--client-intel /path/to/client-intel-dashboard</code> to drop it straight in. The rows have addresses but no coordinates, so set <code>GOOGLE_MAPS_API_KEY</code> and import with geocoding to put them on the map.</p>
    </section>"""

    contact_rows = [[
        e(c.name or "Unknown"), e(c.primary_phone),
        _chip(CUSTOMER_LABEL.get(c.likely_customer, c.likely_customer), "strong" if c.likely_customer == "likely_customer" else ""),
        e(f"{c.customer_confidence:.2f}"), e(c.message_count), e(c.last_seen_at[:10]), e(c.tags), e(c.saved_addresses),
    ] for c in contacts[:ROW_CAP]]
    payment_rows = [[
        e(p.contact_name), _chip(p.status_guess.replace("_", " "), PAYMENT_TONE.get(p.status_guess, "")),
        e(f"{p.confidence:.2f}"), e(p.amount), e(p.payment_method), e(p.timestamp[:10]), e(p.evidence),
    ] for p in payments[:ROW_CAP]]
    job_rows = [[
        e(j.contact_name), _chip(j.job_type), e(j.address), e(f"{j.confidence:.2f}"), e(j.last_mentioned_at[:10]), e(j.evidence),
    ] for j in jobs[:ROW_CAP]]
    review_rows = [[
        e(r.contact_name), _chip(r.reason.replace("_", " ")), e(r.suggested_action), e(f"{r.confidence:.2f}"),
    ] for r in result.review[:ROW_CAP]]

    sections = [
        handoff,
        _section("02", "Customers", "ranked by customer score", _table(
            [("Name", ""), ("Phone", "m"), ("Customer", ""), ("Score", "num"), ("Texts", "num"), ("Last seen", "m"), ("Tags", "ev"), ("Saved address", "")],
            contact_rows, len(contacts))),
        _section("03", "Payment clues", "inferred from text // confirm before acting", _table(
            [("Contact", ""), ("Status", ""), ("Conf.", "num"), ("Amount", "m"), ("Method", ""), ("When", "m"), ("Evidence", "ev")],
            payment_rows, len(payments))),
        _section("04", "Jobs", "job type and address per contact", _table(
            [("Contact", ""), ("Job", ""), ("Address", ""), ("Conf.", "num"), ("Last mentioned", "m"), ("Evidence", "ev")],
            job_rows, len(jobs))),
        _section("05", "Review queue", "a person should check these", _table(
            [("Contact", ""), ("Reason", ""), ("Suggested action", "ev"), ("Conf.", "num")],
            review_rows, len(result.review))),
    ]
    audit = f"""<section class="panel note">
      <span class="mono">Privacy // audit</span>
      <span>Local report. No network, no LLM. Payment status is inferred from text and must be checked against real records. This file contains message snippets: keep it private and delete it when you're done.</span>
      <span class="m">SMS SHA-256 {e(s.get("sms_xml_sha256") or "n/a")}</span>
      <span class="m">Contacts SHA-256 {e(s.get("contacts_vcf_sha256") or "n/a")}</span>
    </section>"""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SMS CRM report</title>
<style>{_font_faces()}
{CSS}</style>
</head><body>
<header class="bar"><div class="tile">SC</div><div><h1>SMS CRM</h1><p>Extraction report // {e(generated)}</p></div>
<span class="pill mono"><i></i>Local only · no network · no LLM</span></header>
<main>
{_section("01", "Summary", "counts only", f'<div class="tiles">{tiles}</div>')}
{"".join(sections)}
{audit}
</main>
</body></html>"""


def write_report(path: Path, result: CrmResult) -> None:
    path.write_text(render_report(result), encoding="utf-8")
