"""
Kestrel's remittance advices for Halvorsen's invoices, generated on the template engine.

The retailer pays in monthly runs: every invoice due in a month is paid on the last day of that month, in one
remittance advice, one line an invoice. Where a credit note was issued against the invoice, the line takes it
into account: the debit is what the invoice made payable, the credit is what the credit note credited, the balance
is what is paid; the line's billing references name both documents. The header carries the totals debited, credited
and paid, the payer's references (its order for payment to its bank, its own reference, the one the supplier asked
it to quote), the accounting parties and the payee as the invoices named them, the payment means the order agreed,
and the exempt tax total. The record's state is OrderDelivered, the main path's last state: delivered and paid.

    from halvorsen_remittances import generate_remittances
    for mh, mv, mxml in generate_remittances(52):
        ...
"""
from __future__ import annotations

import calendar
import os
import random
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
from engine import Quantity  # noqa: E402
from halvorsen import CURRENCY, HALVORSEN, KESTREL, money  # noqa: E402
from shared import RETAILER_PAYMENTS as PAYMENT_SYSTEM, cuid_generator, record  # noqa: E402

I = "Invoice Governed Record/Invoice/"
N = "Credit Note Governed Record/Credit Note/"
M = "Remittance Advice Governed Record/Remittance Advice/"
LINES = 10


def month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def remittance(month: date, items: list[tuple[dict, dict, dict | None, dict | None]], seq: int, rng: random.Random) -> tuple[dict, dict, str]:
    """One payment run: (header, values, instance xml) for the invoices due in the month, each less its credit note."""
    paid_on = month_end(month)
    remittance_id = f"KM-RA-PAY-{paid_on.year}-{seq:06d}"
    ih0, iv0 = items[0][0], items[0][1]
    v = {
        M + "Remittance Advice Document/Customization ID": "https://axius-sdc.com/library/business/remittance-advice-governed-record",
        M + "Remittance Advice Document/Profile ID": iv0.get(I + "Invoice Document/Profile ID"),
        M + "Remittance Advice Document/Remittance Advice ID": remittance_id,
        M + "Remittance Advice Document/Copy Indicator": False,
        M + "Remittance Advice Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        M + "Remittance Advice Document/Issue Date": paid_on.isoformat(),
        M + "Remittance Advice Document/Issue Time": f"{rng.randint(9, 16):02d}:{rng.randint(0, 59):02d}:00",
        M + "Remittance Advice Document/Document Status": "Original",
        M + "Remittance Advice Document/Note": f"Payment run for the invoices due in {paid_on.strftime('%B %Y')}; each invoice paid less the credit note issued against it.",
        M + "Remittance Advice Document/Document Currency": CURRENCY,
        M + "Remittance Advice Document/Payment Order Reference": f"KM-BANK-{paid_on.year}{paid_on.month:02d}-{seq:04d}",
        M + "Remittance Advice Document/Payer Reference": f"KM-AP-{paid_on.year}-{seq:06d}",
        M + "Remittance Advice Document/Invoicing Party Reference": iv0.get(I + "Invoice Document/Buyer Reference"),
        M + "Remittance Advice Document/Line Count": Quantity(str(len(items)), "items"),
        M + "Remittance Advice Document/Invoice Period/Date Range/Date Range Start": date(month.year, month.month, 1).isoformat(),
        M + "Remittance Advice Document/Invoice Period/Date Range/Date Range End": paid_on.isoformat(),
        M + "Payment Means Instruction/Payment Means": iv0.get(I + "Payment Means Instruction/Payment Means"),
        M + "Payment Means Instruction/Payment Due Date": paid_on.isoformat(),
    }
    for side in ("Accounting Supplier Party/", "Accounting Customer Party/"):
        for key, val in iv0.items():
            if key.startswith(I + side):
                v[M + key[len(I):]] = val
    debit = credit = Decimal("0")
    paid_invoices = []
    for n, (ih, iv, ch, cv) in enumerate(items, start=1):
        L = M + f"Remittance Advice Lines/Remittance Advice Line {n}/Remittance Advice Line/"
        d = Decimal(ih["payable"]); c = Decimal(ch["amount"]) if ch else Decimal("0")
        debit += d; credit += c
        v.update({
            L + "Line ID": str(n),
            L + "Debit Line Amount": Quantity(money(d), CURRENCY),
            L + "Credit Line Amount": Quantity(money(c), CURRENCY),
            L + "Balance Amount": Quantity(money(d - c), CURRENCY),
            L + "Payment Purpose": "Payment of invoice" if not ch else "Payment of invoice less credit note",
            L + "Invoicing Party Reference": ih["invoice_id"],
            L + "Invoice Period/Date Range/Date Range Start": ih["issued"],
            L + "Invoice Period/Date Range/Date Range End": ih["due"],
            L + "Billing Reference/Invoice Document Reference/Document Reference/Document Reference ID": ih["invoice_id"],
            L + "Billing Reference/Invoice Document Reference/Document Reference/Document Reference Issue Date": ih["issued"],
            L + "Billing Reference/Invoice Document Reference/Document Reference/Document Type": "Invoice",
        })
        if ch:
            v.update({
                L + "Note": f"Credit note {ch['credit_note_id']} taken into account: {ch['amount']} {CURRENCY} off the invoice.",
                L + "Billing Reference/Credit Note Document Reference/Document Reference/Document Reference ID": ch["credit_note_id"],
                L + "Billing Reference/Credit Note Document Reference/Document Reference/Document Reference Issue Date": ch["issued"],
                L + "Billing Reference/Credit Note Document Reference/Document Reference/Document Type": "Credit note",
            })
        paid_invoices.append(ih["invoice_id"])
    v.update({
        M + "Remittance Advice Document/Total Debit Amount": Quantity(money(debit), CURRENCY),
        M + "Remittance Advice Document/Total Credit Amount": Quantity(money(credit), CURRENCY),
        M + "Remittance Advice Document/Total Payment Amount": Quantity(money(debit - credit), CURRENCY),
        M + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
        M + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(debit - credit), CURRENCY),
        M + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
        M + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
        M + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
        M + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
        M + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
        M + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
    })
    v = {k: val for k, val in v.items() if val is not None}
    when = f"{paid_on.isoformat()}T{rng.randint(9, 16):02d}:{rng.randint(0, 59):02d}:00"
    xml = record("Remittance Advice", v, document_id=remittance_id, buyer=KESTREL["name"], when=when,
                 source=(f"urn:kestrel:payment-run:{paid_on.year}-{paid_on.month:02d}", f"Payment run {paid_on.strftime('%B %Y')}", "The invoices due in the month, paid less the credit notes issued against them: " + ", ".join(paid_invoices)),
                 agent=PAYMENT_SYSTEM, current_state="OrderDelivered", instance_id=cuid_generator(rng), rng=rng)
    mh = {"remittance_id": remittance_id, "paid_on": paid_on.isoformat(), "month": paid_on.strftime("%Y-%m"), "invoices": paid_invoices,
          "credit_notes": [ch["credit_note_id"] for *_, ch, _ in items if ch], "debit": money(debit), "credit": money(credit), "paid": money(debit - credit),
          "lines": len(items), "payer": KESTREL["name"], "payee": HALVORSEN["name"]}
    return mh, v, xml


def payment_runs(invoices_and_credits):
    """Group (invoice header, values, credit note header or None, values or None) by the month the invoice is due, at most LINES to a run."""
    by_month = defaultdict(list)
    for ih, iv, ch, cv in invoices_and_credits:
        due = date.fromisoformat(ih["due"])
        by_month[date(due.year, due.month, 1)].append((ih, iv, ch, cv))
    for month in sorted(by_month):
        items = by_month[month]
        for start in range(0, len(items), LINES):
            yield month, items[start:start + LINES]


def generate_remittances(orders: int, seed: str = "halvorsen-2026"):
    """Yield (remittance header, values, xml) for each monthly payment run of the year's invoices, less their credit notes."""
    from halvorsen_credit_notes import generate_credit_notes
    rng = random.Random(seed + ":remittances")
    pairs = [(ih, iv, ch, cv) for *_, ih, iv, ixml, ch, cv, cxml in generate_credit_notes(orders, seed=seed)]
    for seq, (month, items) in enumerate(payment_runs(pairs), start=1):
        yield remittance(month, items, seq, rng)
