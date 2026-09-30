"""The second retailer's leg: Torvale's orders under Torvale's profile, read by the supplier into the same model, and the same order under two models."""
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "ubl"))
from halvorsen import generate  # noqa: E402
from instance import read_tree  # noqa: E402
from order import TORVALE, profile_of, projected, read_order, validate_ubl, write_order  # noqa: E402
from profiles import refusals, two_models  # noqa: E402
from schema import Schema  # noqa: E402
from shared import SUPPLIER_TRANSLATOR, record  # noqa: E402
from torvale import generate_torvale  # noqa: E402

CASES = list(generate_torvale(12, seed="halvorsen-2026:torvale"))   # the year the supplier's stack loads


def torvale_values(xml):
    return read_tree(xml, Schema.for_dm(TORVALE.ct)).get(*TORVALE.root).paths(TORVALE.root)


def test_the_supplier_reads_each_torvale_order_into_the_torvale_model():
    for h, values, xml in CASES:
        assert profile_of(xml) is TORVALE and refusals(xml, TORVALE.ct) == []
        assert "Torvale Markets order system" in xml
        ubl = write_order(xml)
        assert not validate_ubl(ubl), (h["order_id"], validate_ubl(ubl)[:3])
        back = read_order(ubl, TORVALE)
        assert back == projected(torvale_values(xml)), h["order_id"]
        supplier = record("Torvale Order", back, document_id=h["order_id"], buyer=h["buyer"], when=f"{h['issued']}T12:00:00",
                          source=(f"urn:torvale:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order received"), agent=SUPPLIER_TRANSLATOR)
        assert refusals(supplier, TORVALE.ct) == [] and "Halvorsen Foods document translator" in supplier
        assert write_order(supplier) == ubl


def test_the_same_order_under_two_models_names_what_each_refuses():
    kh, kv, kxml = next(iter(generate(1, seed="halvorsen-2026")))
    th, tv, txml = CASES[0]
    x = two_models(kxml, txml)
    torvale_reqs = {r["cluster"]: r["requires"] for r in x["models"][1]["requirements"]}
    assert "Torvale Order Requirements" in torvale_reqs["Torvale Order"]
    kestrel_under = {u["model"]: u["refused"] for u in x["orders"][0]["under"]}
    torvale_under = {u["model"]: u["refused"] for u in x["orders"][1]["under"]}
    assert kestrel_under["Order"] == [] and torvale_under["Torvale Order"] == []
    assert any("'DAP' is not in the list" in r for r in kestrel_under["Torvale Order"]) and any("requirement of 'Torvale Order'" in r for r in kestrel_under["Torvale Order"])
    assert any("'Pack specification' is not in the list" in r for r in torvale_under["Order"])
