"""
Halvorsen's responses to Kestrel's orders, generated on the template engine.

For each order the seller answers within a day. Most orders are accepted as ordered; some are
accepted with changes (one line's quantity cut to what is in stock, the totals restated); a few have
one line rejected or substituted by the next size of the same product. The response composes the
order's parties, delivery and payment terms as confirmed, references the order by its identifiers,
and answers line by line.

    from halvorsen import generate
    from halvorsen_responses import respond
    for h, order_values, order_xml in generate(52):
        rh, response_values, response_xml = respond(h, order_values, rng)
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import CATALOG, CURRENCY, HALVORSEN, KESTREL, gs1_check, money  # noqa: E402
from shared import SUPPLIER_SYSTEM as SELLER_SYSTEM, cuid_generator, record  # noqa: E402

O = "Order Governed Record/Order/"
R = "Order Response Governed Record/Order Response/"
SUBSTITUTE = {"HF-1001": "HF-1002", "HF-2001": "HF-2002", "HF-5001": "HF-5002"}   # the next product of the same family


def _line(values: dict, n: int) -> dict:
    """The values of order line n, keyed relative to its Line Item."""
    p = O + f"Order Lines/Order Line {n}/Order Line/Line Item/"
    return {k[len(p):]: v for k, v in values.items() if k.startswith(p)}


def respond(h: dict, order: dict, rng: random.Random) -> tuple[dict, dict, str]:
    """Halvorsen's response to one order: (header, values, instance xml)."""
    order_id = h["order_id"]
    issued = date.fromisoformat(h["issued"]) + timedelta(days=1)
    response_id = f"HF-OR-{issued.year}-{int(order_id.rsplit('-', 1)[1]):06d}"
    sales_order_id = f"HF-SO-{int(order_id.rsplit('-', 1)[1]):06d}"
    lines = [n for n in range(1, 11) if (O + f"Order Lines/Order Line {n}/Order Line/Line Item/Line ID") in order]
    # the kind of answer follows the order's number, so every kind appears in any run of a dozen orders or more
    seq = int(order_id.rsplit("-", 1)[1]) % 12
    kind = "changed" if seq in (3, 9) else "rejected" if seq == 6 else "substituted" if seq == 0 else "accepted"
    changed_line = rng.choice(lines) if kind != "accepted" else None
    v = {
        R + "Order Response Document/Customization ID": "https://axius-sdc.com/library/business/order-response-governed-record",
        R + "Order Response Document/Profile ID": order.get(O + "Order Document/Profile ID"),
        R + "Order Response Document/Order Response ID": response_id,
        R + "Order Response Document/Sales Order ID": sales_order_id,
        R + "Order Response Document/Copy Indicator": False,
        R + "Order Response Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        R + "Order Response Document/Issue Date": issued.isoformat(),
        R + "Order Response Document/Issue Time": f"{rng.randint(7, 16):02d}:{rng.randint(0, 59):02d}:00",
        R + "Order Response Document/Order Response Type": {"accepted": "Accepted", "changed": "Accepted with changes", "rejected": "Accepted with changes", "substituted": "Accepted with changes"}[kind],
        R + "Order Response Document/Note": "Chilled lines ship Tuesday and Thursday; the appointment is confirmed with the distribution center." if kind == "accepted" else "See the line answered below.",
        R + "Order Response Document/Document Currency": CURRENCY,
        R + "Order Response Document/Customer Reference": order.get(O + "Order Document/Customer Reference"),
        R + "Order Response Document/Line Count": Quantity(str(len(lines)), "items"),
        R + "Order Reference/Order ID": order_id,
        R + "Order Reference/Sales Order ID": sales_order_id,
        R + "Order Reference/Document UUID": order.get(O + "Order Document/Document UUID"),
        R + "Order Reference/Issue Date": order.get(O + "Order Document/Issue Date"),
        R + "Order Reference/Order Type": order.get(O + "Order Document/Order Type"),
        R + "Contract/Contract ID": order.get(O + "Contract/Contract ID"),
        R + "Delivery/Delivery ID": order.get(O + "Delivery/Delivery ID"),
        R + "Delivery/Latest Delivery Date": order.get(O + "Delivery/Latest Delivery Date"),
        R + "Delivery/Requested Delivery Period/Date Range/Date Range Start": order.get(O + "Delivery/Requested Delivery Period/Date Range/Date Range Start"),
        R + "Delivery/Requested Delivery Period/Date Range/Date Range End": order.get(O + "Delivery/Requested Delivery Period/Date Range/Date Range End"),
        R + "Delivery Terms/Delivery Terms Code": order.get(O + "Delivery Terms/Delivery Terms Code"),
        R + "Payment Means Instruction/Payment Means": order.get(O + "Payment Means/Payment Means"),
        R + "Payment Means Instruction/Payment Due Date": order.get(O + "Payment Means/Payment Due Date"),
        R + "Payment Terms/Payment Terms ID": order.get(O + "Payment Terms/Payment Terms ID"),
        R + "Payment Terms/Settlement Discount Percent": order.get(O + "Payment Terms/Settlement Discount Percent"),
        R + "Payment Terms/Payment Due Date": order.get(O + "Payment Terms/Payment Due Date"),
        R + "Transaction Conditions/Transaction Conditions ID": "HF-TERMS-2025",
        R + "Transaction Conditions/Transaction Conditions Description": "Halvorsen Foods standard terms of sale, 2025 edition, as referenced in the supply agreement.",
    }
    # the parties, as the order named them: the same components, the seller answering
    for side, src in (("Seller Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"), ("Buyer Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/")):
        for k, val in order.items():
            if k.startswith(O + src):
                v[R + side + k[len(O + src):]] = val
    # the delivery location, as the order asked
    for k, val in order.items():
        if k.startswith(O + "Delivery/Delivery Location/"):
            v[R + "Delivery/Delivery Location/" + k[len(O + "Delivery/Delivery Location/"):]] = val
    total = Decimal("0"); packages = 0; weight = Decimal("0"); volume = Decimal("0")
    catalog = {c[0]: c for c in CATALOG}
    for n in lines:
        li = _line(order, n)
        L = R + f"Order Response Lines/Order Response Line {n}/Order Response Line/"
        answer = "Accepted"
        item_no = li["Item/Seller's Item Identification/Item Identification/Item Identification Value"]
        cases = int(li["Ordered Quantity"].magnitude)
        price = Decimal(li["Price/Price Amount"].magnitude)
        if n == changed_line and kind == "changed":
            answer = "Accepted with changes"; cases = max(1, cases - rng.choice((6, 12)))
        elif n == changed_line and kind == "rejected":
            answer = "Rejected"; cases = 0
        elif n == changed_line and kind == "substituted" and item_no in SUBSTITUTE:
            answer = "Substituted"
        elif n == changed_line and kind == "substituted":
            answer = "Accepted with changes"; cases = max(1, cases - 6)
        v.update({
            L + "Order Line Reference/Line ID": str(n),
            L + "Order Line Reference/Sales Order Line ID": f"{sales_order_id}-{n}",
            L + "Order Line Reference/Line Status": "No status" if answer == "Accepted" else "Revised" if answer != "Rejected" else "Cancelled",
            L + "Line Response": answer,
            L + "Line Item/Line ID": str(n),
            L + "Line Item/Ordered Quantity": Quantity(str(cases), "CS"),
            L + "Line Item/Line Extension Amount": Quantity(money(price * cases), CURRENCY),
            L + "Line Item/Price/Price Amount": li["Price/Price Amount"],
            L + "Line Item/Price/Base Quantity": li["Price/Base Quantity"],
            L + "Line Item/Price/Price Type": li["Price/Price Type"],
            L + "Line Item/Item/Item Name": li["Item/Item Name"],
            L + "Line Item/Item/Seller's Item Identification/Item Identification/Item Identification Scheme": "Seller's item number",
            L + "Line Item/Item/Seller's Item Identification/Item Identification/Item Identification Value": item_no,
            L + "Line Item/Item/Standard Item Identification/Item Identification/Item Identification Scheme": "Global Trade Item Number (GS1)",
            L + "Line Item/Item/Standard Item Identification/Item Identification/Item Identification Value": li["Item/Standard Item Identification/Item Identification/Item Identification Value"],
        })
        if answer == "Rejected":
            v[L + "Line Item/Note"] = "Out of stock until the next production run; not back-ordered."
        if answer == "Substituted":
            sub = catalog[SUBSTITUTE[item_no]]
            S = L + "Seller Substituted Line Item/Line Item/"
            sub_price = Decimal(sub[4])
            v.update({
                S + "Line ID": str(n),
                S + "Note": f"{li['Item/Item Name']} is out of stock; substituted by {sub[1]} at its contract price.",
                S + "Ordered Quantity": Quantity(str(cases), "CS"),
                S + "Line Extension Amount": Quantity(money(sub_price * cases), CURRENCY),
                S + "Price/Price Amount": Quantity(sub[4] + "00", CURRENCY),
                S + "Price/Base Quantity": Quantity("1", "CS"),
                S + "Price/Price Type": "Contract price",
                S + "Item/Item Name": sub[1],
                S + "Item/Seller's Item Identification/Item Identification/Item Identification Scheme": "Seller's item number",
                S + "Item/Seller's Item Identification/Item Identification/Item Identification Value": sub[0],
                S + "Item/Standard Item Identification/Item Identification/Item Identification Scheme": "Global Trade Item Number (GS1)",
                S + "Item/Standard Item Identification/Item Identification/Item Identification Value": gs1_check(sub[3]),
            })
            total += sub_price * cases; weight += Decimal(sub[6]) * cases; volume += Decimal(sub[7]) * cases
        else:
            total += price * cases; weight += Decimal(catalog[item_no][6]) * cases; volume += Decimal(catalog[item_no][7]) * cases
        packages += cases
    v.update({
        R + "Order Response Document/Response Shipment Totals/Total Packages Quantity": Quantity(str(packages), "items"),
        R + "Order Response Document/Response Shipment Totals/Gross Weight": Quantity(f"{weight:.2f}", "kg"),
        R + "Order Response Document/Response Shipment Totals/Gross Volume": Quantity(f"{volume:.3f}", "L"),
        R + "Legal Monetary Total/Line Extension Total Amount": Quantity(money(total), CURRENCY),
        R + "Legal Monetary Total/Tax Exclusive Amount": Quantity(money(total), CURRENCY),
        R + "Legal Monetary Total/Tax Inclusive Amount": Quantity(money(total), CURRENCY),
        R + "Legal Monetary Total/Payable Amount": Quantity(money(total), CURRENCY),
    })
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{issued.isoformat()}T{rng.randint(7, 16):02d}:{rng.randint(0, 59):02d}:00"
    xml = record("Order Response", v, document_id=response_id, buyer=HALVORSEN["name"], when=when,
                 source=(f"urn:kestrel:order:{order_id}:ubl", f"{order_id}.xml", "The UBL 2.3 Order this response answers"),
                 agent=SELLER_SYSTEM, current_state="OrderProcessing", instance_id=cuid_generator(rng), rng=rng)
    rh = {"response_id": response_id, "order_id": order_id, "issued": issued.isoformat(), "kind": kind, "seller": HALVORSEN["name"], "buyer": KESTREL["name"]}
    return rh, v, xml


def generate_responses(orders: int, seed: str = "halvorsen-2026"):
    """Yield (order header, order values, order xml, response header, response values, response xml) for each order."""
    from halvorsen import generate
    rng = random.Random(seed + ":responses")
    for h, values, xml in generate(orders, seed=seed):
        rh, rv, rxml = respond(h, values, rng)
        yield h, values, xml, rh, rv, rxml
