"""The credit notes of the settled deductions: one per Receipt that permitted a receipt advice's transition, naming the Receipt, round-tripped as a UBL 2.3 CreditNote."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "datagen"))
sys.path.insert(0, os.path.join(ROOT, "ubl"))
sys.path.insert(0, os.path.join(ROOT, "settlement"))
from credit_note import CR, CREDIT_NOTE_CT, projected_credit_note, read_credit_note, validate_ubl_credit_note, write_credit_note  # noqa: E402
from entries import norm  # noqa: E402
from halvorsen_credit_notes import credit_note  # noqa: E402
from halvorsen_invoices import generate_invoices  # noqa: E402
from instance import read_tree  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import RETAILER_TRANSLATOR, record  # noqa: E402

INDEX = os.path.join(ROOT, "settlement", "index.json")
pytestmark = pytest.mark.skipif(not os.path.exists(INDEX), reason="no settlements issued yet (make settle)")


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{CREDIT_NOTE_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


@pytest.fixture(scope="module")
def cases():
    import random
    by_receipt = {kh["receipt_id"]: (ih, iv, kh, kv) for *_, kh, kv, kxml, ih, iv, ixml in generate_invoices(52, seed="halvorsen-2026")}
    rng = random.Random("halvorsen-2026:credit-notes")
    out = []
    for e in map(norm, json.load(open(INDEX, encoding="utf-8"))):
        if e["kind"] == "permit" and e["decision"] == "PERMIT" and e["model"] == "Receipt Advice":
            ih, iv, kh, kv = by_receipt[e["document_id"]]
            out.append((e, *credit_note(ih, iv, kh, kv, rng, source=(f"urn:vsl:receipt:{e['receipt_id']}", f"{e['receipt_id']}.json", "Settlement Receipt"))))
    return out


def test_one_credit_note_per_permitted_deduction_naming_its_receipt(cases, sdc_schema):
    assert len(cases) >= 1
    for e, ch, cv, xml in cases:
        assert ch["receipt_id"] == e["document_id"] and ch["invoice_id"] == e["invoice_id"]
        assert f"urn:vsl:receipt:{e['receipt_id']}" in xml and "Halvorsen Foods billing system" in xml and "OrderPaymentDue" in xml
        errors = [str(x) for x in sdc_schema.iter_errors(xml)]
        assert not errors, (ch["credit_note_id"], errors[:3])


def test_the_credit_note_round_trips_as_a_conformant_ubl_credit_note(cases, sdc_schema):
    for e, ch, cv, xml in cases:
        ubl = write_credit_note(xml)
        assert not validate_ubl_credit_note(ubl), (ch["credit_note_id"], validate_ubl_credit_note(ubl)[:3])
        back = read_credit_note(ubl)
        assert back == projected_credit_note(read_tree(xml, Schema.for_dm(CREDIT_NOTE_CT)).get(*CR).paths(CR))
        again = record("Credit Note", back, document_id=ch["credit_note_id"], buyer=ch["seller"], when=f"{ch['issued']}T12:00:00",
                       source=(f"urn:halvorsen:credit-note:{ch['credit_note_id']}:ubl", f"{ch['credit_note_id']}.xml", "The UBL 2.3 CreditNote received"), agent=RETAILER_TRANSLATOR, current_state="OrderPaymentDue")
        assert not [str(x) for x in sdc_schema.iter_errors(again)] and write_credit_note(again) == ubl
