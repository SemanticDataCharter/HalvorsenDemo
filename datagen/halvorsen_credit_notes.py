"""
Halvorsen's credit notes for the deductions Kestrel took, generated on the template engine.

Where a receipt advice went into the OrderProblem state (a pallet accepted with an exception: an identifier
outside its validity period, or a unit packed to a pack specification no longer in force), the retailer deducts
three percent of the invoice, and the deduction is agreed. The seller then credits it: one credit note against
the invoice, one line, the deduction as the amount, the discrepancy response naming the receipt advice and
what was found on each pallet, the credit note type a credit note related to goods or services. The credit
note names the order, the dispatch advice, the receipt advice and the invoice it credits, as the invoice did,
and is dated fourteen days after the invoice, the dispute period the payment terms give. The record's state
is OrderPaymentDue: the balance of the invoice, less the credit, is what is paid.

    from halvorsen_credit_notes import generate_credit_notes
    for *_, ih, iv, ixml, ch, cv, cxml in generate_credit_notes(52):
        ...   # ch, cv, cxml are None for the receipts without a deduction

The demonstration (HalvorsenDemo) issues the same credit notes after the deduction is settled with a Settlement
Receipt, and names the Receipt as the entity the credit note's activity used; ``credit_note(..., source=...)``
takes that entity.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import CURRENCY, HALVORSEN, KESTREL, money  # noqa: E402
from shared import SUPPLIER_BILLING as BILLING_SYSTEM, cuid_generator, record  # noqa: E402

I = "Invoice Governed Record/Invoice/"
K = "Receipt Advice Governed Record/Receipt Advice/"
N = "Credit Note Governed Record/Credit Note/"
DEDUCTION_PERCENT = Decimal("3")
DISPUTE_DAYS = 14


def findings(kv: dict) -> list[str]:
    """What the receiver found on each pallet accepted with an exception, in the receipt advice's own words."""
    out = []
    for n in range(1, 7):
        U = K + f"Receipt Shipment/Received Handling Units/Received Handling Unit {n}/Received Handling Unit/"
        if kv.get(U + "Receiving Condition") == "Accepted with exception" and kv.get(U + "Exception Description"):
            out.append(kv[U + "Exception Description"])
    return out


def credit_note(ih: dict, iv: dict, kh: dict, kv: dict, rng: random.Random, source: tuple[str, str, str] | None = None) -> tuple[dict, dict, str]:
    """Halvorsen's credit note for one settled deduction: (header, values, instance xml)."""
    seq = int(ih["invoice_id"].rsplit("-", 1)[1])
    issued = date.fromisoformat(ih["issued"]) + timedelta(days=DISPUTE_DAYS)
    credit_note_id = f"HF-CN-{issued.year}-{seq:06d}"
    payable = Decimal(ih["payable"])
    amount = (payable * DEDUCTION_PERCENT / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    found = findings(kv)
    description = (f"Deduction of {DEDUCTION_PERCENT} percent of invoice {ih['invoice_id']} ({money(payable)} {CURRENCY}) agreed on receipt advice {kh['receipt_id']}: "
                   + " ".join(found))[:500]
    v = {
        N + "Credit Note Document/Customization ID": "https://axius-sdc.com/library/business/credit-note-governed-record",
        N + "Credit Note Document/Profile ID": iv.get(I + "Invoice Document/Profile ID"),
        N + "Credit Note Document/Credit Note ID": credit_note_id,
        N + "Credit Note Document/Copy Indicator": False,
        N + "Credit Note Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        N + "Credit Note Document/Issue Date": issued.isoformat(),
        N + "Credit Note Document/Issue Time": f"{rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}:00",
        N + "Credit Note Document/Due Date": ih["due"],
        N + "Credit Note Document/Document Status": "Original",
        N + "Credit Note Document/Credit Note Type": "Credit note related to goods or services",
        N + "Credit Note Document/Note": "Credits the deduction agreed on the receipt advice; the balance of the invoice is payable on its due date.",
        N + "Credit Note Document/Tax Point Date": issued.isoformat(),
        N + "Credit Note Document/Document Currency": CURRENCY,
        N + "Credit Note Document/Accounting Cost": iv.get(I + "Invoice Document/Accounting Cost"),
        N + "Credit Note Document/Line Count": Quantity("1", "items"),
        N + "Credit Note Document/Buyer Reference": iv.get(I + "Invoice Document/Buyer Reference"),
        N + "Credit Note Document/Invoice Period/Date Range/Date Range Start": kh["received"],
        N + "Credit Note Document/Invoice Period/Date Range/Date Range End": kh["received"],
        N + "Discrepancy Response/Discrepancy Reference ID": ih["invoice_id"],
        N + "Discrepancy Response/Discrepancy Response Code": "Deduction agreed",
        N + "Discrepancy Response/Discrepancy Description": description,
        N + "Discrepancy Response/Discrepancy Effective Date": kh["received"],
        N + "Billing Reference/Invoice Document Reference/Document Reference/Document Reference ID": ih["invoice_id"],
        N + "Billing Reference/Invoice Document Reference/Document Reference/Document Reference Issue Date": ih["issued"],
        N + "Billing Reference/Invoice Document Reference/Document Reference/Document Type": "Other document",
        N + "Billing Reference/Invoice Document Reference/Document Reference/Document Description": "The invoice this credit note credits.",
    }
    # the order, dispatch and receipt references, the contract, the parties, the delivery, the payment means and terms, as the invoice named them
    for key, val in iv.items():
        rest = key[len(I):]
        if rest.startswith(("Order Reference/", "Despatch Document Reference/", "Receipt Document Reference/", "Contract/", "Accounting Supplier Party/", "Accounting Customer Party/",
                            "Buyer Customer Party/", "Seller Supplier Party/", "Delivery/", "Delivery Terms/", "Payment Means Instruction/", "Payment Terms/")):
            v[N + rest] = val
    L = N + "Credit Note Lines/Credit Note Line 1/Credit Note Line/"
    v.update({
        L + "Line ID": "1",
        L + "Note": f"{DEDUCTION_PERCENT} percent of the invoice payable, {money(payable)} {CURRENCY}, for the pallets accepted with an exception.",
        L + "Credited Quantity": Quantity("1", "EA"),
        L + "Line Extension Amount": Quantity(money(amount), CURRENCY),
        L + "Tax Inclusive Line Extension Amount": Quantity(money(amount), CURRENCY),
        L + "Free of Charge": False,
        L + "Discrepancy Response/Discrepancy Reference ID": kh["receipt_id"],
        L + "Discrepancy Response/Discrepancy Response Code": "Deduction agreed",
        L + "Discrepancy Response/Discrepancy Description": (" ".join(found) or "Accepted with exception.")[:500],
        L + "Discrepancy Response/Discrepancy Effective Date": kh["received"],
        L + "Receipt Line Reference/Line ID": "1",
        L + "Receipt Line Reference/Document Reference/Document Reference ID": kh["receipt_id"],
        L + "Receipt Line Reference/Document Reference/Document Type": "Receipt advice",
        L + "Billing Reference/Invoice Document Reference/Document Reference/Document Reference ID": ih["invoice_id"],
        L + "Billing Reference/Invoice Document Reference/Document Reference/Document Type": "Other document",
        L + "Billing Reference/Invoice Document Reference/Document Reference/Document Description": "The invoice this line credits.",
        L + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
        L + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(amount), CURRENCY),
        L + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
        L + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
        L + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
        L + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
        L + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
        L + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
        L + "Item/Item Name": "Deduction for pallets accepted with an exception",
        L + "Item/Item Description": f"{DEDUCTION_PERCENT} percent of invoice {ih['invoice_id']}, agreed on receipt advice {kh['receipt_id']}.",
        L + "Price/Price Amount": Quantity(money(amount), CURRENCY),
        L + "Price/Base Quantity": Quantity("1", "EA"),
        L + "Price/Price Type": "Contract price",
        N + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
        N + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(amount), CURRENCY),
        N + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
        N + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
        N + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
        N + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
        N + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
        N + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
        N + "Legal Monetary Total/Line Extension Total Amount": Quantity(money(amount), CURRENCY),
        N + "Legal Monetary Total/Tax Exclusive Amount": Quantity(money(amount), CURRENCY),
        N + "Legal Monetary Total/Tax Inclusive Amount": Quantity(money(amount), CURRENCY),
        N + "Legal Monetary Total/Payable Amount": Quantity(money(amount), CURRENCY),
    })
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{issued.isoformat()}T{rng.randint(8, 16):02d}:{rng.randint(0, 59):02d}:00"
    src = source or (f"urn:halvorsen:invoice:{ih['invoice_id']}", f"{ih['invoice_id']}.xml", "The Invoice this credit note credits")
    xml = record("Credit Note", v, document_id=credit_note_id, buyer=HALVORSEN["name"], when=when, source=src,
                 agent=BILLING_SYSTEM, current_state="OrderPaymentDue", instance_id=cuid_generator(rng), rng=rng)
    ch = {"credit_note_id": credit_note_id, "invoice_id": ih["invoice_id"], "receipt_id": kh["receipt_id"], "dispatch_id": ih["dispatch_id"], "order_id": ih["order_id"],
          "issued": issued.isoformat(), "amount": money(amount), "payable": money(payable), "findings": len(found), "seller": HALVORSEN["name"], "buyer": KESTREL["name"]}
    return ch, v, xml


def generate_credit_notes(orders: int, seed: str = "halvorsen-2026"):
    """Yield the fifteen of generate_invoices, then (credit note header, values, xml) or three Nones, for each order."""
    from halvorsen_invoices import generate_invoices
    rng = random.Random(seed + ":credit-notes")
    for h, values, xml, rh, rv, rxml, dh, dv, dxml, kh, kv, kxml, ih, iv, ixml in generate_invoices(orders, seed=seed):
        if kh["exceptions"]:
            ch, cv, cxml = credit_note(ih, iv, kh, kv, rng)
        else:
            ch = cv = cxml = None
        yield h, values, xml, rh, rv, rxml, dh, dv, dxml, kh, kv, kxml, ih, iv, ixml, ch, cv, cxml
