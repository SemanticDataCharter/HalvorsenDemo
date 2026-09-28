"""
The OrderResponse's open projection: a conformant OASIS UBL 2.3 OrderResponse written from a governed record, and read into one.

    from ubl.order_response import write_order_response, read_order_response, validate_ubl_response
    ubl_xml = write_order_response(instance_xml)
    assert not validate_ubl_response(ubl_xml)
    values = read_order_response(ubl_xml)

The response composes the Order's components, so its writer and reader are the Order's with the
response's own parts added: the answer to the order as a whole (``cbc:OrderResponseCode``, this
library's token with ``listURI``), the reference to the order answered (``cac:OrderReference``), the
shipment totals, the transaction conditions, the legal monetary total, the accounting supplier party,
and on each line the order line reference, the seller's substituted and proposed substitute line
items, and the answer to the line. UBL has no element for a line's answer beside its status, so the
answer travels as the line item's ``cbc:LineStatusCode`` with ``listURI`` naming the library's
line-response component; a document written elsewhere with UBL's own status list reads back through
LINE_STATUS_TO_RESPONSE. The line item's own status is therefore not projected on a response line
(NOT_PROJECTED_RESPONSE), while the order line reference's status is.
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
from order import CAC, CBC, LIB, NOT_PROJECTED, NOT_PROJECTED_UNDER, NS, ROOT, UBL_VERSION, _Reader, _Writer  # noqa: E402
from schema import Schema  # noqa: E402

RESPONSE_CT = "kuntv2wlkw54h7nxe0kqhvi2"
RESPONSE_NS = "urn:oasis:names:specification:ubl:schema:xsd:OrderResponse-2"
NSMAP_RESPONSE = {None: RESPONSE_NS, "cac": CAC, "cbc": CBC}
UBL_RESPONSE_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-OrderResponse-2.3.xsd")
RR = ("Order Response Governed Record", "Order Response")
#: UBL's own line status values, read into the library's line response when a document did not use the library's list.
LINE_STATUS_TO_RESPONSE = {"NoStatus": "Accepted", "Revised": "Accepted with changes", "Cancelled": "Rejected"}
#: On a response line the line item's own status has no element of its own: the line's answer takes LineStatusCode.
NOT_PROJECTED_RESPONSE = {("Line Item", "Line Status")}


@lru_cache(maxsize=None)
def ubl_response_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_RESPONSE_XSD)


def validate_ubl_response(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 OrderResponse schema; empty when conformant."""
    return [str(e) for e in ubl_response_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_order_response(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(RESPONSE_CT))
    o = tree.get(*RR)
    assert o is not None, "no Order Response cluster in the instance"
    w = _ResponseWriter()
    root = etree.Element(f"{{{RESPONSE_NS}}}OrderResponse", nsmap=NSMAP_RESPONSE)
    h = o.get("Order Response Document") or Node("Order Response Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Order Response ID"))
    w.cbc(root, "SalesOrderID", h.leaf("Sales Order ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.token(root, "OrderResponseCode", h.leaf("Order Response Type"), "order-response-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.cbc(root, "DocumentCurrencyCode", h.leaf("Document Currency"))
    w.cbc(root, "PricingCurrencyCode", h.leaf("Pricing Currency"))
    totals = h.get("Response Shipment Totals") or Node("Response Shipment Totals")
    w.number(root, "TotalPackagesQuantity", totals.leaf("Total Packages Quantity"))
    w.quantity(root, "GrossWeightMeasure", totals.leaf("Gross Weight"), si=True)
    w.quantity(root, "NetWeightMeasure", totals.leaf("Net Weight"), si=True)
    w.quantity(root, "GrossVolumeMeasure", totals.leaf("Gross Volume"), si=True)
    w.quantity(root, "NetVolumeMeasure", totals.leaf("Net Volume"), si=True)
    w.cbc(root, "CustomerReference", h.leaf("Customer Reference"))
    w.cbc(root, "AccountingCost", h.leaf("Accounting Cost"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.period(root, "ValidityPeriod", h.get("Validity Period"))
    w.order_reference(root, o.get("Order Reference"))
    w.docref(root, "OrderDocumentReference", o.get("Order Document Reference", "Document Reference"))
    w.docref(root, "OrderChangeDocumentReference", o.get("Order Change Document Reference", "Document Reference"))
    w.docref(root, "OriginatorDocumentReference", o.get("Originator Document Reference", "Document Reference"))
    w.docref(root, "AdditionalDocumentReference", o.get("Additional Document Reference", "Document Reference"))
    w.contract(root, o.get("Contract"))
    w.supplier_party(root, "SellerSupplierParty", o.get("Seller Supplier Party", "Supplier Party"))
    w.customer_party(root, "BuyerCustomerParty", o.get("Buyer Customer Party", "Customer Party"))
    w.customer_party(root, "OriginatorCustomerParty", o.get("Originator Customer Party", "Customer Party"))
    w.supplier_party(root, "AccountingSupplierParty", o.get("Accounting Supplier Party", "Supplier Party"))
    w.customer_party(root, "AccountingCustomerParty", o.get("Accounting Customer Party", "Customer Party"))
    w.delivery(root, o.get("Delivery"))
    w.delivery_terms(root, o.get("Delivery Terms"))
    w.payment_means(root, o.get("Payment Means Instruction"))
    w.payment_terms(root, o.get("Payment Terms"))
    w.allowance_charge(root, o.get("Allowance Charge"))
    w.transaction_conditions(root, o.get("Transaction Conditions"))
    w.tax_total(root, o.get("Tax Total"))
    w.monetary_total(root, o.get("Legal Monetary Total"), name="LegalMonetaryTotal")
    lines = o.get("Order Response Lines") or Node("Order Response Lines")
    for n in range(1, 11):
        w.response_line(root, lines.get(f"Order Response Line {n}", "Order Response Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _ResponseWriter(_Writer):
    def order_reference(self, parent, node: Node | None):
        """The order answered. UBL requires one; a response with no order reference is not a response."""
        if node is None or node.leaf("Order ID") is None:
            return
        el = self.cac(parent, "OrderReference")
        self.cbc(el, "ID", node.leaf("Order ID"))
        self.cbc(el, "SalesOrderID", node.leaf("Sales Order ID"))
        self.cbc(el, "UUID", node.leaf("Document UUID"))
        self.cbc(el, "IssueDate", node.leaf("Issue Date"))
        self.token(el, "OrderTypeCode", node.leaf("Order Type"), "order-type")

    def transaction_conditions(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "TransactionConditions")
        self.cbc(el, "ID", node.leaf("Transaction Conditions ID"))
        self.cbc(el, "Description", node.leaf("Transaction Conditions Description"))
        self.docref(el, "DocumentReference", node.get("Document Reference"))
        self.drop_if_empty(el)

    def response_line(self, parent, node: Node | None):
        if node is None:
            return
        li = node.get("Line Item")
        if li is None or li.leaf("Line ID") is None:
            return   # UBL requires the line item and its identifier
        ol = self.cac(parent, "OrderLine")
        # the line's answer travels as its status, in this library's list
        self.line_item(ol, "LineItem", li, status=node.leaf("Line Response"), status_key="line-response")
        self.line_item(ol, "SellerProposedSubstituteLineItem", node.get("Seller Proposed Substitute Line Item", "Line Item"))
        self.line_item(ol, "SellerSubstitutedLineItem", node.get("Seller Substituted Line Item", "Line Item"))
        ref = node.get("Order Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:
            r = self.cac(ol, "OrderLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.cbc(r, "SalesOrderLineID", ref.leaf("Sales Order Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
        self.docref(ol, "DocumentReference", node.get("Line Document Reference", "Document Reference"))


# ================================================================ reader
def read_order_response(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 OrderResponse by label path in the Order Response model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{RESPONSE_NS}}}OrderResponse", root.tag
    r = _ResponseReader()
    out = r.out
    h = RR + ("Order Response Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Order Response ID",))
    r.text(root, "cbc:SalesOrderID", h + ("Sales Order ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:OrderResponseCode", h + ("Order Response Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.text(root, "cbc:DocumentCurrencyCode", h + ("Document Currency",))
    r.currency = out.get("/".join(h + ("Document Currency",)))
    r.text(root, "cbc:PricingCurrencyCode", h + ("Pricing Currency",))
    t = h + ("Response Shipment Totals",)
    r.number(root, "cbc:TotalPackagesQuantity", t + ("Total Packages Quantity",), "count")
    r.quantity(root, "cbc:GrossWeightMeasure", t + ("Gross Weight",), si=True)
    r.quantity(root, "cbc:NetWeightMeasure", t + ("Net Weight",), si=True)
    r.quantity(root, "cbc:GrossVolumeMeasure", t + ("Gross Volume",), si=True)
    r.quantity(root, "cbc:NetVolumeMeasure", t + ("Net Volume",), si=True)
    r.text(root, "cbc:CustomerReference", h + ("Customer Reference",))
    r.text(root, "cbc:AccountingCost", h + ("Accounting Cost",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.period(root, "cac:ValidityPeriod", h + ("Validity Period",))
    r.order_reference(root, RR + ("Order Reference",))
    r.docref(root, "cac:OrderDocumentReference", RR + ("Order Document Reference", "Document Reference"))
    r.docref(root, "cac:OrderChangeDocumentReference", RR + ("Order Change Document Reference", "Document Reference"))
    r.docref(root, "cac:OriginatorDocumentReference", RR + ("Originator Document Reference", "Document Reference"))
    r.docref(root, "cac:AdditionalDocumentReference", RR + ("Additional Document Reference", "Document Reference"))
    r.contract(root, RR + ("Contract",))
    r.supplier_party(root, "cac:SellerSupplierParty", RR + ("Seller Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:BuyerCustomerParty", RR + ("Buyer Customer Party", "Customer Party"))
    r.customer_party(root, "cac:OriginatorCustomerParty", RR + ("Originator Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:AccountingSupplierParty", RR + ("Accounting Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:AccountingCustomerParty", RR + ("Accounting Customer Party", "Customer Party"))
    r.delivery(r.one(root, "cac:Delivery"), RR + ("Delivery",))
    r.delivery_terms(root, RR + ("Delivery Terms",))
    r.payment_means(root, RR + ("Payment Means Instruction",))
    r.payment_terms(root, RR + ("Payment Terms",))
    r.allowance_charge(root, RR + ("Allowance Charge",))
    r.transaction_conditions(root, RR + ("Transaction Conditions",))
    r.tax_total(root, RR + ("Tax Total",))
    r.monetary_total(root, RR + ("Legal Monetary Total",), name="LegalMonetaryTotal")
    lines = root.findall("cac:OrderLine", NS)
    assert len(lines) <= 10, f"the Order Response model carries ten lines; the document has {len(lines)}"
    for n, ol in enumerate(lines, start=1):
        r.response_line(ol, RR + ("Order Response Lines", f"Order Response Line {n}", "Order Response Line"))
    return out


class _ResponseReader(_Reader):
    def order_reference(self, el, to: tuple[str, ...]):
        ref = self.one(el, "cac:OrderReference")
        if ref is not None:
            self.text(ref, "cbc:ID", to + ("Order ID",))
            self.text(ref, "cbc:SalesOrderID", to + ("Sales Order ID",))
            self.text(ref, "cbc:UUID", to + ("Document UUID",))
            self.text(ref, "cbc:IssueDate", to + ("Issue Date",))
            self.text(ref, "cbc:OrderTypeCode", to + ("Order Type",))

    def transaction_conditions(self, el, to: tuple[str, ...]):
        tc = self.one(el, "cac:TransactionConditions")
        if tc is not None:
            self.text(tc, "cbc:ID", to + ("Transaction Conditions ID",))
            self.text(tc, "cbc:Description", to + ("Transaction Conditions Description",))
            self.docref(tc, "cac:DocumentReference", to + ("Document Reference",))

    def response_line(self, ol, to: tuple[str, ...]):
        li = self.one(ol, "cac:LineItem")
        self.line_item_from(li, to + ("Line Item",), status_to=to + ("Line Response",))
        answer = self.out.get("/".join(to + ("Line Response",)))
        if answer in LINE_STATUS_TO_RESPONSE:   # a document written with UBL's own list rather than the library's
            self.out["/".join(to + ("Line Response",))] = LINE_STATUS_TO_RESPONSE[answer]
        self.line_item_from(self.one(ol, "cac:SellerProposedSubstituteLineItem"), to + ("Seller Proposed Substitute Line Item", "Line Item"))
        self.line_item_from(self.one(ol, "cac:SellerSubstitutedLineItem"), to + ("Seller Substituted Line Item", "Line Item"))
        ref = self.one(ol, "cac:OrderLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Order Line Reference", "Line ID"))
            self.text(ref, "cbc:SalesOrderLineID", to + ("Order Line Reference", "Sales Order Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Order Line Reference", "Line Status"))
        self.docref(ol, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))


def projected_response(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL OrderResponse can carry: everything but NOT_PROJECTED, NOT_PROJECTED_UNDER and the response line item's own status."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        if len(parts) >= 3 and tuple(parts[-2:]) in NOT_PROJECTED_RESPONSE and "Order Response Line" in parts and parts[-3] == "Order Response Line":
            continue
        out[path] = v
    return out
