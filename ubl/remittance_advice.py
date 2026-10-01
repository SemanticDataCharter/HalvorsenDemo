"""
The RemittanceAdvice's open projection: a conformant OASIS UBL 2.3 RemittanceAdvice written from a governed record, and read into one.

    from ubl.remittance_advice import write_remittance_advice, read_remittance_advice, validate_ubl_remittance_advice
    ubl_xml = write_remittance_advice(instance_xml)
    assert not validate_ubl_remittance_advice(ubl_xml)
    values = read_remittance_advice(ubl_xml)

The remittance advice composes the Invoice's header leaves, the accounting parties, the payee, the payment means and
the tax total, and the billing reference revised to name the credit note beside the invoice, so its writer and reader
are the Invoice's with the remittance advice's own parts added: the totals debited, credited and paid and the payer's
references are UBL's own header elements; each line's debit, credit and balance are ``cbc:DebitLineAmount``,
``cbc:CreditLineAmount`` and ``cbc:BalanceAmount``; the payment's purpose is ``cbc:PaymentPurposeCode``; the invoice
paid and the credit note taken into account are the line's ``cac:BillingReference`` with ``cac:InvoiceDocumentReference``
and ``cac:CreditNoteDocumentReference``. UBL's RemittanceAdvice orders the accounting customer before the accounting
supplier, and the writer follows it. UBL's RemittanceAdvice carries no document status: the header's Document Status
is left out and named (NOT_PROJECTED_REMITTANCE); two leaves of every party have no home in a UBL Contact
(NOT_PROJECTED, from the Order); nothing else is.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any

from lxml import etree

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "datagen"))
from instance import Node, read_tree  # noqa: E402
from invoice import _InvoiceReader, _InvoiceWriter  # noqa: E402
from order import CAC, CBC, NOT_PROJECTED, NOT_PROJECTED_UNDER, NS, ROOT, UBL_VERSION  # noqa: E402
from schema import Schema  # noqa: E402

REMITTANCE_CT = "fgtbf38cj0bwxppxn69etcci"
REMITTANCE_NS = "urn:oasis:names:specification:ubl:schema:xsd:RemittanceAdvice-2"
NSMAP_REMITTANCE = {None: REMITTANCE_NS, "cac": CAC, "cbc": CBC}
UBL_REMITTANCE_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-RemittanceAdvice-2.3.xsd")
MR = ("Remittance Advice Governed Record", "Remittance Advice")
#: UBL's RemittanceAdvice has no DocumentStatusCode: the header's status has no home in the document.
NOT_PROJECTED_REMITTANCE = {("Remittance Advice Document", "Document Status")}
LINES = 10


@lru_cache(maxsize=None)
def ubl_remittance_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_REMITTANCE_XSD)


def validate_ubl_remittance_advice(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 RemittanceAdvice schema; empty when conformant."""
    return [str(e) for e in ubl_remittance_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_remittance_advice(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(REMITTANCE_CT))
    m = tree.get(*MR)
    assert m is not None, "no Remittance Advice cluster in the instance"
    w = _RemittanceWriter()
    root = etree.Element(f"{{{REMITTANCE_NS}}}RemittanceAdvice", nsmap=NSMAP_REMITTANCE)
    h = m.get("Remittance Advice Document") or Node("Remittance Advice Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Remittance Advice ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.cbc(root, "Note", h.leaf("Note"))
    w.cbc(root, "DocumentCurrencyCode", h.leaf("Document Currency"))
    w.amount(root, "TotalDebitAmount", h.leaf("Total Debit Amount"))
    w.amount(root, "TotalCreditAmount", h.leaf("Total Credit Amount"))
    w.amount(root, "TotalPaymentAmount", h.leaf("Total Payment Amount"))
    w.cbc(root, "PaymentOrderReference", h.leaf("Payment Order Reference"))
    w.cbc(root, "PayerReference", h.leaf("Payer Reference"))
    w.cbc(root, "InvoicingPartyReference", h.leaf("Invoicing Party Reference"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.period(root, "InvoicePeriod", h.get("Invoice Period"))
    w.billing_references(root, m.get("Billing Reference"))
    w.docref(root, "AdditionalDocumentReference", m.get("Additional Document Reference", "Document Reference"))
    # UBL requires the accounting customer and supplier, in that order, every member optional: present even when the record has none
    w.customer_party(root, "AccountingCustomerParty", m.get("Accounting Customer Party", "Customer Party"))
    w.required(root, "AccountingCustomerParty")
    w.supplier_party(root, "AccountingSupplierParty", m.get("Accounting Supplier Party", "Supplier Party"))
    w.required(root, "AccountingSupplierParty")
    w.plain_party(root, "PayeeParty", m.get("Payee Party", "Party"))
    w.payment_means(root, m.get("Payment Means Instruction"))
    w.tax_total(root, m.get("Tax Total"))
    lines = m.get("Remittance Advice Lines") or Node("Remittance Advice Lines")
    for n in range(1, LINES + 1):
        w.remittance_line(root, lines.get(f"Remittance Advice Line {n}", "Remittance Advice Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _RemittanceWriter(_InvoiceWriter):
    def billing_references(self, parent, node: Node | None):
        """The billing documents: the invoice paid and the credit note taken into account, each a document reference under UBL's BillingReference."""
        if node is None:
            return
        inv = node.get("Invoice Document Reference", "Document Reference")
        cn = node.get("Credit Note Document Reference", "Document Reference")
        have_inv = inv is not None and inv.leaf("Document Reference ID") is not None
        have_cn = cn is not None and cn.leaf("Document Reference ID") is not None
        if not (have_inv or have_cn):
            return
        el = self.cac(parent, "BillingReference")
        if have_inv:
            self.docref(el, "InvoiceDocumentReference", inv)
        if have_cn:
            self.docref(el, "CreditNoteDocumentReference", cn)

    def remittance_line(self, parent, node: Node | None):
        if node is None or node.leaf("Line ID") is None:
            return   # UBL requires the line's identifier
        rl = self.cac(parent, "RemittanceAdviceLine")
        self.cbc(rl, "ID", node.leaf("Line ID"))
        self.cbc(rl, "Note", node.leaf("Note"))
        self.amount(rl, "DebitLineAmount", node.leaf("Debit Line Amount"))
        self.amount(rl, "CreditLineAmount", node.leaf("Credit Line Amount"))
        self.amount(rl, "BalanceAmount", node.leaf("Balance Amount"))
        self.cbc(rl, "PaymentPurposeCode", node.leaf("Payment Purpose"))
        self.cbc(rl, "InvoicingPartyReference", node.leaf("Invoicing Party Reference"))
        self.supplier_party(rl, "AccountingSupplierParty", node.get("Accounting Supplier Party", "Supplier Party"))
        self.customer_party(rl, "AccountingCustomerParty", node.get("Accounting Customer Party", "Customer Party"))
        self.customer_party(rl, "BuyerCustomerParty", node.get("Buyer Customer Party", "Customer Party"))
        self.supplier_party(rl, "SellerSupplierParty", node.get("Seller Supplier Party", "Supplier Party"))
        self.plain_party(rl, "PayeeParty", node.get("Payee Party", "Party"))
        self.period(rl, "InvoicePeriod", node.get("Invoice Period"))
        self.billing_references(rl, node.get("Billing Reference"))
        self.docref(rl, "DocumentReference", node.get("Line Document Reference", "Document Reference"))


# ================================================================ reader
def read_remittance_advice(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 RemittanceAdvice by label path in the Remittance Advice model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{REMITTANCE_NS}}}RemittanceAdvice", root.tag
    r = _RemittanceReader()
    out = r.out
    h = MR + ("Remittance Advice Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Remittance Advice ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.text(root, "cbc:DocumentCurrencyCode", h + ("Document Currency",))
    r.currency = out.get("/".join(h + ("Document Currency",)))
    r.amount(root, "cbc:TotalDebitAmount", h + ("Total Debit Amount",))
    r.amount(root, "cbc:TotalCreditAmount", h + ("Total Credit Amount",))
    r.amount(root, "cbc:TotalPaymentAmount", h + ("Total Payment Amount",))
    r.text(root, "cbc:PaymentOrderReference", h + ("Payment Order Reference",))
    r.text(root, "cbc:PayerReference", h + ("Payer Reference",))
    r.text(root, "cbc:InvoicingPartyReference", h + ("Invoicing Party Reference",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.period(root, "cac:InvoicePeriod", h + ("Invoice Period",))
    r.billing_references(root, MR + ("Billing Reference",))
    r.docref(root, "cac:AdditionalDocumentReference", MR + ("Additional Document Reference", "Document Reference"))
    r.customer_party(root, "cac:AccountingCustomerParty", MR + ("Accounting Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:AccountingSupplierParty", MR + ("Accounting Supplier Party", "Supplier Party"))
    r.party_from(r.one(root, "cac:PayeeParty"), MR + ("Payee Party", "Party"))
    r.payment_means(root, MR + ("Payment Means Instruction",))
    r.tax_total(root, MR + ("Tax Total",))
    lines = root.findall("cac:RemittanceAdviceLine", NS)
    assert len(lines) <= LINES, f"the Remittance Advice model carries {LINES} lines; the document has {len(lines)}"
    for n, rl in enumerate(lines, start=1):
        r.remittance_line(rl, MR + ("Remittance Advice Lines", f"Remittance Advice Line {n}", "Remittance Advice Line"))
    return out


class _RemittanceReader(_InvoiceReader):
    def billing_references(self, el, to: tuple[str, ...]):
        br = self.one(el, "cac:BillingReference")
        if br is not None:
            self.docref(br, "cac:InvoiceDocumentReference", to + ("Invoice Document Reference", "Document Reference"))
            self.docref(br, "cac:CreditNoteDocumentReference", to + ("Credit Note Document Reference", "Document Reference"))

    def remittance_line(self, rl, to: tuple[str, ...]):
        self.text(rl, "cbc:ID", to + ("Line ID",))
        self.text(rl, "cbc:Note", to + ("Note",))
        self.amount(rl, "cbc:DebitLineAmount", to + ("Debit Line Amount",))
        self.amount(rl, "cbc:CreditLineAmount", to + ("Credit Line Amount",))
        self.amount(rl, "cbc:BalanceAmount", to + ("Balance Amount",))
        self.text(rl, "cbc:PaymentPurposeCode", to + ("Payment Purpose",))
        self.text(rl, "cbc:InvoicingPartyReference", to + ("Invoicing Party Reference",))
        self.supplier_party(rl, "cac:AccountingSupplierParty", to + ("Accounting Supplier Party", "Supplier Party"))
        self.customer_party(rl, "cac:AccountingCustomerParty", to + ("Accounting Customer Party", "Customer Party"))
        self.customer_party(rl, "cac:BuyerCustomerParty", to + ("Buyer Customer Party", "Customer Party"))
        self.supplier_party(rl, "cac:SellerSupplierParty", to + ("Seller Supplier Party", "Supplier Party"))
        self.party_from(self.one(rl, "cac:PayeeParty"), to + ("Payee Party", "Party"))
        self.period(rl, "cac:InvoicePeriod", to + ("Invoice Period",))
        self.billing_references(rl, to + ("Billing Reference",))
        self.docref(rl, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))


def projected_remittance_advice(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL RemittanceAdvice can carry: everything but NOT_PROJECTED, NOT_PROJECTED_UNDER and the header's document status."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        if len(parts) >= 2 and tuple(parts[-2:]) in NOT_PROJECTED_REMITTANCE:
            continue
        out[path] = v
    return out
