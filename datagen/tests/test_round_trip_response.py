"""The response leg of the exchange: the supplier's record writes a conformant UBL 2.3 OrderResponse, the retailer reads it into the same record, and both validate."""
import os
import random
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from halvorsen import generate  # noqa: E402
from halvorsen_responses import respond  # noqa: E402
from instance import read_tree  # noqa: E402
from order_response import RESPONSE_CT, RR, projected_response, read_order_response, validate_ubl_response, write_order_response  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import RETAILER_TRANSLATOR, record  # noqa: E402

rng = random.Random("round-trip:responses")
CASES = [(h, v, x, *respond(h, v, rng)) for h, v, x in generate(24, seed="round-trip")]


@pytest.fixture(scope="module")
def sdc_schema():
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{RESPONSE_CT}.xsd"),
                              uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def response_values(xml):
    return read_tree(xml, Schema.for_dm(RESPONSE_CT)).get(*RR).paths(RR)


def test_every_kind_of_answer_occurs_and_the_responses_validate(sdc_schema):
    kinds = {rh["kind"] for _, _, _, rh, _, _ in CASES}
    assert kinds == {"accepted", "changed", "rejected", "substituted"}, kinds
    for _, _, _, rh, values, xml in CASES:
        errors = [str(e) for e in sdc_schema.iter_errors(xml)]
        assert not errors, (rh["response_id"], errors[:3])
        assert "Halvorsen Foods order system" in xml


def test_the_retailer_reads_the_response_into_the_same_record(sdc_schema):
    for _, _, _, rh, values, xml in CASES:
        ubl = write_order_response(xml)
        assert not validate_ubl_response(ubl), (rh["response_id"], validate_ubl_response(ubl)[:3])
        back = read_order_response(ubl)
        assert back == projected_response(response_values(xml)), rh["response_id"]
        retailer = record("Order Response", back, document_id=rh["response_id"], buyer=rh["seller"], when=f"{rh['issued']}T12:00:00",
                          source=(f"urn:halvorsen:response:{rh['response_id']}:ubl", f"{rh['response_id']}.xml", "The UBL 2.3 OrderResponse received"), agent=RETAILER_TRANSLATOR)
        errors = [str(e) for e in sdc_schema.iter_errors(retailer)]
        assert not errors, (rh["response_id"], errors[:3])
        assert "Kestrel Mercantile document translator" in retailer
        assert write_order_response(retailer) == ubl, rh["response_id"]
