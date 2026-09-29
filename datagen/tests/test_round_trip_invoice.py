"""The invoice leg of the exchange: the supplier's record writes a conformant UBL 2.3 Invoice, the retailer reads it into the same record, and both validate."""
import os
import sys
from decimal import Decimal

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from halvorsen_invoices import generate_invoices  # noqa: E402
from instance import read_tree  # noqa: E402
from invoice import INVOICE_CT, IR, projected_invoice, read_invoice, validate_ubl_invoice, write_invoice  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import RETAILER_TRANSLATOR, record  # noqa: E402

CASES = [(kh, kv, ih, iv, ixml) for *_, kh, kv, kxml, ih, iv, ixml in generate_invoices(52)]   # the year the stacks load
K = "Receipt Advice Governed Record/Receipt Advice/Receipt Lines/Receipt Line %d/Receipt Line/"
L = "Invoice Governed Record/Invoice/Invoice Lines/Invoice Line %d/Invoice Line/"


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{INVOICE_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def invoice_values(xml):
    return read_tree(xml, Schema.for_dm(INVOICE_CT)).get(*IR).paths(IR)


def test_the_invoices_bill_what_the_receipt_says_arrived_and_validate(sdc_schema):
    kinds = {ih["kind"] for _, _, ih, _, _ in CASES}
    assert kinds == {"standard", "deposit"}, kinds
    for kh, kv, ih, values, xml in CASES:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (ih["invoice_id"], errors[:3])
        assert "Halvorsen Foods billing system" in xml and "OrderPaymentDue" in xml
        total = Decimal("0")
        for n in range(1, ih["lines"] + 1):
            assert values[L % n + "Invoiced Quantity"].magnitude == kv[K % n + "Received Quantity"].magnitude
            total += Decimal(values[L % n + "Line Extension Amount"].magnitude)
        assert Decimal(ih["payable"]) == total - Decimal(ih["prepaid"])


def test_the_retailer_reads_the_invoice_into_the_same_record(sdc_schema):
    for kh, kv, ih, values, xml in CASES:
        ubl = write_invoice(xml)
        assert not validate_ubl_invoice(ubl), (ih["invoice_id"], validate_ubl_invoice(ubl)[:3])
        back = read_invoice(ubl)
        assert back == projected_invoice(invoice_values(xml)), ih["invoice_id"]
        retailer = record("Invoice", back, document_id=ih["invoice_id"], buyer=ih["seller"], when=f"{ih['issued']}T19:00:00",
                          source=(f"urn:halvorsen:invoice:{ih['invoice_id']}:ubl", f"{ih['invoice_id']}.xml", "The UBL 2.3 Invoice received"),
                          agent=RETAILER_TRANSLATOR, current_state="OrderPaymentDue")
        errors = [str(e) for e in sdc_schema.iter_errors(retailer)]
        assert not errors, (ih["invoice_id"], errors[:3])
        assert "Kestrel Mercantile document translator" in retailer
        assert write_invoice(retailer) == ubl, ih["invoice_id"]
