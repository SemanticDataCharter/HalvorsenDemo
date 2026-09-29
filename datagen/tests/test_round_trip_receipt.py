"""The receipt leg of the exchange: the retailer's record writes a conformant UBL 2.3 ReceiptAdvice, the supplier reads it into the same record, and both validate."""
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from halvorsen_receipts import generate_receipts  # noqa: E402
from instance import read_tree  # noqa: E402
from receipt_advice import KR, RECEIPT_CT, projected_receipt, read_receipt_advice, validate_ubl_receipt, write_receipt_advice  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import SUPPLIER_TRANSLATOR, record  # noqa: E402

CASES = [(dh, kh, kv, kxml) for _, _, _, _, _, _, dh, _, _, kh, kv, kxml in generate_receipts(52)]   # the year the stacks load
U = "Receipt Advice Governed Record/Receipt Advice/Receipt Shipment/Received Handling Units/Received Handling Unit 1/Received Handling Unit/"


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{RECEIPT_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def receipt_values(xml):
    return read_tree(xml, Schema.for_dm(RECEIPT_CT)).get(*KR).paths(KR)


def test_every_kind_of_receipt_occurs_the_checks_hold_against_the_receipt_date_and_the_receipts_validate(sdc_schema):
    kinds = {kh["kind"] for _, kh, _, _ in CASES}
    assert kinds == {"complete", "short", "rejected", "late"}, kinds
    assert any(dh["pallet_lapses"] for dh, _, _, _ in CASES) and any(dh["pack_stale"] for dh, _, _, _ in CASES)
    for dh, kh, values, xml in CASES:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (kh["receipt_id"], errors[:3])
        assert "Kestrel Mercantile receiving system" in xml
        assert ("OrderProblem" in xml) == bool(kh["exceptions"])
        if dh["pallet_lapses"]:
            assert values[U + "Pallet ID Valid on Receipt"] is False and values[U + "Receiving Condition"] == "Accepted with exception"
        if dh["pack_stale"]:
            assert values[U + "Pack Specification Compliant"] is False


def test_the_supplier_reads_the_receipt_into_the_same_record(sdc_schema):
    for dh, kh, values, xml in CASES:
        ubl = write_receipt_advice(xml)
        assert not validate_ubl_receipt(ubl), (kh["receipt_id"], validate_ubl_receipt(ubl)[:3])
        back = read_receipt_advice(ubl)
        assert back == projected_receipt(receipt_values(xml)), kh["receipt_id"]
        supplier = record("Receipt Advice", back, document_id=kh["receipt_id"], buyer=kh["buyer"], when=f"{kh['received']}T19:00:00",
                          source=(f"urn:kestrel:receipt:{kh['receipt_id']}:ubl", f"{kh['receipt_id']}.xml", "The UBL 2.3 ReceiptAdvice received"),
                          agent=SUPPLIER_TRANSLATOR, current_state="OrderProblem" if kh["exceptions"] else "OrderDelivered")
        errors = [str(e) for e in sdc_schema.iter_errors(supplier)]
        assert not errors, (kh["receipt_id"], errors[:3])
        assert "Halvorsen Foods document translator" in supplier
        assert write_receipt_advice(supplier) == ubl, kh["receipt_id"]
