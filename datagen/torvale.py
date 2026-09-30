"""
Torvale Markets' orders, generated on the template engine under Torvale's own order profile.

Torvale Markets is a second fictitious retailer. It orders from the same catalog, monthly rather than
weekly, under its own profile of the business documents library: the same components as the Order,
with the delivery terms narrowed to the one rule Torvale accepts (delivered duty paid), and two things
Torvale requires stated on every order, the pack specification version the order is placed under and
the delivery window in days. Those requirements are assertions in the model's schema, so an order that
lacks them is not a Torvale order. The orders are records of the Torvale Order model; the UBL 2.3 Order
written from one carries the requirements in UBL's own places (see ubl/order.py, TORVALE).

    from torvale import generate_torvale
    for h, values, xml in generate_torvale(12):
        ...
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import HALVORSEN, gs1_check, order_values, party  # noqa: E402
from shared import RETAILER2_SYSTEM as TORVALE_SYSTEM, cuid_generator, record  # noqa: E402

O = "Order Governed Record/Order/"
T = "Torvale Order Governed Record/Torvale Order/"
# Fictitious. The prefix 0000 is not a GS1 company prefix.
TORVALE = {
    "name": "Torvale Markets, Inc.", "gln": gs1_check("000000400001"), "endpoint": gs1_check("000000400001"), "company_id": "IL-63-4471820",
    "address": {"line1": "750 North State Street", "city": "Rockford", "state": "IL", "zip": "61103"},
    "contact": {"name": "Category buying", "department": "Merchandising", "phone": "+1 815 555 0177", "email": "buying@torvalemarkets.example"},
    "dc": {"gln": gs1_check("000000400002"), "name": "Torvale Markets DC 1 (Rockford)", "line1": "4400 Kishwaukee Street", "city": "Rockford", "state": "IL", "zip": "61109"},
}
PACK_SPECIFICATION = "TV-PACK-2026-01"
WINDOW_DAYS = 2


def torvale_values(n: int, rng: random.Random, year: int = 2026) -> tuple[dict, dict]:
    """One Torvale order: the Order's values remapped to Torvale's profile, with Torvale's parties, terms and requirements."""
    base, h = order_values(n, rng, year)
    order_id = f"TV-PO-{year}-{n:06d}"
    v = {}
    for k, val in base.items():
        rel = k[len(O):]
        if rel.startswith("Buyer Customer Party/") or rel.startswith("Delivery/Delivery Location/") or rel.startswith("Delivery Terms/"):
            continue
        if rel.startswith("Payment Means/"):   # Torvale's profile composes the revised Payment Means Instruction cluster
            rel = "Payment Means Instruction/" + rel[len("Payment Means/"):]
        v[T + rel] = val
    v[T + "Order Document/Order ID"] = order_id
    v[T + "Order Document/Customization ID"] = "https://axius-sdc.com/library/business/torvale-order-governed-record"
    v[T + "Order Document/Profile ID"] = "urn:torvale:profile:order:1"
    v[T + "Order Document/Customer Reference"] = f"TV-BUY-{rng.randint(100, 999)}"
    v[T + "Order Document/Accounting Cost"] = "Grocery 2210"
    v[T + "Order Document/Note"] = "Deliver duty paid to DC 1 within the two-day window; pallets to the pack specification named on this order."
    v[T + "Contract/Contract ID"] = "TV-HF-SA-2026-01"
    v[T + "Contract/Contract Issue Date"] = "2026-01-12"
    v[T + "Buyer Customer Party/Customer Party/Supplier Assigned Account ID"] = "HF-CUST-00522"
    v.update(party(T + "Buyer Customer Party/Customer Party/", TORVALE, "buyer"))
    dc = TORVALE["dc"]
    start = date.fromisoformat(base[O + "Delivery/Requested Delivery Period/Date Range/Date Range Start"])
    v.update({
        T + "Delivery/Delivery ID": f"{order_id}-D1",
        T + "Delivery/Latest Delivery Date": (start + timedelta(days=WINDOW_DAYS - 1)).isoformat(),
        T + "Delivery/Delivery Location/Delivery Location ID": dc["gln"], T + "Delivery/Delivery Location/Delivery Location Name": dc["name"],
        T + "Delivery/Delivery Location/US Address/Address (Line 1)": dc["line1"], T + "Delivery/Delivery Location/US Address/City Name": dc["city"],
        T + "Delivery/Delivery Location/US Address/US State Code": dc["state"], T + "Delivery/Delivery Location/US Address/US ZIP Code": dc["zip"],
        T + "Delivery/Delivery Location/US Address/Country Code ISO 3166": "US",
        T + "Delivery/Requested Delivery Period/Date Range/Date Range Start": start.isoformat(),
        T + "Delivery/Requested Delivery Period/Date Range/Date Range End": (start + timedelta(days=WINDOW_DAYS - 1)).isoformat(),
        T + "Torvale Delivery Terms/Torvale Delivery Terms Code": "DDP",
        T + "Torvale Delivery Terms/Delivery Special Terms": "Delivered duty paid to DC 1; appointment required 48 hours ahead.",
        T + "Torvale Order Requirements/Torvale Pack Specification Version": PACK_SPECIFICATION,
        T + "Torvale Order Requirements/Torvale Delivery Window Days": Quantity(str(WINDOW_DAYS), "days"),
    })
    return v, {"order_id": order_id, "issued": h["issued"], "buyer": TORVALE["name"], "seller": HALVORSEN["name"]}


def generate_torvale(orders: int = 12, seed: str = "torvale-2026", year: int = 2026):
    """Yield (header, values, instance xml) for each Torvale order, the same sequence on every run."""
    rng = random.Random(seed)
    for n in range(1, orders + 1):
        values, h = torvale_values(n, rng, year)
        when = f"{h['issued']}T{rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}:00"
        xml = record("Torvale Order", values, document_id=h["order_id"], buyer=h["buyer"], when=when,
                     source=(f"urn:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order written from this record, the buyer's projection"),
                     agent=TORVALE_SYSTEM, instance_id=cuid_generator(rng), rng=rng)
        yield h, values, xml
