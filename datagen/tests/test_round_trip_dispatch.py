"""The dispatch leg of the exchange: the supplier's record writes a conformant UBL 2.3 DespatchAdvice, the retailer reads it into the same record, and both validate."""
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from dispatch_advice import DISPATCH_CT, DR, projected_dispatch, read_dispatch_advice, validate_ubl_dispatch, write_dispatch_advice  # noqa: E402
from halvorsen_dispatch import generate_dispatches  # noqa: E402
from instance import read_tree  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import RETAILER_TRANSLATOR, record  # noqa: E402

CASES = [(dh, dv, dxml) for _, _, _, _, _, _, dh, dv, dxml in generate_dispatches(52)]   # the year the stacks load: the seed the generator runs with
U = "Despatch Advice Governed Record/Despatch Advice/Shipment/Transport Handling Units/Transport Handling Unit 1/Transport Handling Unit/"


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{DISPATCH_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def dispatch_values(xml):
    return read_tree(xml, Schema.for_dm(DISPATCH_CT)).get(*DR).paths(DR)


def test_every_kind_of_dispatch_occurs_with_the_notice_facts_and_the_dispatches_validate(sdc_schema):
    kinds = {dh["kind"] for dh, _, _ in CASES}
    assert kinds == {"complete", "short", "canceled-line", "substituted"}, kinds
    assert any(dh["pallet_lapses"] for dh, _, _ in CASES) and any(dh["pack_stale"] for dh, _, _ in CASES)
    for dh, values, xml in CASES:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (dh["dispatch_id"], errors[:3])
        assert "Halvorsen Foods warehouse system" in xml
        if dh["pallet_lapses"]:
            assert values[U + "Pallet Identification/Date Range/Date Range End"] == dh["issued"]


def test_the_retailer_reads_the_dispatch_into_the_same_record(sdc_schema):
    for dh, values, xml in CASES:
        ubl = write_dispatch_advice(xml)
        assert not validate_ubl_dispatch(ubl), (dh["dispatch_id"], validate_ubl_dispatch(ubl)[:3])
        back = read_dispatch_advice(ubl)
        assert back == projected_dispatch(dispatch_values(xml)), dh["dispatch_id"]
        retailer = record("Despatch Advice", back, document_id=dh["dispatch_id"], buyer=dh["seller"], when=f"{dh['issued']}T18:00:00",
                          source=(f"urn:halvorsen:dispatch:{dh['dispatch_id']}:ubl", f"{dh['dispatch_id']}.xml", "The UBL 2.3 DespatchAdvice received"),
                          agent=RETAILER_TRANSLATOR, current_state="OrderInTransit")
        errors = [str(e) for e in sdc_schema.iter_errors(retailer)]
        assert not errors, (dh["dispatch_id"], errors[:3])
        assert "Kestrel Mercantile document translator" in retailer
        assert write_dispatch_advice(retailer) == ubl, dh["dispatch_id"]
