"""
The CreditNote's open projection: a conformant OASIS UBL 2.3 CreditNote written from a governed record, and read into one.

    from ubl.credit_note import write_credit_note, read_credit_note, validate_ubl_credit_note
    ubl_xml = write_credit_note(instance_xml)
    assert not validate_ubl_credit_note(ubl_xml)
    values = read_credit_note(ubl_xml)

The credit note composes the Invoice, so its writer and reader are the Invoice's with the credit note's own parts
added: the type is this library's token with ``listURI``; the discrepancy it resolves is ``cac:DiscrepancyResponse``
(the reference, the response code, the description, the effective date), at the document and on each line; each
line's credited quantity is ``cbc:CreditedQuantity`` and the invoice it credits is the line's ``cac:BillingReference``.
UBL's CreditNote orders the contract and the additional document references before the originator's, and a line's
tax total before its allowances and charges, and the writer follows it. UBL's CreditNote carries no prepaid payment
and no document status: the header's Document Status is left out and named (NOT_PROJECTED_CREDIT_NOTE), as the
Invoice's is; two leaves of every party have no home in a UBL Contact (NOT_PROJECTED, from the Order); nothing else is.
The invoice credited is named by its identifier under the document kind ``Other document``: the library's list of
document kinds stops at the receipt advice.
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

CREDIT_NOTE_CT = "jkuyr38hydqaiwlq5vhp2rjr"
CREDIT_NOTE_NS = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NSMAP_CREDIT_NOTE = {None: CREDIT_NOTE_NS, "cac": CAC, "cbc": CBC}
UBL_CREDIT_NOTE_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-CreditNote-2.3.xsd")
CR = ("Credit Note Governed Record", "Credit Note")
#: UBL's CreditNote has no DocumentStatusCode: the header's status has no home in the document.
NOT_PROJECTED_CREDIT_NOTE = {("Credit Note Document", "Document Status")}
LINES = 10


@lru_cache(maxsize=None)
def ubl_credit_note_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_CREDIT_NOTE_XSD)


def validate_ubl_credit_note(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 CreditNote schema; empty when conformant."""
    return [str(e) for e in ubl_credit_note_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_credit_note(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(CREDIT_NOTE_CT))
    c = tree.get(*CR)
    assert c is not None, "no Credit Note cluster in the instance"
    w = _CreditNoteWriter()
    root = etree.Element(f"{{{CREDIT_NOTE_NS}}}CreditNote", nsmap=NSMAP_CREDIT_NOTE)
    h = c.get("Credit Note Document") or Node("Credit Note Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Credit Note ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.cbc(root, "DueDate", h.leaf("Due Date"))
    w.cbc(root, "TaxPointDate", h.leaf("Tax Point Date"))
    w.token(root, "CreditNoteTypeCode", h.leaf("Credit Note Type"), "credit-note-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.cbc(root, "DocumentCurrencyCode", h.leaf("Document Currency"))
    w.cbc(root, "TaxCurrencyCode", h.leaf("Tax Currency"))
    w.cbc(root, "PricingCurrencyCode", h.leaf("Pricing Currency"))
    w.cbc(root, "PaymentCurrencyCode", h.leaf("Payment Currency"))
    w.cbc(root, "AccountingCost", h.leaf("Accounting Cost"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.cbc(root, "BuyerReference", h.leaf("Buyer Reference"))
    w.period(root, "InvoicePeriod", h.get("Invoice Period"))
    w.discrepancy_response(root, c.get("Discrepancy Response"))
    w.order_reference(root, c.get("Order Reference"))
    w.billing_reference(root, c.get("Billing Reference"))
    w.docref(root, "DespatchDocumentReference", c.get("Despatch Document Reference", "Document Reference"))
    w.docref(root, "ReceiptDocumentReference", c.get("Receipt Document Reference", "Document Reference"))
    w.contract_reference(root, c.get("Contract"))
    w.docref(root, "AdditionalDocumentReference", c.get("Additional Document Reference", "Document Reference"))
    w.docref(root, "OriginatorDocumentReference", c.get("Originator Document Reference", "Document Reference"))
    w.supplier_party(root, "AccountingSupplierParty", c.get("Accounting Supplier Party", "Supplier Party"))
    w.required(root, "AccountingSupplierParty")
    w.customer_party(root, "AccountingCustomerParty", c.get("Accounting Customer Party", "Customer Party"))
    w.required(root, "AccountingCustomerParty")
    w.plain_party(root, "PayeeParty", c.get("Payee Party", "Party"))
    w.customer_party(root, "BuyerCustomerParty", c.get("Buyer Customer Party", "Customer Party"))
    w.supplier_party(root, "SellerSupplierParty", c.get("Seller Supplier Party", "Supplier Party"))
    w.plain_party(root, "TaxRepresentativeParty", c.get("Tax Representative Party", "Party"))
    w.delivery(root, c.get("Delivery"))
    w.delivery_terms(root, c.get("Delivery Terms"))
    w.payment_means(root, c.get("Payment Means Instruction"))
    w.payment_terms(root, c.get("Payment Terms"))
    w.allowance_charge(root, c.get("Allowance Charge"))
    w.tax_total(root, c.get("Tax Total"))
    w.tax_total_named(root, c.get("Withholding Tax Total", "Tax Total"), "WithholdingTaxTotal")
    w.monetary_total(root, c.get("Legal Monetary Total"), name="LegalMonetaryTotal")
    lines = c.get("Credit Note Lines") or Node("Credit Note Lines")
    for n in range(1, LINES + 1):
        w.credit_note_line(root, lines.get(f"Credit Note Line {n}", "Credit Note Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _CreditNoteWriter(_InvoiceWriter):
    def discrepancy_response(self, parent, node: Node | None):
        """The discrepancy the credit resolves, as UBL's Response: the reference, the response code, the description, the effective date."""
        if node is None:
            return
        el = self.cac(parent, "DiscrepancyResponse")
        self.cbc(el, "ReferenceID", node.leaf("Discrepancy Reference ID"))
        self.cbc(el, "ResponseCode", node.leaf("Discrepancy Response Code"))
        self.cbc(el, "Description", node.leaf("Discrepancy Description"))
        self.cbc(el, "EffectiveDate", node.leaf("Discrepancy Effective Date"))
        self.drop_if_empty(el)

    def credit_note_line(self, parent, node: Node | None):
        if node is None or node.leaf("Line ID") is None:
            return   # UBL requires the line's identifier
        cl = self.cac(parent, "CreditNoteLine")
        self.cbc(cl, "ID", node.leaf("Line ID"))
        self.cbc(cl, "Note", node.leaf("Note"))
        self.quantity(cl, "CreditedQuantity", node.leaf("Credited Quantity"))
        self.amount(cl, "LineExtensionAmount", node.leaf("Line Extension Amount"))   # UBL requires it; without it the document is not conformant, and says so
        self.amount(cl, "TaxInclusiveLineExtensionAmount", node.leaf("Tax Inclusive Line Extension Amount"))
        self.cbc(cl, "TaxPointDate", node.leaf("Tax Point Date"))
        self.cbc(cl, "AccountingCost", node.leaf("Accounting Cost"))
        self.bool(cl, "FreeOfChargeIndicator", node.leaf("Free of Charge"))
        self.period(cl, "InvoicePeriod", node.get("Invoice Period"))
        ref = node.get("Order Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:
            r = self.cac(cl, "OrderLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.cbc(r, "SalesOrderLineID", ref.leaf("Sales Order Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
        self.discrepancy_response(cl, node.get("Discrepancy Response"))
        self.line_reference(cl, "DespatchLineReference", node.get("Despatch Line Reference"))
        self.line_reference(cl, "ReceiptLineReference", node.get("Receipt Line Reference"))
        self.billing_reference(cl, node.get("Billing Reference"))
        self.docref(cl, "DocumentReference", node.get("Line Document Reference", "Document Reference"))
        self.tax_total(cl, node.get("Tax Total"))
        self.allowance_charge(cl, node.get("Allowance Charge"))
        self.item(cl, node.get("Item"))
        self.price(cl, node.get("Price"))


# ================================================================ reader
def read_credit_note(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 CreditNote by label path in the Credit Note model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{CREDIT_NOTE_NS}}}CreditNote", root.tag
    r = _CreditNoteReader()
    out = r.out
    h = CR + ("Credit Note Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Credit Note ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:DueDate", h + ("Due Date",))
    r.text(root, "cbc:TaxPointDate", h + ("Tax Point Date",))
    r.text(root, "cbc:CreditNoteTypeCode", h + ("Credit Note Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.text(root, "cbc:DocumentCurrencyCode", h + ("Document Currency",))
    r.currency = out.get("/".join(h + ("Document Currency",)))
    r.text(root, "cbc:TaxCurrencyCode", h + ("Tax Currency",))
    r.text(root, "cbc:PricingCurrencyCode", h + ("Pricing Currency",))
    r.text(root, "cbc:PaymentCurrencyCode", h + ("Payment Currency",))
    r.text(root, "cbc:AccountingCost", h + ("Accounting Cost",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.text(root, "cbc:BuyerReference", h + ("Buyer Reference",))
    r.period(root, "cac:InvoicePeriod", h + ("Invoice Period",))
    r.discrepancy_response(root, CR + ("Discrepancy Response",))
    r.order_reference(root, CR + ("Order Reference",))
    r.billing_reference(root, CR + ("Billing Reference",))
    r.docref(root, "cac:DespatchDocumentReference", CR + ("Despatch Document Reference", "Document Reference"))
    r.docref(root, "cac:ReceiptDocumentReference", CR + ("Receipt Document Reference", "Document Reference"))
    c = r.one(root, "cac:ContractDocumentReference")
    if c is not None:
        r.text(c, "cbc:ID", CR + ("Contract", "Contract ID"))
        r.text(c, "cbc:IssueDate", CR + ("Contract", "Contract Issue Date"))
        r.text(c, "cbc:DocumentType", CR + ("Contract", "Contract Type"))
    r.docref(root, "cac:AdditionalDocumentReference", CR + ("Additional Document Reference", "Document Reference"))
    r.docref(root, "cac:OriginatorDocumentReference", CR + ("Originator Document Reference", "Document Reference"))
    r.supplier_party(root, "cac:AccountingSupplierParty", CR + ("Accounting Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:AccountingCustomerParty", CR + ("Accounting Customer Party", "Customer Party"))
    r.party_from(r.one(root, "cac:PayeeParty"), CR + ("Payee Party", "Party"))
    r.customer_party(root, "cac:BuyerCustomerParty", CR + ("Buyer Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:SellerSupplierParty", CR + ("Seller Supplier Party", "Supplier Party"))
    r.party_from(r.one(root, "cac:TaxRepresentativeParty"), CR + ("Tax Representative Party", "Party"))
    r.delivery(r.one(root, "cac:Delivery"), CR + ("Delivery",))
    r.delivery_terms(root, CR + ("Delivery Terms",))
    r.payment_means(root, CR + ("Payment Means Instruction",))
    r.payment_terms(root, CR + ("Payment Terms",))
    r.allowance_charge(root, CR + ("Allowance Charge",))
    r.tax_total(root, CR + ("Tax Total",))
    r.tax_total_named(root, CR + ("Withholding Tax Total", "Tax Total"), "WithholdingTaxTotal")
    r.monetary_total(root, CR + ("Legal Monetary Total",), name="LegalMonetaryTotal")
    lines = root.findall("cac:CreditNoteLine", NS)
    assert len(lines) <= LINES, f"the Credit Note model carries {LINES} lines; the document has {len(lines)}"
    for n, cl in enumerate(lines, start=1):
        r.credit_note_line(cl, CR + ("Credit Note Lines", f"Credit Note Line {n}", "Credit Note Line"))
    return out


class _CreditNoteReader(_InvoiceReader):
    def discrepancy_response(self, el, to: tuple[str, ...]):
        d = self.one(el, "cac:DiscrepancyResponse")
        if d is not None:
            self.text(d, "cbc:ReferenceID", to + ("Discrepancy Reference ID",))
            self.text(d, "cbc:ResponseCode", to + ("Discrepancy Response Code",))
            self.text(d, "cbc:Description", to + ("Discrepancy Description",))
            self.text(d, "cbc:EffectiveDate", to + ("Discrepancy Effective Date",))

    def billing_reference(self, el, to: tuple[str, ...]):
        br = self.one(el, "cac:BillingReference")
        if br is not None:
            self.docref(br, "cac:InvoiceDocumentReference", to + ("Invoice Document Reference", "Document Reference"))

    def credit_note_line(self, cl, to: tuple[str, ...]):
        self.text(cl, "cbc:ID", to + ("Line ID",))
        self.text(cl, "cbc:Note", to + ("Note",))
        self.quantity(cl, "cbc:CreditedQuantity", to + ("Credited Quantity",))
        self.amount(cl, "cbc:LineExtensionAmount", to + ("Line Extension Amount",))
        self.amount(cl, "cbc:TaxInclusiveLineExtensionAmount", to + ("Tax Inclusive Line Extension Amount",))
        self.text(cl, "cbc:TaxPointDate", to + ("Tax Point Date",))
        self.text(cl, "cbc:AccountingCost", to + ("Accounting Cost",))
        self.bool(cl, "cbc:FreeOfChargeIndicator", to + ("Free of Charge",))
        self.period(cl, "cac:InvoicePeriod", to + ("Invoice Period",))
        ref = self.one(cl, "cac:OrderLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Order Line Reference", "Line ID"))
            self.text(ref, "cbc:SalesOrderLineID", to + ("Order Line Reference", "Sales Order Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Order Line Reference", "Line Status"))
        self.discrepancy_response(cl, to + ("Discrepancy Response",))
        self.line_reference(cl, "cac:DespatchLineReference", to + ("Despatch Line Reference",))
        self.line_reference(cl, "cac:ReceiptLineReference", to + ("Receipt Line Reference",))
        self.billing_reference(cl, to + ("Billing Reference",))
        self.docref(cl, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))
        self.tax_total(cl, to + ("Tax Total",))
        self.allowance_charge(cl, to + ("Allowance Charge",))
        self.item(cl, to + ("Item",))
        self.price(cl, to + ("Price",))


def projected_credit_note(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL CreditNote can carry: everything but NOT_PROJECTED, NOT_PROJECTED_UNDER and the header's document status."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        if len(parts) >= 2 and tuple(parts[-2:]) in NOT_PROJECTED_CREDIT_NOTE:
            continue
        out[path] = v
    return out
