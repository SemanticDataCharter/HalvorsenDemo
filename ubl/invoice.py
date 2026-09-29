"""
The Invoice's open projection: a conformant OASIS UBL 2.3 Invoice written from a governed record, and read into one.

    from ubl.invoice import write_invoice, read_invoice, validate_ubl_invoice
    ubl_xml = write_invoice(instance_xml)
    assert not validate_ubl_invoice(ubl_xml)
    values = read_invoice(ubl_xml)

The invoice composes the Order's parties, delivery, payment means and terms, allowances and charges, tax total and
monetary total, the OrderResponse's accounting parties and order reference, and the DispatchAdvice's and
ReceiptAdvice's document and line references, so its writer and reader are those with the invoice's own parts
added. The invoice type is this library's token with ``listURI``; the earlier invoice is ``cac:BillingReference/cac:InvoiceDocumentReference``;
the dispatch and the receipt settled are ``cac:DespatchDocumentReference`` and ``cac:ReceiptDocumentReference``;
the contract is ``cac:ContractDocumentReference`` (its identifier, issue date and type); the payee and the tax
representative are parties; a prepaid payment is ``cac:PrepaidPayment``; the withholding tax total is
``cac:WithholdingTaxTotal``; each line's order, dispatch and receipt line references are UBL's own. Two leaves of
every party have no home in a UBL Contact (NOT_PROJECTED, from the Order), and UBL's Invoice carries no document
status, so the header's Document Status is left out and named (NOT_PROJECTED_INVOICE); nothing else is.
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
from order import CAC, CBC, NOT_PROJECTED, NOT_PROJECTED_UNDER, NS, ROOT, UBL_VERSION  # noqa: E402
from order_response import _ResponseReader, _ResponseWriter  # noqa: E402
from schema import Schema  # noqa: E402

INVOICE_CT = "u19w614300a8ot4a7qnn2o1c"
INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NSMAP_INVOICE = {None: INVOICE_NS, "cac": CAC, "cbc": CBC}
UBL_INVOICE_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-Invoice-2.3.xsd")
IR = ("Invoice Governed Record", "Invoice")
#: UBL's Invoice has no DocumentStatusCode: the header's status has no home in the document.
NOT_PROJECTED_INVOICE = {("Invoice Document", "Document Status")}
LINES = 10


@lru_cache(maxsize=None)
def ubl_invoice_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_INVOICE_XSD)


def validate_ubl_invoice(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 Invoice schema; empty when conformant."""
    return [str(e) for e in ubl_invoice_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_invoice(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(INVOICE_CT))
    i = tree.get(*IR)
    assert i is not None, "no Invoice cluster in the instance"
    w = _InvoiceWriter()
    root = etree.Element(f"{{{INVOICE_NS}}}Invoice", nsmap=NSMAP_INVOICE)
    h = i.get("Invoice Document") or Node("Invoice Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Invoice ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.cbc(root, "DueDate", h.leaf("Due Date"))
    w.token(root, "InvoiceTypeCode", h.leaf("Invoice Type"), "invoice-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.cbc(root, "TaxPointDate", h.leaf("Tax Point Date"))
    w.cbc(root, "DocumentCurrencyCode", h.leaf("Document Currency"))
    w.cbc(root, "TaxCurrencyCode", h.leaf("Tax Currency"))
    w.cbc(root, "PricingCurrencyCode", h.leaf("Pricing Currency"))
    w.cbc(root, "PaymentCurrencyCode", h.leaf("Payment Currency"))
    w.cbc(root, "AccountingCost", h.leaf("Accounting Cost"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.cbc(root, "BuyerReference", h.leaf("Buyer Reference"))
    w.period(root, "InvoicePeriod", h.get("Invoice Period"))
    w.order_reference(root, i.get("Order Reference"))
    w.billing_reference(root, i.get("Billing Reference"))
    w.docref(root, "DespatchDocumentReference", i.get("Despatch Document Reference", "Document Reference"))
    w.docref(root, "ReceiptDocumentReference", i.get("Receipt Document Reference", "Document Reference"))
    w.docref(root, "OriginatorDocumentReference", i.get("Originator Document Reference", "Document Reference"))
    w.contract_reference(root, i.get("Contract"))
    w.docref(root, "AdditionalDocumentReference", i.get("Additional Document Reference", "Document Reference"))
    # UBL requires the accounting supplier and customer, every member optional: present even when the record has none
    w.supplier_party(root, "AccountingSupplierParty", i.get("Accounting Supplier Party", "Supplier Party"))
    w.required(root, "AccountingSupplierParty")
    w.customer_party(root, "AccountingCustomerParty", i.get("Accounting Customer Party", "Customer Party"))
    w.required(root, "AccountingCustomerParty")
    w.plain_party(root, "PayeeParty", i.get("Payee Party", "Party"))
    w.customer_party(root, "BuyerCustomerParty", i.get("Buyer Customer Party", "Customer Party"))
    w.supplier_party(root, "SellerSupplierParty", i.get("Seller Supplier Party", "Supplier Party"))
    w.plain_party(root, "TaxRepresentativeParty", i.get("Tax Representative Party", "Party"))
    w.delivery(root, i.get("Delivery"))
    w.delivery_terms(root, i.get("Delivery Terms"))
    w.payment_means(root, i.get("Payment Means Instruction"))
    w.payment_terms(root, i.get("Payment Terms"))
    w.prepaid_payment(root, i.get("Prepaid Payment"))
    w.allowance_charge(root, i.get("Allowance Charge"))
    w.tax_total(root, i.get("Tax Total"))
    w.tax_total_named(root, i.get("Withholding Tax Total", "Tax Total"), "WithholdingTaxTotal")
    w.monetary_total(root, i.get("Legal Monetary Total"), name="LegalMonetaryTotal")
    lines = i.get("Invoice Lines") or Node("Invoice Lines")
    for n in range(1, LINES + 1):
        w.invoice_line(root, lines.get(f"Invoice Line {n}", "Invoice Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _InvoiceWriter(_ResponseWriter):
    def required(self, parent, name: str):
        """An aggregate UBL requires, empty when the record has nothing for it (every member of the two parties is optional)."""
        if parent.find(f"cac:{name}", NS) is None:
            self.cac(parent, name)

    def plain_party(self, parent, name: str, node: Node | None):
        """A party that is UBL's PartyType itself (the payee, the tax representative)."""
        if node is None:
            return
        el = self.cac(parent, name)
        self.party_into(el, node)
        self.drop_if_empty(el)

    def billing_reference(self, parent, node: Node | None):
        ref = None if node is None else node.get("Invoice Document Reference", "Document Reference")
        if ref is None or ref.leaf("Document Reference ID") is None:
            return
        el = self.cac(parent, "BillingReference")
        self.docref(el, "InvoiceDocumentReference", ref)

    def contract_reference(self, parent, node: Node | None):
        """The contract as UBL's ContractDocumentReference: the identifier, the issue date, and the type as the document type text."""
        if node is None or node.leaf("Contract ID") is None:
            return
        el = self.cac(parent, "ContractDocumentReference")
        self.cbc(el, "ID", node.leaf("Contract ID"))
        self.cbc(el, "IssueDate", node.leaf("Contract Issue Date"))
        self.cbc(el, "DocumentType", node.leaf("Contract Type"))

    def prepaid_payment(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "PrepaidPayment")
        self.cbc(el, "ID", node.leaf("Payment ID"))
        self.amount(el, "PaidAmount", node.leaf("Paid Amount"))
        self.cbc(el, "ReceivedDate", node.leaf("Payment Received Date"))
        self.cbc(el, "PaidDate", node.leaf("Paid Date"))
        self.cbc(el, "InstructionID", node.leaf("Payment Instruction ID"))
        self.drop_if_empty(el)

    def tax_total_named(self, parent, node: Node | None, name: str):
        """A tax total under another element name (UBL's WithholdingTaxTotal is a TaxTotal)."""
        if node is None or node.leaf("Tax Amount") is None:
            return
        el = self.cac(parent, name)
        self.amount(el, "TaxAmount", node.leaf("Tax Amount"))
        sub = node.get("Tax Subtotal")
        if sub is not None and sub.leaf("Tax Amount") is not None:
            s = self.cac(el, "TaxSubtotal")
            self.amount(s, "TaxableAmount", sub.leaf("Taxable Amount"))
            self.amount(s, "TaxAmount", sub.leaf("Tax Amount"))
            self.tax_category(s, "TaxCategory", sub.get("Tax Category") or Node("Tax Category"))

    def line_reference(self, parent, name: str, node: Node | None):
        """A UBL LineReference (the dispatch or receipt line settled): its identifier, its status, and the document it belongs to."""
        if node is None or node.leaf("Line ID") is None:
            return
        r = self.cac(parent, name)
        self.cbc(r, "LineID", node.leaf("Line ID"))
        self.token(r, "LineStatusCode", node.leaf("Line Status"), "line-status")
        self.docref(r, "DocumentReference", node.get("Document Reference"))

    def invoice_line(self, parent, node: Node | None):
        if node is None or node.leaf("Line ID") is None:
            return   # UBL requires the line's identifier
        il = self.cac(parent, "InvoiceLine")
        self.cbc(il, "ID", node.leaf("Line ID"))
        self.cbc(il, "Note", node.leaf("Note"))
        self.quantity(il, "InvoicedQuantity", node.leaf("Invoiced Quantity"))
        self.amount(il, "LineExtensionAmount", node.leaf("Line Extension Amount"))   # UBL requires it; without it the document is not conformant, and says so
        self.amount(il, "TaxInclusiveLineExtensionAmount", node.leaf("Tax Inclusive Line Extension Amount"))
        self.cbc(il, "TaxPointDate", node.leaf("Tax Point Date"))
        self.cbc(il, "AccountingCost", node.leaf("Accounting Cost"))
        self.bool(il, "FreeOfChargeIndicator", node.leaf("Free of Charge"))
        self.period(il, "InvoicePeriod", node.get("Invoice Period"))
        ref = node.get("Order Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:
            r = self.cac(il, "OrderLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.cbc(r, "SalesOrderLineID", ref.leaf("Sales Order Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
        self.line_reference(il, "DespatchLineReference", node.get("Despatch Line Reference"))
        self.line_reference(il, "ReceiptLineReference", node.get("Receipt Line Reference"))
        self.docref(il, "DocumentReference", node.get("Line Document Reference", "Document Reference"))
        self.allowance_charge(il, node.get("Allowance Charge"))
        self.tax_total(il, node.get("Tax Total"))
        self.item(il, node.get("Item"))
        self.price(il, node.get("Price"))


# ================================================================ reader
def read_invoice(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 Invoice by label path in the Invoice model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{INVOICE_NS}}}Invoice", root.tag
    r = _InvoiceReader()
    out = r.out
    h = IR + ("Invoice Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Invoice ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:DueDate", h + ("Due Date",))
    r.text(root, "cbc:InvoiceTypeCode", h + ("Invoice Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.text(root, "cbc:TaxPointDate", h + ("Tax Point Date",))
    r.text(root, "cbc:DocumentCurrencyCode", h + ("Document Currency",))
    r.currency = out.get("/".join(h + ("Document Currency",)))
    r.text(root, "cbc:TaxCurrencyCode", h + ("Tax Currency",))
    r.text(root, "cbc:PricingCurrencyCode", h + ("Pricing Currency",))
    r.text(root, "cbc:PaymentCurrencyCode", h + ("Payment Currency",))
    r.text(root, "cbc:AccountingCost", h + ("Accounting Cost",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.text(root, "cbc:BuyerReference", h + ("Buyer Reference",))
    r.period(root, "cac:InvoicePeriod", h + ("Invoice Period",))
    r.order_reference(root, IR + ("Order Reference",))
    br = r.one(root, "cac:BillingReference")
    if br is not None:
        r.docref(br, "cac:InvoiceDocumentReference", IR + ("Billing Reference", "Invoice Document Reference", "Document Reference"))
    r.docref(root, "cac:DespatchDocumentReference", IR + ("Despatch Document Reference", "Document Reference"))
    r.docref(root, "cac:ReceiptDocumentReference", IR + ("Receipt Document Reference", "Document Reference"))
    r.docref(root, "cac:OriginatorDocumentReference", IR + ("Originator Document Reference", "Document Reference"))
    c = r.one(root, "cac:ContractDocumentReference")
    if c is not None:
        r.text(c, "cbc:ID", IR + ("Contract", "Contract ID"))
        r.text(c, "cbc:IssueDate", IR + ("Contract", "Contract Issue Date"))
        r.text(c, "cbc:DocumentType", IR + ("Contract", "Contract Type"))
    r.docref(root, "cac:AdditionalDocumentReference", IR + ("Additional Document Reference", "Document Reference"))
    r.supplier_party(root, "cac:AccountingSupplierParty", IR + ("Accounting Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:AccountingCustomerParty", IR + ("Accounting Customer Party", "Customer Party"))
    r.party_from(r.one(root, "cac:PayeeParty"), IR + ("Payee Party", "Party"))
    r.customer_party(root, "cac:BuyerCustomerParty", IR + ("Buyer Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:SellerSupplierParty", IR + ("Seller Supplier Party", "Supplier Party"))
    r.party_from(r.one(root, "cac:TaxRepresentativeParty"), IR + ("Tax Representative Party", "Party"))
    r.delivery(r.one(root, "cac:Delivery"), IR + ("Delivery",))
    r.delivery_terms(root, IR + ("Delivery Terms",))
    r.payment_means(root, IR + ("Payment Means Instruction",))
    r.payment_terms(root, IR + ("Payment Terms",))
    pp = r.one(root, "cac:PrepaidPayment")
    if pp is not None:
        r.text(pp, "cbc:ID", IR + ("Prepaid Payment", "Payment ID"))
        r.amount(pp, "cbc:PaidAmount", IR + ("Prepaid Payment", "Paid Amount"))
        r.text(pp, "cbc:ReceivedDate", IR + ("Prepaid Payment", "Payment Received Date"))
        r.text(pp, "cbc:PaidDate", IR + ("Prepaid Payment", "Paid Date"))
        r.text(pp, "cbc:InstructionID", IR + ("Prepaid Payment", "Payment Instruction ID"))
    r.allowance_charge(root, IR + ("Allowance Charge",))
    r.tax_total(root, IR + ("Tax Total",))
    r.tax_total_named(root, IR + ("Withholding Tax Total", "Tax Total"), "WithholdingTaxTotal")
    r.monetary_total(root, IR + ("Legal Monetary Total",), name="LegalMonetaryTotal")
    lines = root.findall("cac:InvoiceLine", NS)
    assert len(lines) <= LINES, f"the Invoice model carries {LINES} lines; the document has {len(lines)}"
    for n, il in enumerate(lines, start=1):
        r.invoice_line(il, IR + ("Invoice Lines", f"Invoice Line {n}", "Invoice Line"))
    return out


class _InvoiceReader(_ResponseReader):
    def tax_total_named(self, el, to: tuple[str, ...], name: str):
        tt = self.one(el, f"cac:{name}")
        if tt is not None:
            self.amount(tt, "cbc:TaxAmount", to + ("Tax Amount",))
            st = self.one(tt, "cac:TaxSubtotal")
            if st is not None:
                self.amount(st, "cbc:TaxableAmount", to + ("Tax Subtotal", "Taxable Amount"))
                self.amount(st, "cbc:TaxAmount", to + ("Tax Subtotal", "Tax Amount"))
                self.tax_category(st, "cac:TaxCategory", to + ("Tax Subtotal", "Tax Category"))

    def line_reference(self, el, path: str, to: tuple[str, ...]):
        ref = self.one(el, path)
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Line ID",))
            self.text(ref, "cbc:LineStatusCode", to + ("Line Status",))
            self.docref(ref, "cac:DocumentReference", to + ("Document Reference",))

    def invoice_line(self, il, to: tuple[str, ...]):
        self.text(il, "cbc:ID", to + ("Line ID",))
        self.text(il, "cbc:Note", to + ("Note",))
        self.quantity(il, "cbc:InvoicedQuantity", to + ("Invoiced Quantity",))
        self.amount(il, "cbc:LineExtensionAmount", to + ("Line Extension Amount",))
        self.amount(il, "cbc:TaxInclusiveLineExtensionAmount", to + ("Tax Inclusive Line Extension Amount",))
        self.text(il, "cbc:TaxPointDate", to + ("Tax Point Date",))
        self.text(il, "cbc:AccountingCost", to + ("Accounting Cost",))
        self.bool(il, "cbc:FreeOfChargeIndicator", to + ("Free of Charge",))
        self.period(il, "cac:InvoicePeriod", to + ("Invoice Period",))
        ref = self.one(il, "cac:OrderLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Order Line Reference", "Line ID"))
            self.text(ref, "cbc:SalesOrderLineID", to + ("Order Line Reference", "Sales Order Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Order Line Reference", "Line Status"))
        self.line_reference(il, "cac:DespatchLineReference", to + ("Despatch Line Reference",))
        self.line_reference(il, "cac:ReceiptLineReference", to + ("Receipt Line Reference",))
        self.docref(il, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))
        self.allowance_charge(il, to + ("Allowance Charge",))
        self.tax_total(il, to + ("Tax Total",))
        self.item(il, to + ("Item",))
        self.price(il, to + ("Price",))


def projected_invoice(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL Invoice can carry: everything but NOT_PROJECTED, NOT_PROJECTED_UNDER and the header's document status."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        if len(parts) >= 2 and tuple(parts[-2:]) in NOT_PROJECTED_INVOICE:
            continue
        out[path] = v
    return out
