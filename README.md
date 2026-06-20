# AI Agent SMS CRM Extractor

Local-first **contacts + Android SMS Backup & Restore XML** to lightweight CRM extractor for small service businesses and AI-agent workflows.

The tool is designed for scenarios where a business owner already has useful customer records saved in their phone contacts: names, numbers, and sometimes addresses. It uses that contact export as the seed customer database, then enriches those contacts from SMS/MMS history.

## What it does

1. Imports contacts from a `.vcf` export.
2. Uses saved contact phone numbers and addresses as the seed CRM.
3. Parses Android `SMS Backup & Restore` XML.
4. Matches message threads back to known contacts by phone number.
5. Finds conservative customer/job/payment/address clues.
6. Outputs local files only: CSV, SQLite, HTML dashboard, and JSON audit.

No cloud upload. No external API calls. No LLM calls by default.

## AI agent safe-use promise

This repository is meant to be easy for an AI agent to run on a user's own computer without leaking private messages.

Agents should follow these rules:

- Run locally only.
- Do not upload `.vcf`, `.xml`, CSV, SQLite, HTML, or message contents.
- Do not paste private message contents into chat.
- Do not use remote workbenches, online converters, telemetry, or external APIs.
- Report counts and file paths by default, not private customer text.
- Treat payment status as an inferred review queue, not accounting truth.

See [`AGENT_README.md`](AGENT_README.md) for a copy/paste agent prompt.

## Why contacts first?

Contacts-first extraction is usually cleaner than scraping all messages and guessing who matters:

- Contacts become the seed customer database.
- Saved phone numbers and addresses anchor matching.
- SMS is used to enrich each contact with job/payment/follow-up evidence.
- Unknown message numbers still appear in review, but the main customer list starts from trusted phone contacts.
- Contacts with multiple phone numbers stay grouped as one CRM contact.

## Install locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

## Inputs

Recommended:

- `contacts.vcf` exported from Android Contacts / Google Contacts / iCloud Contacts.
- `sms.xml` exported from Android app **SMS Backup & Restore** by SyncTech.

## Run sample

```bash
sms-crm extract \
  --contacts tests/fixtures/sample_contacts.vcf \
  --sms tests/fixtures/sample_sms.xml \
  --output output/sample \
  --yes
```

## Run on real data

```bash
sms-crm extract \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml \
  --output ~/sms-crm-extraction/output \
  --yes
```

Contacts are optional but strongly recommended:

```bash
sms-crm extract --sms sms.xml --output output --yes
```

## Outputs

- `contacts.csv` — CRM-ready contact/customer list.
- `jobs.csv` — job/address/opportunity signals.
- `payments.csv` — payment/quote/invoice clues with confidence and evidence snippets.
- `review_needed.csv` — rows a human should inspect manually.
- `messages.csv` — normalized message metadata and message text.
- `crm.sqlite` — same data in SQLite.
- `dashboard.html` — local browser review dashboard.
- `audit_log.json` — counts, input hashes, and privacy flags.

## Safety limits

Payment status is inferred from text and can be wrong. Treat it as a review queue, not accounting truth. For real payment verification, match against actual payment systems or accounting records.

## Export contacts from Android

Usually:

1. Open Contacts app.
2. Go to **Fix & manage** / **Manage contacts**.
3. Choose **Export to file**.
4. Save `.vcf` locally.
5. Transfer `.vcf` to the laptop by USB/flash drive/local transfer.

## Export SMS from Android

1. Install/open **SMS Backup & Restore**.
2. Set up a backup.
3. Select SMS. MMS optional.
4. Choose local backup.
5. Transfer `.xml` to the laptop.

## Privacy

Treat `.vcf`, `.xml`, CSVs, SQLite, and HTML as sensitive. Do not commit real exports or outputs to git. Do not upload them unless the data owner explicitly approves.
