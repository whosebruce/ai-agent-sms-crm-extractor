# Agent README: Local Contacts-First SMS CRM Extraction

Copy/paste this into an AI agent that is helping a data owner run the tool on their own computer.

---

You are helping the user build a **local customer/contact database from their phone**, starting from their **Contacts** export first and then enriching those contacts from Android SMS history.

Privacy rules:

- Treat contacts and SMS as sensitive personal/business records.
- Do not upload `.vcf`, `.xml`, CSV, SQLite, HTML, or message contents to any cloud service.
- Do not use remote workbenches, online converters, external APIs, or LLMs on message bodies.
- Run everything locally on the user's computer unless the user explicitly approves otherwise.
- Stop before any command that would send customer/private data over the network.
- Report counts and paths by default. Do not print private message contents unless the user explicitly asks.

## 1) Export contacts first

On Android:

1. Open **Contacts**.
2. Go to **Fix & manage** or **Manage contacts**.
3. Choose **Export to file**.
4. Save a `.vcf` file locally.
5. Transfer it to the computer by USB/flash drive/local method.

Place it here:

```bash
mkdir -p ~/sms-crm-extraction/input ~/sms-crm-extraction/output
# put contacts.vcf inside ~/sms-crm-extraction/input/
```

Expected:

```text
~/sms-crm-extraction/input/contacts.vcf
```

## 2) Export Android SMS

On Android:

1. Install/open **SMS Backup & Restore** by SyncTech.
2. Create a local backup of SMS. MMS optional.
3. Transfer the resulting `.xml` file to the computer locally.

Expected:

```text
~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml
```

## 3) Install and run the extractor

From the repo folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Validate without writing CRM outputs:

```bash
sms-crm validate \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml
```

Run extraction:

```bash
sms-crm extract \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml \
  --output ~/sms-crm-extraction/output \
  --yes
```

## 4) Verify outputs

```bash
find ~/sms-crm-extraction/output -maxdepth 1 -type f -print
sqlite3 ~/sms-crm-extraction/output/crm.sqlite ".tables"
sqlite3 ~/sms-crm-extraction/output/crm.sqlite "SELECT 'contacts', COUNT(*) FROM contacts UNION ALL SELECT 'messages', COUNT(*) FROM messages UNION ALL SELECT 'payments', COUNT(*) FROM payments;"
```

Open local dashboard:

macOS:

```bash
open ~/sms-crm-extraction/output/dashboard.html
```

Linux:

```bash
xdg-open ~/sms-crm-extraction/output/dashboard.html
```

Windows PowerShell:

```powershell
start $HOME\sms-crm-extraction\output\dashboard.html
```

## Final response format

Report only counts and paths unless the user asks for private details:

```text
Completed local contacts-first SMS CRM extraction.
Input contacts: [path]
Input SMS: [path]
Output folder: [path]
Messages parsed: [number]
Contacts seeded: [number]
CRM contacts: [number]
Jobs detected: [number]
Payment signals: [number]
Review items: [number]
Privacy: no cloud upload, no external API/LLM used.
Important: payment status is inferred from text and requires human review.
```
