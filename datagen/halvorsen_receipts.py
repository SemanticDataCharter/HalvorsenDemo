"""
Kestrel's receipt advices for Halvorsen's shipments, generated on the template engine.

The retailer receives each shipment on the day the delivery window opens, the day after it was
dispatched. The receiving system counts every line against the dispatch advice, and checks every
handling unit on the receipt date against the two rules the fined notice turned on: was the pallet
identifier within its validity period that day, and was the unit packed to the pack specification
version in force that day. A unit that fails either is accepted with an exception that says what was
found and against which rule; the record's state is then OrderProblem, the transition the settlement
receipt will answer. Now and then a line arrives short or with a damaged case, or the truck arrives
late, so the receipt has something to say beyond the two rules.

    from halvorsen_receipts import generate_receipts
    for *_, kh, receipt_values, receipt_xml in generate_receipts(52):
        ...
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import KESTREL  # noqa: E402
from halvorsen_dispatch import pack_specification_in_force  # noqa: E402
from shared import RETAILER_RECEIVING as RECEIVING_SYSTEM, cuid_generator, record  # noqa: E402

O = "Order Governed Record/Order/"
D = "Despatch Advice Governed Record/Despatch Advice/"
K = "Receipt Advice Governed Record/Receipt Advice/"


def _units(dv: dict) -> list[int]:
    return [n for n in range(1, 7) if (D + f"Shipment/Transport Handling Units/Transport Handling Unit {n}/Transport Handling Unit/Transport Handling Unit ID") in dv]


def _lines(dv: dict) -> list[int]:
    return [n for n in range(1, 11) if (D + f"Despatch Lines/Despatch Line {n}/Despatch Line/Line ID") in dv]


def receive(h: dict, order: dict, dh: dict, dv: dict, rng: random.Random) -> tuple[dict, dict, str]:
    """Kestrel's receipt advice for one dispatch: (header, values, instance xml)."""
    order_id = h["order_id"]
    seq = int(order_id.rsplit("-", 1)[1])
    received = date.fromisoformat(dh["issued"]) + timedelta(days=1)
    received_time = f"{rng.randint(6, 11):02d}:{rng.randint(0, 59):02d}:00"
    receipt_id = f"KM-RA-{received.year}-{seq:06d}"
    kind = "short" if seq % 12 == 2 else "rejected" if seq % 12 == 8 else "late" if seq % 12 == 4 else "complete"
    in_force, _ = pack_specification_in_force(received)
    v = {
        K + "Receipt Advice Document/Customization ID": "https://axius-sdc.com/library/business/receipt-advice-governed-record",
        K + "Receipt Advice Document/Profile ID": order.get(O + "Order Document/Profile ID"),
        K + "Receipt Advice Document/Receipt Advice ID": receipt_id,
        K + "Receipt Advice Document/Copy Indicator": False,
        K + "Receipt Advice Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        K + "Receipt Advice Document/Issue Date": received.isoformat(),
        K + "Receipt Advice Document/Issue Time": f"{rng.randint(12, 17):02d}:{rng.randint(0, 59):02d}:00",
        K + "Receipt Advice Document/Document Status": "Original",
        K + "Receipt Advice Document/Receipt Advice Type": "Delivery",
        K + "Receipt Advice Document/Note": "Received at DC 2 (Joliet) and checked against the pack specification in force and the pallet identifiers' validity on the day of receipt.",
        K + "Despatch Document Reference/Document Reference/Document Reference ID": dh["dispatch_id"],
        K + "Despatch Document Reference/Document Reference/Document Reference Issue Date": dh["issued"],
        K + "Despatch Document Reference/Document Reference/Document Type": "Despatch advice",
        K + "Despatch Document Reference/Document Reference/Document Description": "The dispatch advice this receipt answers.",
        K + "Receipt Shipment/Actual Delivery Date": received.isoformat(),
        K + "Receipt Shipment/Actual Delivery Time": received_time,
    }
    # the order reference, the shipment identifier, the consignment and the delivery, as the dispatch advice stated them
    for prefix in ("Order Reference/", "Shipment/Shipment ID", "Shipment/Consignment/", "Shipment/Delivery/"):
        for key, val in dv.items():
            if key.startswith(D + prefix):
                v[K + key[len(D):].replace("Shipment/", "Receipt Shipment/", 1)] = val
    # the parties, as the order named them
    for side, src in (("Delivery Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/"), ("Buyer Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/"),
                      ("Despatch Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"), ("Seller Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/")):
        for key, val in order.items():
            if key.startswith(O + src):
                v[K + side + key[len(O + src):]] = val
    # the handling units, each checked on the receipt date
    exceptions = 0; pallet_lapsed = False; pack_stale = False
    for i in _units(dv):
        DU = D + f"Shipment/Transport Handling Units/Transport Handling Unit {i}/Transport Handling Unit/"
        U = K + f"Receipt Shipment/Received Handling Units/Received Handling Unit {i}/Received Handling Unit/"
        end = date.fromisoformat(dv[DU + "Pallet Identification/Date Range/Date Range End"])
        valid = received <= end
        packed_to = dv[DU + "Package/Pack Specification/Pack Specification Version"]
        compliant = packed_to == in_force
        problems = []
        if not valid:
            problems.append(f"pallet identifier {dv[DU + 'Pallet Identification/Pallet ID']} valid to {end.isoformat()}, received {received.isoformat()}")
        if not compliant:
            problems.append(f"packed to {packed_to}; {in_force} in force on {received.isoformat()}")
        v.update({
            U + "Transport Handling Unit ID": dv[DU + "Transport Handling Unit ID"],
            U + "Received Date": received.isoformat(),
            U + "Received Time": received_time,
            U + "Pallet ID Valid on Receipt": valid,
            U + "Pack Specification Version": packed_to,
            U + "Pack Specification in Force": in_force,
            U + "Pack Specification Compliant": compliant,
            U + "Receiving Condition": "Accepted" if not problems else "Accepted with exception",
            U + "Exception Description": None if not problems else "Accepted with exception: " + "; ".join(problems) + ".",
        })
        for key, val in dv.items():
            if key.startswith(DU + "Pallet Identification/"):
                v[U + key[len(DU):]] = val
        exceptions += bool(problems); pallet_lapsed = pallet_lapsed or not valid; pack_stale = pack_stale or not compliant
    # the lines, counted against the dispatch
    lines = _lines(dv)
    short_line = rng.choice(lines) if kind == "short" and lines else None
    rejected_line = rng.choice(lines) if kind == "rejected" and lines else None
    for n in lines:
        DL = D + f"Despatch Lines/Despatch Line {n}/Despatch Line/"
        L = K + f"Receipt Lines/Receipt Line {n}/Receipt Line/"
        delivered = int(dv[DL + "Delivered Quantity"].magnitude)
        received_cases = delivered
        v.update({
            L + "Line ID": str(n),
            L + "Received Date": received.isoformat(),
            L + "Quantity Discrepancy": "None",
            L + "Timing Complaint": "Late" if kind == "late" else "On time",
            L + "Despatch Line Reference/Line ID": str(n),
            L + "Despatch Line Reference/Line Status": dv.get(DL + "Line Status"),
            L + "Despatch Line Reference/Document Reference/Document Reference ID": dh["dispatch_id"],
            L + "Despatch Line Reference/Document Reference/Document Type": "Despatch advice",
        })
        if kind == "late":
            v[L + "Timing Complaint Description"] = "Arrived after the appointment window; unloaded in the next open slot."
        for key, val in dv.items():
            if key.startswith(DL + "Order Line Reference/") or key.startswith(DL + "Item/"):
                v[L + key[len(DL):]] = val
        if delivered == 0:
            v[L + "Note"] = "Nothing supplied on this line, as the dispatch advice states."
        elif n == short_line and delivered > 2:
            received_cases = delivered - 2
            v.update({L + "Short Quantity": Quantity("2", "CS"), L + "Shortage Action": "Back order the balance", L + "Quantity Discrepancy": "Short",
                      L + "Note": "Two cases fewer than the dispatch advice states; counted twice at the dock."})
        elif n == rejected_line and delivered > 1:
            received_cases = delivered - 1
            v.update({L + "Rejected Quantity": Quantity("1", "CS"), L + "Reject Reason": "Damaged", L + "Reject Reason Description": "One case crushed on the bottom layer; contents unsaleable.",
                      L + "Reject Action": "Return to sender", L + "Quantity Discrepancy": "Damaged"})
        v[L + "Received Quantity"] = Quantity(str(received_cases), "CS")
    v[K + "Receipt Advice Document/Line Count"] = Quantity(str(len(lines)), "items")
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{received.isoformat()}T{rng.randint(12, 17):02d}:{rng.randint(0, 59):02d}:00"
    xml = record("Receipt Advice", v, document_id=receipt_id, buyer=KESTREL["name"], when=when,
                 source=(f"urn:halvorsen:dispatch:{dh['dispatch_id']}", f"{dh['dispatch_id']}.xml", "The Despatch Advice this receipt answers"),
                 agent=RECEIVING_SYSTEM, current_state="OrderProblem" if exceptions else "OrderDelivered", instance_id=cuid_generator(rng), rng=rng)
    kh = {"receipt_id": receipt_id, "dispatch_id": dh["dispatch_id"], "order_id": order_id, "received": received.isoformat(), "kind": kind, "units": len(_units(dv)),
          "exceptions": exceptions, "pallet_lapsed": pallet_lapsed, "pack_stale": pack_stale, "buyer": KESTREL["name"], "seller": dh["seller"]}
    return kh, v, xml


def generate_receipts(orders: int, seed: str = "halvorsen-2026"):
    """Yield the order, response and dispatch triples of generate_dispatches, then (receipt header, values, xml), for each order."""
    from halvorsen_dispatch import generate_dispatches
    rng = random.Random(seed + ":receipts")
    for h, values, xml, rh, rv, rxml, dh, dv, dxml in generate_dispatches(orders, seed=seed):
        kh, kv, kxml = receive(h, values, dh, dv, rng)
        yield h, values, xml, rh, rv, rxml, dh, dv, dxml, kh, kv, kxml
