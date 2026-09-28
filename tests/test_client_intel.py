"""Client Intel hand-off: client_intel.csv, --client-intel, and the report page. Synthetic fixtures only."""
import csv
from pathlib import Path

import pytest

from sms_crm_extractor.cli import main
from sms_crm_extractor.client_intel import FIELDS, client_intel_rows
from sms_crm_extractor.crm import build_crm
from sms_crm_extractor.models import CrmContact, PaymentSignal
from sms_crm_extractor.report import render_report
from sms_crm_extractor.sms_xml import parse_sms_xml
from sms_crm_extractor.vcf import parse_vcf

FIX = Path(__file__).parent / "fixtures"
ARGS = ["--contacts", str(FIX / "sample_contacts.vcf"), "--sms", str(FIX / "sample_sms.xml")]


def sample_crm():
    return build_crm(parse_vcf(FIX / "sample_contacts.vcf"), list(parse_sms_xml(FIX / "sample_sms.xml")))


def test_rows_use_the_dashboard_schema_and_skip_non_customers():
    crm = sample_crm()
    rows = {r["name"]: r for r in crm.client_intel}
    assert set(rows) == {"Sample Contact One", "Sample Contact Two"}  # the verification-code thread stays out
    assert crm.summary["client_intel_rows"] == 2
    assert crm.summary["client_intel_skipped_not_enough_evidence"] == 1
    assert all(list(r) == FIELDS for r in crm.client_intel)


def test_status_value_and_address_come_from_the_crm():
    rows = {r["name"]: r for r in sample_crm().client_intel}
    one, two = rows["Sample Contact One"], rows["Sample Contact Two"]
    assert (one["status"], one["value"]) == ("lead", "$850")  # latest clue is a quote
    assert (two["status"], two["value"]) == ("paid", "$500")
    assert one["address"] == "100 Example St, Example City, CA, 90210, USA"
    assert one["city"] == "Example City"
    assert one["phone"] == "(202) 555-0101"
    assert one["last_contact"] == "2023-11-18"
    assert one["lat"] == one["lng"] == ""


def test_rows_never_carry_message_text():
    crm = sample_crm()
    bodies = [m.body for m in crm.messages if len(m.body) > 12]
    for row in crm.client_intel:
        blob = " ".join(row.values())
        assert not any(body in blob for body in bodies)


def test_latest_payment_clue_wins():
    contact = CrmContact("c1", "Jo", "(202) 555-0100", "2025550100", "", "sms_only", likely_customer="likely_customer", customer_confidence=0.9)

    def pay(status, ts, amount=""):
        return PaymentSignal("p" + ts, "c1", "", "Jo", status, 0.8, amount, "", ts, "", "", True)

    rows, _ = client_intel_rows([contact], [], [pay("invoice_sent", "2026-01-01", "$300"), pay("paid_likely", "2026-01-05"), pay("mentioned", "2026-01-06")], [])
    assert rows[0]["status"] == "paid"
    assert rows[0]["value"] == "$300"


def test_extract_writes_client_intel_csv(tmp_path):
    assert main(["extract", *ARGS, "--output", str(tmp_path / "out"), "--yes"]) == 0
    with (tmp_path / "out" / "client_intel.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2


def test_client_intel_flag_drops_into_a_checkout(tmp_path, capsys):
    checkout = tmp_path / "client-intel-dashboard"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts" / "ingest.py").write_text("# stub\n")
    assert main(["extract", *ARGS, "--output", str(tmp_path / "out"), "--client-intel", str(checkout), "--yes"]) == 0
    drop = checkout / "data" / "raw" / "csv" / "sms-crm-extractor.csv"
    assert drop.read_text(encoding="utf-8").startswith(",".join(FIELDS))
    assert "scripts/ingest.py --json --geocode" in capsys.readouterr().out


def test_client_intel_flag_rejects_a_wrong_folder_before_reading(tmp_path, capsys):
    rc = main(["extract", *ARGS, "--output", str(tmp_path / "out"), "--client-intel", str(tmp_path), "--yes"])
    assert rc == 1
    assert "client-intel-dashboard checkout" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_report_is_self_contained_and_escaped():
    crm = sample_crm()
    crm.contacts[0].name = "<script>alert(1)</script>"
    html = render_report(crm)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert 'src="http' not in html and "url(http" not in html and "@import" not in html
    assert "client_intel.csv" in html and "Client Intel" in html
    assert "data:font/woff;base64," in html


@pytest.mark.parametrize("flag", ["--help"])
def test_help_mentions_client_intel(flag, capsys):
    with pytest.raises(SystemExit):
        main(["extract", flag])
    assert "--client-intel" in capsys.readouterr().out
