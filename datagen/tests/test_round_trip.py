"""The exchange: the retailer's record writes a conformant UBL 2.3 Order, the supplier reads it into the same record, and both validate."""
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from halvorsen import generate  # noqa: E402
from instance import read_tree  # noqa: E402
from order import ORDER_CT, R, projected, read_order, validate_ubl, write_order  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import SUPPLIER_TRANSLATOR, record  # noqa: E402

ORDERS = list(generate(6, seed="round-trip"))


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{ORDER_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def order_values(instance_xml: str) -> dict:
    return read_tree(instance_xml, Schema.for_dm(ORDER_CT)).get(*R).paths(R)


def test_the_retailers_records_validate_under_the_order_schema(sdc_schema):
    for h, values, xml in ORDERS:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (h["order_id"], errors[:3])
        assert "Kestrel Mercantile order system" in xml


def test_every_document_written_is_a_conformant_ubl_order():
    for h, values, xml in ORDERS:
        ubl = write_order(xml)
        assert not validate_ubl(ubl), (h["order_id"], validate_ubl(ubl)[:3])
        assert "UBLExtensions" not in ubl


def test_the_supplier_reads_the_document_into_the_same_record(sdc_schema):
    """Retailer record -> document -> supplier record: the same order values, the supplier's own provenance, both valid."""
    for h, values, xml in ORDERS:
        ubl = write_order(xml)
        back = read_order(ubl)
        assert back == projected(order_values(xml)), h["order_id"]
        supplier = record("Order", back, document_id=h["order_id"], buyer=h["buyer"], when=f"{h['issued']}T{h['received_time']}",
                          source=(f"urn:kestrel:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order received"), agent=SUPPLIER_TRANSLATOR)
        errors = [str(e) for e in sdc_schema.iter_errors(supplier)]
        assert not errors, (h["order_id"], errors[:3])
        assert "Halvorsen Foods document translator" in supplier and f"{h['order_id']}.xml" in supplier
        assert write_order(supplier) == ubl, h["order_id"]   # the supplier's projection is byte for byte the document it received
