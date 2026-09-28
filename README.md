# AI Agent SMS CRM Extractor

A local command-line tool that turns a phone's contacts export and an Android SMS backup into a small CRM: contacts, job leads, payment clues and a review queue.

It's for small service businesses whose customer history lives in a phone. Saved contacts become the seed customer list, and SMS/MMS threads add job, address and payment evidence to each one. It is written so an AI agent can run it on the owner's computer without the messages leaving that machine.

It pairs with [Client Intel Dashboard](https://github.com/whosebruce/client-intel-dashboard): the extractor finds the customers in a phone, and Client Intel puts them on a map with a follow-up queue. Version 0.2.0 (September 2026) adds that hand-off; 0.1.0 was published in June 2026.

## How it keeps data local

- Pure Python standard library with no third-party dependencies.
- No network code and no LLM calls. Extraction is keyword and pattern matching.
- `extract` asks for confirmation before it reads anything. `--yes` skips the prompt for scripted runs.
- `dashboard.html` is a single static file with no scripts and no external requests. Its fonts are embedded.

The outputs themselves are sensitive. See [Privacy](#privacy) below.

## Install

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

This installs the `sms-crm` command.

## Inputs

- `contacts.vcf` exported from Android Contacts, Google Contacts or iCloud. Optional, but matching is much better with it.
- An `.xml` backup from the Android app **SMS Backup & Restore** (SyncTech). SMS is enough; MMS is optional, and only the text parts of an MMS are read.

### Export contacts from Android

1. Open the Contacts app.
2. Go to **Fix & manage** or **Manage contacts**.
3. Choose **Export to file** and save the `.vcf` locally.
4. Move it to the computer over USB or another local transfer.

### Export SMS from Android

1. Install and open **SMS Backup & Restore**.
2. Back up SMS (MMS optional) to local storage.
3. Move the `.xml` file to the computer the same way.

## Usage

Try it on the bundled sample data first:

```bash
sms-crm extract \
  --contacts tests/fixtures/sample_contacts.vcf \
  --sms tests/fixtures/sample_sms.xml \
  --output output/sample \
  --yes
```

Check that real exports parse, without writing anything:

```bash
sms-crm validate \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml
```

Then extract:

```bash
sms-crm extract \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml \
  --output ~/sms-crm-extraction/output
```

`--contacts` is optional. Without it, contacts are built from the SMS threads alone, using the names stored in the backup when present.

The command prints counts and the output folder, never message contents.

## Send customers to Client Intel Dashboard

[Client Intel Dashboard](https://github.com/whosebruce/client-intel-dashboard) is the companion app: a local map of customers with paid, due and lead status and a follow-up queue. Every run writes `client_intel.csv` in its import format, with one row per likely or possible customer. Contacts without enough customer evidence (friends, family, verification codes) are left out.

| Client Intel column | Comes from |
| --- | --- |
| `name`, `phone` | the contact (first phone when there are several) |
| `address`, `city` | the saved contact address, or else an address found in the texts |
| `status` | the latest payment clue: paid likely → `paid`; invoice, balance or deposit → `unpaid` (shown as due); quote → `lead`; none → `lead` |
| `value` | the latest amount mentioned with a payment clue |
| `last_contact` | date of the last text |
| `notes` | customer score, job type and payment clue as labels. No message text. |
| `id`, `confidence` | stable contact id, and `sms likely` or `sms possible` |

`lat`, `lng` and `follow_up` are left blank. To drop the file straight into a Client Intel checkout, add `--client-intel`:

```bash
sms-crm extract \
  --contacts ~/sms-crm-extraction/input/contacts.vcf \
  --sms ~/sms-crm-extraction/input/sms-YYYYMMDDHHMMSS.xml \
  --output ~/sms-crm-extraction/output \
  --client-intel ~/path/to/client-intel-dashboard
```

That writes `data/raw/csv/sms-crm-extractor.csv` in the checkout and prints the next command. The rows have addresses but no coordinates, so in Client Intel set `GOOGLE_MAPS_API_KEY` and run `python3 scripts/ingest.py --json --geocode`, or they stay off the map. You can also upload `client_intel.csv` with Client Intel's **Import** button.

Payment status is still a guess from text. Client Intel shows it as a status, so check it against real payment records before chasing anyone.

## Outputs

| File | Contents |
| --- | --- |
| `contacts.csv` | One row per contact, with phone numbers, saved addresses, message counts, a customer score, tags and a preview of the last message. |
| `jobs.csv` | Job type, address and evidence snippets per contact. |
| `payments.csv` | Payment clues: status guess, confidence, amount, method and the message snippet behind it. |
| `review_needed.csv` | Items a person should check: payment signals, likely customers missing from contacts, and saved contacts with no texts. |
| `client_intel.csv` | Likely and possible customers in Client Intel Dashboard's import format. No message text. |
| `messages.csv` | Every parsed message with its full text. |
| `crm.sqlite` | The same five tables in SQLite. |
| `dashboard.html` | A static report styled like Client Intel: counts, the Client Intel next step, and tables of customers, payment clues, jobs and the review queue. About 120 KB because the fonts are embedded. |
| `audit_log.json` | Counts, SHA-256 hashes of the input files and the privacy flags. |

## How it decides

- **Matching:** phone numbers are reduced to digits, and an 11-digit number starting with 1 drops the country code. Matching is tuned for US numbers. A contact with several numbers stays one CRM contact.
- **Customer score:** points for being in contacts, a saved address, business keywords, addresses in messages, payment language and a two-way thread. Verification codes and promo texts lower the score. The result is `likely_customer`, `possible_customer` or `not_enough_evidence`.
- **Payment status:** phrase matching produces guesses such as `paid_likely`, `invoice_sent`, `overdue_possible` or `quoted`, each with a confidence. Treat these as a review queue, not accounting truth. Confirm against real payment records before acting on them.

## Privacy

- `messages.csv` and `crm.sqlite` hold the full text of every message in the backup, including personal ones. `contacts.csv`, `jobs.csv`, `payments.csv` and `dashboard.html` include message snippets. `client_intel.csv` has names, phones, addresses and amounts but no message text.
- Outputs are plain, unencrypted files. Write them to a folder only the data owner can read, and delete them when they're no longer needed.
- `.gitignore` covers `input/`, `output/`, `*.xml`, `*.vcf` (except the test fixtures), `*.sqlite` and `*.db`. CSV, HTML and JSON outputs are only ignored inside `output/` or `input/`, so don't point `--output` at another folder in the repo.
- Don't upload the exports or outputs anywhere unless the data owner explicitly approves.

### Using it with an AI agent

[`AGENT_README.md`](AGENT_README.md) is a prompt to paste into an agent that is helping someone run the tool. It tells the agent to stay local, avoid online converters and remote APIs, stop before anything that would send data over the network, and report counts and paths instead of message contents.

## Development

```text
sms_crm_extractor/
  cli.py       sms-crm extract / validate
  vcf.py       vCard parser (FN, N, TEL, ADR, NOTE; quoted-printable)
  sms_xml.py   SMS Backup & Restore XML parser (streaming)
  crm.py       matching, scoring, job and payment signals
  rules.py     keyword lists and patterns
  output.py    CSV, SQLite and audit writers
  report.py    dashboard.html report
  client_intel.py  client_intel.csv and --client-intel hand-off
  assets/fonts/    OFL fonts embedded in the report
tests/         smoke tests and synthetic fixtures (555 numbers, example addresses)
```

The tests use pytest, which isn't a package dependency:

```bash
pip install pytest
pytest
```

## License

MIT. See [LICENSE](LICENSE).

Maintained by Jonathan Bruce ([@whosebruce](https://github.com/whosebruce)).
