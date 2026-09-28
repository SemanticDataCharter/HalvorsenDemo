"""The despatch leg of the exchange: the supplier's record writes a conformant UBL 2.3 DespatchAdvice, the retailer reads it into the same record, and both validate."""
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from despatch_advice import DESPATCH_CT, DR, projected_despatch, read_despatch_advice, validate_ubl_despatch, write_despatch_advice  # noqa: E402
from halvorsen_despatch import generate_despatches  # noqa: E402
from instance import read_tree  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import RETAILER_TRANSLATOR, record  # noqa: E402

CASES = [(dh, dv, dxml) for _, _, _, _, _, _, dh, dv, dxml in generate_despatches(52)]   # the year the stacks load: the seed the generator runs with
U = "Despatch Advice Governed Record/Despatch Advice/Shipment/Transport Handling Units/Transport Handling Unit 1/Transport Handling Unit/"


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{DESPATCH_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def despatch_values(xml):
    return read_tree(xml, Schema.for_dm(DESPATCH_CT)).get(*DR).paths(DR)


def test_every_kind_of_despatch_occurs_with_the_notice_facts_and_the_despatches_validate(sdc_schema):
    kinds = {dh["kind"] for dh, _, _ in CASES}
    assert kinds == {"complete", "short", "canceled-line", "substituted"}, kinds
    assert any(dh["pallet_lapses"] for dh, _, _ in CASES) and any(dh["pack_stale"] for dh, _, _ in CASES)
    for dh, values, xml in CASES:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (dh["despatch_id"], errors[:3])
        assert "Halvorsen Foods warehouse system" in xml
        if dh["pallet_lapses"]:
            assert values[U + "Pallet Identification/Date Range/Date Range End"] == dh["issued"]


def test_the_retailer_reads_the_despatch_into_the_same_record(sdc_schema):
    for dh, values, xml in CASES:
        ubl = write_despatch_advice(xml)
        assert not validate_ubl_despatch(ubl), (dh["despatch_id"], validate_ubl_despatch(ubl)[:3])
        back = read_despatch_advice(ubl)
        assert back == projected_despatch(despatch_values(xml)), dh["despatch_id"]
        retailer = record("Despatch Advice", back, document_id=dh["despatch_id"], buyer=dh["seller"], when=f"{dh['issued']}T18:00:00",
                          source=(f"urn:halvorsen:despatch:{dh['despatch_id']}:ubl", f"{dh['despatch_id']}.xml", "The UBL 2.3 DespatchAdvice received"),
                          agent=RETAILER_TRANSLATOR, current_state="OrderInTransit")
        errors = [str(e) for e in sdc_schema.iter_errors(retailer)]
        assert not errors, (dh["despatch_id"], errors[:3])
        assert "Kestrel Mercantile document translator" in retailer
        assert write_despatch_advice(retailer) == ubl, dh["despatch_id"]
