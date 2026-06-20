from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .crm import build_crm
from .output import write_outputs
from .sms_xml import parse_sms_xml
from .vcf import parse_vcf

CONSENT = """This tool processes private contacts and SMS messages locally.
It may extract names, phone numbers, addresses, job details, and payment-related text.
No data is uploaded and no LLM/API is called by this tool.
Continue? [y/N] """


def cmd_extract(args: argparse.Namespace) -> int:
    if not args.yes:
        answer = input(CONSENT).strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 2
    contacts = parse_vcf(args.contacts) if args.contacts else []
    messages = list(parse_sms_xml(args.sms))
    result = build_crm(contacts, messages, sms_path=args.sms, contacts_path=args.contacts)
    write_outputs(args.output, result)
    print("SMS CRM extraction complete.")
    print(f"Messages parsed: {result.summary['messages_processed']}")
    print(f"Contacts seeded: {result.summary['contacts_seeded_from_vcf']}")
    print(f"CRM contacts: {result.summary['crm_contacts']}")
    print(f"Jobs detected: {result.summary['jobs_detected']}")
    print(f"Payment signals: {result.summary['payment_signals_detected']}")
    print(f"Review items: {result.summary['review_items']}")
    print(f"Output folder: {Path(args.output).resolve()}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    n_contacts = len(parse_vcf(args.contacts)) if args.contacts else 0
    n_messages = sum(1 for _ in parse_sms_xml(args.sms))
    print("Validation OK")
    if args.contacts:
        print(f"Contacts parsed: {n_contacts}")
    print(f"SMS/MMS messages parsed: {n_messages}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sms-crm", description="Local Android contacts + SMS Backup XML to contractor CRM extractor")
    sub = p.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("extract", help="extract CRM files")
    ex.add_argument("--contacts", help="optional contacts .vcf export")
    ex.add_argument("--sms", required=True, help="SMS Backup & Restore .xml file")
    ex.add_argument("--output", required=True, help="output folder")
    ex.add_argument("--yes", action="store_true", help="accept local privacy warning non-interactively")
    ex.set_defaults(func=cmd_extract)

    val = sub.add_parser("validate", help="parse inputs and print counts only")
    val.add_argument("--contacts", help="optional contacts .vcf export")
    val.add_argument("--sms", required=True, help="SMS Backup & Restore .xml file")
    val.set_defaults(func=cmd_validate)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
