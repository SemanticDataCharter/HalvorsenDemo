"""
Halvorsen's invoices for Kestrel's receipts, generated on the template engine.

The seller bills the day after the receipt advice arrives, for what the retailer received: every line
at the quantity the receipt states, at the price the order response confirmed, with the short and the
rejected cases left off the bill. The invoice names the order, the dispatch advice and the receipt
advice it settles, line by line, and carries the order's payment means and terms, its tax total (the
lines are exempt, as the order stated) and the legal monetary total. Every twelfth order was paid a
deposit up front, so the invoice carries a prepaid payment and the payable amount is the balance. The
record's state is OrderPaymentDue.

    from halvorsen_invoices import generate_invoices
    for *_, ih, invoice_values, invoice_xml in generate_invoices(52):
        ...
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import CURRENCY, HALVORSEN, KESTREL, money  # noqa: E402
from shared import SUPPLIER_BILLING as BILLING_SYSTEM, cuid_generator, record  # noqa: E402

O = "Order Governed Record/Order/"
R = "Order Response Governed Record/Order Response/"
K = "Receipt Advice Governed Record/Receipt Advice/"
I = "Invoice Governed Record/Invoice/"
DEPOSIT = Decimal("0.10")


def _lines(kv: dict) -> list[int]:
    return [n for n in range(1, 11) if (K + f"Receipt Lines/Receipt Line {n}/Receipt Line/Line ID") in kv]


def invoice(h: dict, order: dict, rh: dict, rv: dict, dh: dict, kh: dict, kv: dict, rng: random.Random) -> tuple[dict, dict, str]:
    """Halvorsen's invoice for one receipt: (header, values, instance xml)."""
    order_id = h["order_id"]
    seq = int(order_id.rsplit("-", 1)[1])
    issued = date.fromisoformat(kh["received"]) + timedelta(days=1)
    due = issued + timedelta(days=30)
    invoice_id = f"HF-INV-{issued.year}-{seq:06d}"
    kind = "deposit" if seq % 12 == 1 else "standard"
    v = {
        I + "Invoice Document/Customization ID": "https://axius-sdc.com/library/business/invoice-governed-record",
        I + "Invoice Document/Profile ID": order.get(O + "Order Document/Profile ID"),
        I + "Invoice Document/Invoice ID": invoice_id,
        I + "Invoice Document/Copy Indicator": False,
        I + "Invoice Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        I + "Invoice Document/Issue Date": issued.isoformat(),
        I + "Invoice Document/Issue Time": f"{rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}:00",
        I + "Invoice Document/Due Date": due.isoformat(),
        I + "Invoice Document/Document Status": "Original",
        I + "Invoice Document/Invoice Type": "Commercial invoice",
        I + "Invoice Document/Note": "Billed for the quantities received, as the receipt advice states; short and rejected cases are not billed.",
        I + "Invoice Document/Tax Point Date": issued.isoformat(),
        I + "Invoice Document/Document Currency": CURRENCY,
        I + "Invoice Document/Accounting Cost": order.get(O + "Order Document/Accounting Cost"),
        I + "Invoice Document/Buyer Reference": order.get(O + "Order Document/Customer Reference"),
        I + "Invoice Document/Invoice Period/Date Range/Date Range Start": kh["received"],
        I + "Invoice Document/Invoice Period/Date Range/Date Range End": kh["received"],
        I + "Despatch Document Reference/Document Reference/Document Reference ID": dh["dispatch_id"],
        I + "Despatch Document Reference/Document Reference/Document Reference Issue Date": dh["issued"],
        I + "Despatch Document Reference/Document Reference/Document Type": "Despatch advice",
        I + "Receipt Document Reference/Document Reference/Document Reference ID": kh["receipt_id"],
        I + "Receipt Document Reference/Document Reference/Document Reference Issue Date": kh["received"],
        I + "Receipt Document Reference/Document Reference/Document Type": "Receipt advice",
        I + "Receipt Document Reference/Document Reference/Document Description": "The receipt advice this invoice settles against.",
        I + "Contract/Contract ID": order.get(O + "Contract/Contract ID"),
        I + "Contract/Contract Issue Date": order.get(O + "Contract/Contract Issue Date"),
        I + "Contract/Contract Type": order.get(O + "Contract/Contract Type"),
        I + "Delivery Terms/Delivery Terms Code": order.get(O + "Delivery Terms/Delivery Terms Code"),
        I + "Payment Means Instruction/Payment Means": order.get(O + "Payment Means/Payment Means"),
        I + "Payment Means Instruction/Payment Due Date": due.isoformat(),
        I + "Payment Terms/Payment Terms ID": order.get(O + "Payment Terms/Payment Terms ID"),
        I + "Payment Terms/Note": order.get(O + "Payment Terms/Note"),
        I + "Payment Terms/Settlement Discount Percent": order.get(O + "Payment Terms/Settlement Discount Percent"),
        I + "Payment Terms/Payment Due Date": due.isoformat(),
        I + "Payment Terms/Settlement Period/Date Range/Date Range Start": issued.isoformat(),
        I + "Payment Terms/Settlement Period/Date Range/Date Range End": (issued + timedelta(days=10)).isoformat(),
    }
    # the order reference as the response stated it; the delivery as the dispatch stated it; the parties as the order named them
    for key, val in rv.items():
        if key.startswith(R + "Order Reference/"):
            v[I + key[len(R):]] = val
    for key, val in kv.items():
        if key.startswith(K + "Receipt Shipment/Delivery/"):
            v[I + "Delivery/" + key[len(K + "Receipt Shipment/Delivery/"):]] = val
    for side, src in (("Accounting Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"), ("Seller Supplier Party/Supplier Party/", "Seller Supplier Party/Supplier Party/"),
                      ("Accounting Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/"), ("Buyer Customer Party/Customer Party/", "Buyer Customer Party/Customer Party/")):
        for key, val in order.items():
            if key.startswith(O + src):
                v[I + side + key[len(O + src):]] = val
    # the lines: the received quantity at the confirmed price
    total = Decimal("0")
    lines = _lines(kv)
    for n in lines:
        KL = K + f"Receipt Lines/Receipt Line {n}/Receipt Line/"
        RL = R + f"Order Response Lines/Order Response Line {n}/Order Response Line/"
        L = I + f"Invoice Lines/Invoice Line {n}/Invoice Line/"
        received = int(kv[KL + "Received Quantity"].magnitude)
        answer = rv[RL + "Line Response"]
        price_path = RL + ("Seller Substituted Line Item/Line Item/Price/Price Amount" if answer == "Substituted" else "Line Item/Price/Price Amount")
        price = Decimal(rv[price_path].magnitude)
        ext = price * received
        total += ext
        v.update({
            L + "Line ID": str(n),
            L + "Invoiced Quantity": Quantity(str(received), "CS"),
            L + "Line Extension Amount": Quantity(money(ext), CURRENCY),
            L + "Tax Inclusive Line Extension Amount": Quantity(money(ext), CURRENCY),
            L + "Free of Charge": False,
            L + "Despatch Line Reference/Line ID": str(n),
            L + "Despatch Line Reference/Document Reference/Document Reference ID": dh["dispatch_id"],
            L + "Despatch Line Reference/Document Reference/Document Type": "Despatch advice",
            L + "Receipt Line Reference/Line ID": str(n),
            L + "Receipt Line Reference/Document Reference/Document Reference ID": kh["receipt_id"],
            L + "Receipt Line Reference/Document Reference/Document Type": "Receipt advice",
            L + "Price/Price Amount": rv[price_path],
            L + "Price/Base Quantity": Quantity("1", "CS"),
            L + "Price/Price Type": "Contract price",
            L + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
            L + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(ext), CURRENCY),
            L + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
            L + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
            L + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
            L + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
            L + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
            L + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
        })
        if received == 0:
            v[L + "Note"] = "Nothing received on this line; billed at zero."
        elif (KL + "Short Quantity") in kv or (KL + "Rejected Quantity") in kv:
            v[L + "Note"] = "Billed for the quantity received; the balance is not billed."
        for key, val in kv.items():
            if key.startswith(KL + "Order Line Reference/") or key.startswith(KL + "Item/"):
                v[L + key[len(KL):]] = val
    prepaid = Decimal("0")
    if kind == "deposit" and total:
        prepaid = (total * DEPOSIT).quantize(Decimal("0.01"))
        v.update({
            I + "Prepaid Payment/Payment ID": f"KM-PAY-{h['issued'][:4]}-{seq:06d}",
            I + "Prepaid Payment/Paid Amount": Quantity(money(prepaid), CURRENCY),
            I + "Prepaid Payment/Paid Date": h["issued"],
            I + "Prepaid Payment/Payment Received Date": (date.fromisoformat(h["issued"]) + timedelta(days=1)).isoformat(),
            I + "Prepaid Payment/Payment Instruction ID": f"{order_id}-DEPOSIT",
        })
    v.update({
        I + "Invoice Document/Line Count": Quantity(str(len(lines)), "items"),
        I + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
        I + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(total), CURRENCY),
        I + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
        I + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
        I + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
        I + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
        I + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
        I + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
        I + "Legal Monetary Total/Line Extension Total Amount": Quantity(money(total), CURRENCY),
        I + "Legal Monetary Total/Tax Exclusive Amount": Quantity(money(total), CURRENCY),
        I + "Legal Monetary Total/Tax Inclusive Amount": Quantity(money(total), CURRENCY),
        I + "Legal Monetary Total/Prepaid Amount": Quantity(money(prepaid), CURRENCY) if prepaid else None,
        I + "Legal Monetary Total/Payable Amount": Quantity(money(total - prepaid), CURRENCY),
    })
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{issued.isoformat()}T{rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}:00"
    xml = record("Invoice", v, document_id=invoice_id, buyer=HALVORSEN["name"], when=when,
                 source=(f"urn:kestrel:receipt:{kh['receipt_id']}", f"{kh['receipt_id']}.xml", "The Receipt Advice this invoice settles against"),
                 agent=BILLING_SYSTEM, current_state="OrderPaymentDue", instance_id=cuid_generator(rng), rng=rng)
    ih = {"invoice_id": invoice_id, "receipt_id": kh["receipt_id"], "dispatch_id": dh["dispatch_id"], "order_id": order_id, "issued": issued.isoformat(), "due": due.isoformat(),
          "kind": kind, "total": money(total), "prepaid": money(prepaid), "payable": money(total - prepaid), "lines": len(lines), "seller": HALVORSEN["name"], "buyer": KESTREL["name"]}
    return ih, v, xml


def generate_invoices(orders: int, seed: str = "halvorsen-2026"):
    """Yield the twelve of generate_receipts, then (invoice header, values, xml), for each order."""
    from halvorsen_receipts import generate_receipts
    rng = random.Random(seed + ":invoices")
    for h, values, xml, rh, rv, rxml, dh, dv, dxml, kh, kv, kxml in generate_receipts(orders, seed=seed):
        ih, iv, ixml = invoice(h, values, rh, rv, dh, kh, kv, rng)
        yield h, values, xml, rh, rv, rxml, dh, dv, dxml, kh, kv, kxml, ih, iv, ixml
