"""The payment runs: every invoice paid once less the credit note a Receipt permitted, round-tripped as a UBL 2.3 RemittanceAdvice."""
import os
import random
import sys
from decimal import Decimal

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "datagen"))
sys.path.insert(0, os.path.join(ROOT, "ubl"))
from halvorsen_remittances import generate_remittances  # noqa: E402
from instance import read_tree  # noqa: E402
from remittance_advice import MR, REMITTANCE_CT, projected_remittance_advice, read_remittance_advice, validate_ubl_remittance_advice, write_remittance_advice  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import SUPPLIER_TRANSLATOR, record  # noqa: E402

CASES = list(generate_remittances(52, seed="halvorsen-2026"))


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{REMITTANCE_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def test_every_invoice_is_paid_once_and_the_runs_validate(sdc_schema):
    invoices = [i for mh, _, _ in CASES for i in mh["invoices"]]
    assert len(invoices) == 52 == len(set(invoices))
    for mh, mv, xml in CASES:
        assert Decimal(mh["paid"]) == Decimal(mh["debit"]) - Decimal(mh["credit"]) and 1 <= mh["lines"] <= 10
        assert "Kestrel Mercantile payment system" in xml and "OrderDelivered" in xml
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (mh["remittance_id"], errors[:3])


def test_the_runs_round_trip_as_conformant_ubl_remittance_advices(sdc_schema):
    for mh, mv, xml in CASES:
        ubl = write_remittance_advice(xml)
        assert not validate_ubl_remittance_advice(ubl), (mh["remittance_id"], validate_ubl_remittance_advice(ubl)[:3])
        assert ubl.count("<cac:CreditNoteDocumentReference>") == len(mh["credit_notes"]) and ">Invoice<" in ubl
        back = read_remittance_advice(ubl)
        assert back == projected_remittance_advice(read_tree(xml, Schema.for_dm(REMITTANCE_CT)).get(*MR).paths(MR))
        again = record("Remittance Advice", back, document_id=mh["remittance_id"], buyer=mh["payer"], when=f"{mh['paid_on']}T12:00:00",
                       source=(f"urn:kestrel:remittance:{mh['remittance_id']}:ubl", f"{mh['remittance_id']}.xml", "The UBL 2.3 RemittanceAdvice received"), agent=SUPPLIER_TRANSLATOR, current_state="OrderDelivered")
        assert not [str(e) for e in sdc_schema.iter_errors(again)] and write_remittance_advice(again) == ubl
