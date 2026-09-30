"""
The same order under two retailers' models: what each requires, where they differ, and what each refuses.

    from ubl.profiles import two_models
    exhibit = two_models(kestrel_instance_xml, torvale_instance_xml)

Each order is written as the UBL 2.3 Order its own profile writes, then read into both profiles' models and
validated under each model's schema. What a model refuses is named value by value: a value outside a list, a
requirement the record does not meet, a kind of document the list does not know. The result is data for a page,
not a verdict: both models compose the same components, and each says what it needs.
"""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "datagen"))
from order import KESTREL, TORVALE, Profile, read_order, write_order  # noqa: E402
from schema import DMLIB, Schema  # noqa: E402
from shared import TRANSLATOR, TRANSLATOR_ID, record  # noqa: E402

TITLES = {KESTREL.ct: "Order", TORVALE.ct: "Torvale Order"}
RETAILERS = {KESTREL.ct: "Kestrel Mercantile", TORVALE.ct: "Torvale Markets"}


@lru_cache(maxsize=None)
def schema_for(ct: str):
    from sdcvalidator import build_xsd11_schema
    return build_xsd11_schema(os.path.join(DMLIB, f"dm-{ct}.xsd"), uri_mapper={"https://semanticdatacharter.com/ns/sdc4/sdc4.xsd": os.path.abspath(os.path.join(DMLIB, "sdc4.xsd"))}, validation="lax")


def requirements_of(profile: Profile) -> list[dict]:
    """What the profile's schema requires, read from its assertions: the cluster, and the members it must hold."""
    xsd = open(os.path.join(DMLIB, f"dm-{profile.ct}.xsd"), encoding="utf-8").read()
    s = Schema.for_dm(profile.ct)
    out = []
    for m in re.finditer(r'<xsd:complexType name="mc-([a-z0-9]{24})"(.*?)</xsd:complexType>', xsd, re.S):
        cluster, body = m.group(1), m.group(2)
        required = re.findall(r'<xsd:assert test="exists\(ms-([a-z0-9]{24})\)', body)
        if required:
            out.append({"cluster": s.label.get(cluster, cluster), "requires": [s.label.get(ct, ct) for ct in required]})
    return out


def _named(error: str) -> str:
    """A validation error as a reader would say it: the value refused and the list it failed, or the cluster whose requirement failed."""
    m = re.search(r"failed validating '([^']*)' with XsdEnumerationFacets\((\[[^\]]*\])\)", error)
    if m:
        return f"{m.group(1)!r} is not in the list {m.group(2)}"
    m = re.search(r"failed validating (\S+) with XsdMaxInclusiveFacet\(value=(\S+),", error)
    if m:
        return f"{m.group(1)} exceeds the maximum {m.group(2)}"
    m = re.search(r"failed validating (\S+) with XsdMinInclusiveFacet\(value=(\S+),", error)
    if m:
        return f"{m.group(1)} is below the minimum {m.group(2)}"
    m = re.search(r"XsdPatternFacets\(\[(.*?)\]\)", error)
    if m:
        return f"the value does not match the pattern {m.group(1)}"
    m = re.search(r"ms-([a-z0-9]{24})' at 0x[0-9a-f]+> with XsdAssert", error)
    if m:
        return f"a requirement of the cluster {m.group(1)} is not met"
    return error.split("\n")[0][:160]


def refusals(instance_xml: str, ct: str) -> list[str]:
    s = Schema.for_dm(ct)
    out = []
    for e in schema_for(ct).iter_errors(instance_xml):
        text = str(e)
        m = re.search(r"ms-([a-z0-9]{24})' at 0x[0-9a-f]+> with XsdAssert", text)
        if m:
            out.append(f"a requirement of {s.label.get(m.group(1), m.group(1))!r} is not met")
        else:
            out.append(_named(text))
    return sorted(set(out))


def under(ubl_xml: str, profile: Profile, document_id: str, buyer: str, when: str) -> dict[str, Any]:
    """A UBL Order read into a profile's model and validated under it."""
    values = read_order(ubl_xml, profile)
    xml = record(TITLES[profile.ct], values, document_id=document_id, buyer=buyer, when=when,
                 source=(f"urn:order:{document_id}:ubl", f"{document_id}.xml", "The UBL 2.3 Order received"), agent=(TRANSLATOR_ID, TRANSLATOR, "Read"))
    return {"model": TITLES[profile.ct], "retailer": RETAILERS[profile.ct], "ct_id": profile.ct, "values": len(values), "refused": refusals(xml, profile.ct)}


def two_models(kestrel_xml: str, torvale_xml: str) -> dict[str, Any]:
    """Both orders, each as its own UBL document, each read into both models: what each model requires and what it refuses."""
    orders = []
    for xml, profile in ((kestrel_xml, KESTREL), (torvale_xml, TORVALE)):
        ubl = write_order(xml, profile)
        order_id = re.search(r"<label>Order ID</label>\s*<xdstring-value>([^<]*)<", xml).group(1)
        buyer = RETAILERS[profile.ct] + ", Inc."
        orders.append({"order_id": order_id, "written_by": RETAILERS[profile.ct], "own_model": TITLES[profile.ct],
                       "under": [under(ubl, p, order_id, buyer, "2026-06-01T12:00:00") for p in (KESTREL, TORVALE)]})
    return {"models": [{"model": TITLES[p.ct], "retailer": RETAILERS[p.ct], "ct_id": p.ct, "requirements": requirements_of(p)} for p in (KESTREL, TORVALE)], "orders": orders}
