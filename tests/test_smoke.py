from pathlib import Path
from sms_crm_extractor.vcf import parse_vcf
from sms_crm_extractor.sms_xml import parse_sms_xml
from sms_crm_extractor.crm import build_crm

FIX = Path(__file__).parent / "fixtures"


def test_parse_contacts():
    contacts = parse_vcf(FIX / "sample_contacts.vcf")
    assert len(contacts) == 2
    assert contacts[0].name == "Sample Contact One"
    assert contacts[0].phones[0].normalized.endswith("2025550101")
    assert "100 Example St" in contacts[0].addresses[0].formatted


def test_parse_sms_and_build_crm():
    contacts = parse_vcf(FIX / "sample_contacts.vcf")
    messages = list(parse_sms_xml(FIX / "sample_sms.xml"))
    assert len(messages) == 6
    crm = build_crm(contacts, messages)
    assert crm.summary["messages_processed"] == 6
    contact_one = next(c for c in crm.contacts if c.name == "Sample Contact One")
    assert contact_one.message_count == 3
    assert contact_one.likely_customer in {"likely_customer", "possible_customer"}
    contact_two_payments = [p for p in crm.payments if "Sample Contact Two" in p.contact_name]
    assert contact_two_payments
    assert max(p.confidence for p in contact_two_payments) >= 0.8
