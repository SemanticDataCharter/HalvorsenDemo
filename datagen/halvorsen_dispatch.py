"""
Halvorsen's dispatch advices for Kestrel's orders, generated on the template engine.

Each order the seller answered is shipped the day before the requested delivery window opens, from
the Duluth warehouse to the Joliet distribution center by the carrier. The dispatch fulfils the
response: the confirmed quantity of every line is delivered, a rejected line is canceled, a
substituted line carries the substitute, and now and then a line is short-shipped with the balance on
back order. The cases are stacked on pallets, up to six, each a transport handling unit with its
serial shipping container code, the pallet's own identifier with the period it is valid for, the
packages on it packed against the retailer's pack specification, and the temperature range for
chilled goods.

Two facts are the fined notice's: a pallet identifier valid on the day the advice is sent and lapsed
by the day the goods are received, and a unit packed to a pack specification version the retailer
had already replaced. Both are in the record, both travel in the UBL projection, and the receipt
advice will hold them against the receipt date.

    from halvorsen_dispatch import generate_dispatches
    for h, order_values, order_xml, rh, response_values, response_xml, dh, dispatch_values, dispatch_xml in generate_dispatches(52):
        ...
"""
from __future__ import annotations

import math
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import CATALOG, HALVORSEN, KESTREL, gs1_check, party  # noqa: E402
from shared import SUPPLIER_WAREHOUSE as WAREHOUSE_SYSTEM, cuid_generator, record  # noqa: E402

O = "Order Governed Record/Order/"
R = "Order Response Governed Record/Order Response/"
D = "Despatch Advice Governed Record/Despatch Advice/"
# Fictitious. The prefix 0000 is not a GS1 company prefix.
CARRIER = {
    "name": "Northline Freight, LLC", "gln": gs1_check("000000300001"), "endpoint": gs1_check("000000300001"), "company_id": "MN-52-8810447",
    "address": {"line1": "2100 Port Terminal Drive", "city": "Duluth", "state": "MN", "zip": "55802"},
    "contact": {"name": "Dispatch", "department": "Operations", "phone": "+1 218 555 0190", "email": "dispatch@northlinefreight.example"},
}
CHILLED = {"HF-3001", "HF-4001"}
CASES_PER_LAYER = 8
CASE_HEIGHT_CM = 25
PALLET_HEIGHT_CM = 15
PALLET_TARE_KG = Decimal("25.0")
PALLET_VOLUME_L = Decimal("150.000")
#: The retailer's pack specification versions and the day each took effect.
PACK_SPECIFICATIONS = [("KM-PACK-2026-01", date(2026, 1, 1)), ("KM-PACK-2026-02", date(2026, 7, 1))]
POOL_SCHEME = "Pool operator number"


def _sscc(rng: random.Random) -> str:
    """A serial shipping container code: extension digit, the fictitious prefix, a serial, the check digit."""
    return gs1_check("0" + "0000001" + f"{rng.randint(0, 999999999):09d}")


def pack_specification_in_force(on: date) -> tuple[str, str | None]:
    """The version in force on a date, and the one it replaced when there is one."""
    current = [v for v, since in PACK_SPECIFICATIONS if since <= on]
    return current[-1], (current[-2] if len(current) > 1 else None)


def _response_lines(rv: dict) -> list[int]:
    return [n for n in range(1, 11) if (R + f"Order Response Lines/Order Response Line {n}/Order Response Line/Line Response") in rv]


def dispatch(h: dict, order: dict, rh: dict, rv: dict, rng: random.Random) -> tuple[dict, dict, str]:
    """Halvorsen's dispatch advice for one answered order: (header, values, instance xml)."""
    order_id = h["order_id"]
    seq = int(order_id.rsplit("-", 1)[1])
    window_start = date.fromisoformat(order[O + "Delivery/Requested Delivery Period/Date Range/Date Range Start"])
    issued = window_start - timedelta(days=1)
    dispatch_id = f"HF-DA-{issued.year}-{seq:06d}"
    catalog = {c[0]: c for c in CATALOG}
    kind = "short" if seq % 12 == 7 else "canceled-line" if rh["kind"] == "rejected" else "substituted" if rh["kind"] == "substituted" else "complete"
    pallet_lapses = seq % 12 == 5
    version, previous = pack_specification_in_force(issued)
    pack_stale = seq % 12 == 11 and previous is not None
    v = {
        D + "Despatch Advice Document/Customization ID": "https://axius-sdc.com/library/business/despatch-advice-governed-record",
        D + "Despatch Advice Document/Profile ID": order.get(O + "Order Document/Profile ID"),
        D + "Despatch Advice Document/Despatch Advice ID": dispatch_id,
        D + "Despatch Advice Document/Copy Indicator": False,
        D + "Despatch Advice Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        D + "Despatch Advice Document/Issue Date": issued.isoformat(),
        D + "Despatch Advice Document/Issue Time": f"{rng.randint(6, 15):02d}:{rng.randint(0, 59):02d}:00",
        D + "Despatch Advice Document/Document Status": "Original",
        D + "Despatch Advice Document/Despatch Advice Type": "Delivery",
        D + "Despatch Advice Document/Note": "Shipped from Duluth for delivery in the requested window; the appointment is booked with the distribution center.",
        D + "Order Reference/Order ID": order_id,
        D + "Order Reference/Sales Order ID": rv.get(R + "Order Reference/Sales Order ID"),
        D + "Order Reference/Document UUID": order.get(O + "Order Document/Document UUID"),
        D + "Order Reference/Issue Date": order.get(O + "Order Document/Issue Date"),
        D + "Order Reference/Order Type": order.get(O + "Order Document/Order Type"),
        D + "Additional Document Reference/Document Reference/Document Reference ID": rh["response_id"],
        D + "Additional Document Reference/Document Reference/Document Reference Issue Date": rh["issued"],
        D + "Additional Document Reference/Document Reference/Document Type": "Other document",   # the document-type list predates the response; a revision will name it
        D + "Additional Document Reference/Document Reference/Document Description": "The order response this dispatch fulfils.",
        D + "Shipment/Shipment ID": f"HF-SH-{issued.year}-{seq:06d}",
        D + "Shipment/Consignment/Consignment ID": f"HF-CN-{issued.year}-{seq:06d}",
        D + "Shipment/Consignment/Carrier Assigned ID": f"NLF{rng.randint(10000000, 99999999)}",
        D + "Shipment/Delivery/Delivery ID": order.get(O + "Delivery/Delivery ID"),
        D + "Shipment/Delivery/Latest Delivery Date": order.get(O + "Delivery/Latest Delivery Date"),
        D + "Shipment/Delivery/Requested Delivery Period/Date Range/Date Range Start": order.get(O + "Delivery/Requested Delivery Period/Date Range/Date Range Start"),
        D + "Shipment/Delivery/Requested Delivery Period/Date Range/Date Range End": order.get(O + "Delivery/Requested Delivery Period/Date Range/Date Range End"),
    }
    v.update(party(D + "Shipment/Consignment/Carrier Party/", CARRIER, "carrier"))
    # the parties and the delivery location, as the order named them
    for side, src in (("Despatch Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"), ("Seller Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"),
                      ("Delivery Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/"), ("Buyer Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/"),
                      ("Shipment/Delivery/Delivery Location/", "Delivery/Delivery Location/")):
        for k, val in order.items():
            if k.startswith(O + src):
                v[D + side + k[len(O + src):]] = val
    # the lines, as answered
    short_line = None
    cases_by_line: list[tuple[int, str, int]] = []   # (line, item number, cases shipped)
    net = Decimal("0"); volume = Decimal("0")
    lines = _response_lines(rv)
    if kind == "short":
        short_line = rng.choice([n for n in lines if rv[R + f"Order Response Lines/Order Response Line {n}/Order Response Line/Line Response"] in ("Accepted", "Accepted with changes")] or lines)
    for n in lines:
        RL = R + f"Order Response Lines/Order Response Line {n}/Order Response Line/"
        L = D + f"Despatch Lines/Despatch Line {n}/Despatch Line/"
        answer = rv[RL + "Line Response"]
        item_path = RL + ("Seller Substituted Line Item/Line Item/Item/" if answer == "Substituted" else "Line Item/Item/")
        item_no = rv[item_path + "Seller's Item Identification/Item Identification/Item Identification Value"]
        confirmed = int(rv[RL + "Line Item/Ordered Quantity"].magnitude)
        ordered = int(order[O + f"Order Lines/Order Line {n}/Order Line/Line Item/Ordered Quantity"].magnitude)
        shipped = confirmed
        v.update({
            L + "Line ID": str(n),
            L + "Line Status": "Cancelled" if answer == "Rejected" else "Revised" if answer in ("Accepted with changes", "Substituted") or n == short_line else "No status",
            L + "Order Line Reference/Line ID": str(n),
            L + "Order Line Reference/Sales Order Line ID": rv.get(RL + "Order Line Reference/Sales Order Line ID"),
            L + "Order Line Reference/Line Status": rv.get(RL + "Order Line Reference/Line Status"),
            L + "Item/Item Name": rv[item_path + "Item Name"],
            L + "Item/Seller's Item Identification/Item Identification/Item Identification Scheme": "Seller's item number",
            L + "Item/Seller's Item Identification/Item Identification/Item Identification Value": item_no,
            L + "Item/Standard Item Identification/Item Identification/Item Identification Scheme": "Global Trade Item Number (GS1)",
            L + "Item/Standard Item Identification/Item Identification/Item Identification Value": rv[item_path + "Standard Item Identification/Item Identification/Item Identification Value"],
            L + "Item/Pack Quantity": Quantity(str(catalog[item_no][5]), "items"),
        })
        if answer == "Rejected":
            shipped = 0
            v[L + "Outstanding Quantity"] = Quantity(str(ordered), "CS")
            v[L + "Outstanding Reason"] = "Rejected on the order response; nothing supplied on this line."
        elif n == short_line:
            shipped = max(1, confirmed - 6)
            v[L + "Backorder Quantity"] = Quantity(str(confirmed - shipped), "CS")
            v[L + "Backorder Reason"] = "Short stock at dispatch; the balance follows on the next run."
        elif answer == "Substituted":
            v[L + "Note"] = rv.get(RL + "Seller Substituted Line Item/Line Item/Note")
        if confirmed and shipped < ordered and answer != "Rejected" and n != short_line:
            v[L + "Outstanding Quantity"] = Quantity(str(ordered - confirmed), "CS")
            v[L + "Outstanding Reason"] = "Quantity confirmed on the order response below the quantity ordered."
        v[L + "Delivered Quantity"] = Quantity(str(shipped), "CS")
        if shipped:
            cases_by_line.append((n, item_no, shipped))
            net += Decimal(catalog[item_no][6]) * shipped; volume += Decimal(catalog[item_no][7]) * shipped
    # the pallets: the cases in line order, as many pallets as the load needs, up to six
    total = sum(c for _, _, c in cases_by_line)
    pallets = max(1, min(6, math.ceil(total / (CASES_PER_LAYER * 6)))) if total else 0
    per_pallet = math.ceil(total / pallets) if pallets else 0
    remaining = [[n, item_no, c] for n, item_no, c in cases_by_line]
    for i in range(1, pallets + 1):
        U = D + f"Shipment/Transport Handling Units/Transport Handling Unit {i}/Transport Handling Unit/"
        on_pallet = 0; weight = PALLET_TARE_KG; chilled = False
        while remaining and on_pallet < per_pallet:
            n, item_no, c = remaining[0]
            take = min(c, per_pallet - on_pallet)
            on_pallet += take; weight += Decimal(catalog[item_no][6]) * take; chilled = chilled or item_no in CHILLED
            remaining[0][2] -= take
            if remaining[0][2] == 0:
                remaining.pop(0)
        layers = math.ceil(on_pallet / CASES_PER_LAYER)
        registered = issued - timedelta(days=rng.randint(60, 700))
        lapses = pallet_lapses and i == 1
        v.update({
            U + "Transport Handling Unit ID": _sscc(rng),
            U + "Transport Handling Unit Type": "Pallet",
            U + "Pallet Identification/Pallet ID": f"PL-{rng.randint(100000, 999999)}",
            U + "Pallet Identification/Pallet ID Scheme": POOL_SCHEME,
            U + "Pallet Identification/Date Range/Date Range Start": registered.isoformat(),
            U + "Pallet Identification/Date Range/Date Range End": (issued if lapses else registered + timedelta(days=730)).isoformat(),
            U + "Package/Packaging Type": "Case",
            U + "Package/Package Quantity": Quantity(str(on_pallet), "items"),
            U + "Package/Pack Specification/Pack Specification Version": previous if pack_stale else version,
            U + "Package/Pack Specification/Cases per Layer": Quantity(str(CASES_PER_LAYER), "items"),
            U + "Package/Pack Specification/Layers per Pallet": Quantity(str(layers), "items"),
            U + "Package/Pack Specification/Pallet Height": Quantity(str(PALLET_HEIGHT_CM + layers * CASE_HEIGHT_CM), "cm"),
            U + "Package/Pack Specification/Weight": Quantity(f"{weight:.1f}", "kg"),
            U + "Total Package Quantity": Quantity(str(on_pallet), "items"),
            U + "Shipping Marks": f"{order_id} pallet {i} of {pallets} for {KESTREL['dc']['name']}",
            U + "Handling Instructions": "Keep chilled; do not double stack." if chilled else "Do not double stack.",
        })
        if chilled:
            v[U + "Minimum Temperature"] = Quantity("2.0", "°C")
            v[U + "Maximum Temperature"] = Quantity("6.0", "°C")
    v.update({
        D + "Despatch Advice Document/Line Count": Quantity(str(len(lines)), "items"),
        D + "Shipment/Total Goods Item Quantity": Quantity(str(len(cases_by_line)), "items"),
        D + "Shipment/Total Transport Handling Unit Quantity": Quantity(str(pallets), "items"),
        D + "Shipment/Net Weight": Quantity(f"{net:.2f}", "kg"),
        D + "Shipment/Gross Weight": Quantity(f"{net + PALLET_TARE_KG * pallets:.2f}", "kg"),
        D + "Shipment/Net Volume": Quantity(f"{volume:.3f}", "L"),
        D + "Shipment/Gross Volume": Quantity(f"{volume + PALLET_VOLUME_L * pallets:.3f}", "L"),
        D + "Shipment/Handling Instructions": "Chilled pallets to the cold dock first." if any(item_no in CHILLED for _, item_no, _ in cases_by_line) else None,
    })
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{issued.isoformat()}T{rng.randint(6, 15):02d}:{rng.randint(0, 59):02d}:00"
    xml = record("Despatch Advice", v, document_id=dispatch_id, buyer=HALVORSEN["name"], when=when,
                 source=(f"urn:halvorsen:response:{rh['response_id']}", f"{rh['response_id']}.xml", "The Order Response this dispatch fulfils"),
                 agent=WAREHOUSE_SYSTEM, current_state="OrderInTransit", instance_id=cuid_generator(rng), rng=rng)
    dh = {"dispatch_id": dispatch_id, "order_id": order_id, "response_id": rh["response_id"], "issued": issued.isoformat(), "kind": kind,
          "pallets": pallets, "pallet_lapses": pallet_lapses and pallets > 0, "pack_version": previous if pack_stale else version, "pack_stale": pack_stale,
          "seller": HALVORSEN["name"], "buyer": KESTREL["name"]}
    return dh, v, xml


def generate_dispatches(orders: int, seed: str = "halvorsen-2026"):
    """Yield (order header, values, xml, response header, values, xml, dispatch header, values, xml) for each order."""
    from halvorsen_responses import generate_responses
    rng = random.Random(seed + ":dispatches")
    for h, values, xml, rh, rv, rxml in generate_responses(orders, seed=seed):
        dh, dv, dxml = dispatch(h, values, rh, rv, rng)
        yield h, values, xml, rh, rv, rxml, dh, dv, dxml
