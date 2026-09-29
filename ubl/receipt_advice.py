"""
The ReceiptAdvice's open projection: a conformant OASIS UBL 2.3 ReceiptAdvice written from a governed record, and read into one.

    from ubl.receipt_advice import write_receipt_advice, read_receipt_advice, validate_ubl_receipt
    ubl_xml = write_receipt_advice(instance_xml)
    assert not validate_ubl_receipt(ubl_xml)
    values = read_receipt_advice(ubl_xml)

The receipt advice composes the Order's parties and delivery, the DespatchAdvice's shipment, consignment and
handling unit, so its writer and reader are those with the receipt's own parts added: the dispatch advice
answered (``cac:DespatchDocumentReference``), the shipment as received with the actual delivery date and time
on the delivery, each handling unit as received, and the receipt lines. Where the record names something UBL
has no element for, the projection says where it went:

- Each received unit is a ``cac:TransportHandlingUnit`` with the SSCC, the pallet as ``cac:TransportEquipment``
  with its identifier's validity period (as the DespatchAdvice writes it), and two ``cac:ShipmentDocumentReference``s:
  the pack specification version the unit was packed to (type ``Pack specification``) and the version in force on
  the receipt date (type ``Pack specification in force``).
- The receiver's decision on the unit is a ``cac:Status``: the receiving condition as ``cbc:ConditionCode`` (this
  library's token with ``listURI``), the received date and time as the reference date and time, the exception as
  the description. Each check the receiver made on the receipt date (the pallet identifier within its period, the
  pack specification compliant) is a further ``cac:Status`` whose description names the library component and
  whose ``cbc:IndicationIndicator`` carries the yes or no. The verdict's facts, in the document.
- A receipt line's quantities, codes, dates and references map one to one onto UBL's ReceiptLine; the codes are
  this library's tokens with ``listURI``, as every token of the library travels.

Two leaves of every party have no home in a UBL Contact (NOT_PROJECTED, from the Order); nothing else of the
record is left out.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any

from lxml import etree

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "datagen"))
from dispatch_advice import PACK_SPECIFICATION_DOCUMENT, SSCC, UNITS, _DispatchReader, _DispatchWriter  # noqa: E402
from instance import Node, read_tree  # noqa: E402
from order import CAC, CBC, LIB, NOT_PROJECTED, NOT_PROJECTED_UNDER, NS, ROOT, UBL_VERSION  # noqa: E402
from schema import Schema  # noqa: E402

RECEIPT_CT = "tog0v0p1zit1xwpxysxwpf3d"
RECEIPT_NS = "urn:oasis:names:specification:ubl:schema:xsd:ReceiptAdvice-2"
NSMAP_RECEIPT = {None: RECEIPT_NS, "cac": CAC, "cbc": CBC}
UBL_RECEIPT_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-ReceiptAdvice-2.3.xsd")
KR = ("Receipt Advice Governed Record", "Receipt Advice")
PACK_IN_FORCE_DOCUMENT = "Pack specification in force"
#: The checks a received unit carries as a Status with an indication: the record's label and the library component the status names.
CHECKS = (("Pallet ID Valid on Receipt", LIB + "pallet-id-valid-on-receipt"), ("Pack Specification Compliant", LIB + "pack-specification-compliant"))
LINES = 10


@lru_cache(maxsize=None)
def ubl_receipt_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_RECEIPT_XSD)


def validate_ubl_receipt(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 ReceiptAdvice schema; empty when conformant."""
    return [str(e) for e in ubl_receipt_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_receipt_advice(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(RECEIPT_CT))
    k = tree.get(*KR)
    assert k is not None, "no Receipt Advice cluster in the instance"
    w = _ReceiptWriter()
    root = etree.Element(f"{{{RECEIPT_NS}}}ReceiptAdvice", nsmap=NSMAP_RECEIPT)
    h = k.get("Receipt Advice Document") or Node("Receipt Advice Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Receipt Advice ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.token(root, "DocumentStatusCode", h.leaf("Document Status"), "document-status")
    w.token(root, "ReceiptAdviceTypeCode", h.leaf("Receipt Advice Type"), "receipt-advice-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.order_reference(root, k.get("Order Reference"))
    w.docref(root, "DespatchDocumentReference", k.get("Despatch Document Reference", "Document Reference"))
    # UBL requires the delivery customer and the dispatching supplier, every member optional: present even when the record has none
    w.customer_party(root, "DeliveryCustomerParty", k.get("Delivery Customer Party", "Customer Party"))
    w.required(root, "DeliveryCustomerParty")
    w.supplier_party(root, "DespatchSupplierParty", k.get("Despatch Supplier Party", "Supplier Party"))
    w.required(root, "DespatchSupplierParty")
    w.customer_party(root, "BuyerCustomerParty", k.get("Buyer Customer Party", "Customer Party"))
    w.supplier_party(root, "SellerSupplierParty", k.get("Seller Supplier Party", "Supplier Party"))
    w.receipt_shipment(root, k.get("Receipt Shipment"))
    lines = k.get("Receipt Lines") or Node("Receipt Lines")
    for n in range(1, LINES + 1):
        w.receipt_line(root, lines.get(f"Receipt Line {n}", "Receipt Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _ReceiptWriter(_DispatchWriter):
    def receipt_shipment(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "Shipment")
        self.cbc(el, "ID", node.leaf("Shipment ID"))
        self.consignment(el, node.get("Consignment"))
        self.received_delivery(el, node.get("Delivery"), node.leaf("Actual Delivery Date"), node.leaf("Actual Delivery Time"))
        units = node.get("Received Handling Units") or Node("Received Handling Units")
        for n in range(1, UNITS + 1):
            self.received_unit(el, units.get(f"Received Handling Unit {n}", "Received Handling Unit"))
        self.drop_if_empty(el)

    def received_delivery(self, parent, node: Node | None, actual_date, actual_time):
        """The delivery as arranged, with the date and time it actually arrived (UBL's ActualDeliveryDate and ActualDeliveryTime sit between the quantity and the latest date)."""
        if node is None and actual_date is None and actual_time is None:
            return
        node = node or Node("Delivery")
        el = self.cac(parent, "Delivery")
        self.cbc(el, "ID", node.leaf("Delivery ID"))
        self.quantity(el, "Quantity", node.leaf("Delivery Quantity"))
        self.cbc(el, "ActualDeliveryDate", actual_date)
        self.cbc(el, "ActualDeliveryTime", actual_time)
        self.cbc(el, "LatestDeliveryDate", node.leaf("Latest Delivery Date"))
        self.location(el, "DeliveryLocation", node.get("Delivery Location"))
        self.period(el, "RequestedDeliveryPeriod", node.get("Requested Delivery Period"))
        if node.get("Delivery Party", "Party") is not None:
            dp = self.cac(el, "DeliveryParty")
            self.party_into(dp, node.get("Delivery Party", "Party"))
            self.drop_if_empty(dp)
        self.drop_if_empty(el)

    def received_unit(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "TransportHandlingUnit")
        self.cbc(el, "ID", node.leaf("Transport Handling Unit ID"), schemeID=SSCC[0], schemeAgencyID=SSCC[1], schemeName=SSCC[2])
        self.pallet_equipment(el, node.get("Pallet Identification"))
        self.unit_document(el, node.leaf("Pack Specification Version"), PACK_SPECIFICATION_DOCUMENT)
        self.unit_document(el, node.leaf("Pack Specification in Force"), PACK_IN_FORCE_DOCUMENT)
        if any(node.leaf(x) is not None for x in ("Receiving Condition", "Received Date", "Received Time", "Exception Description")):
            st = self.cac(el, "Status")
            self.token(st, "ConditionCode", node.leaf("Receiving Condition"), "receiving-condition")
            self.cbc(st, "ReferenceDate", node.leaf("Received Date"))
            self.cbc(st, "ReferenceTime", node.leaf("Received Time"))
            self.cbc(st, "Description", node.leaf("Exception Description"))
        for label, component in CHECKS:
            if node.leaf(label) is not None:
                st = self.cac(el, "Status")
                self.cbc(st, "Description", component)
                self.bool(st, "IndicationIndicator", node.leaf(label))
        self.drop_if_empty(el)

    def receipt_line(self, parent, node: Node | None):
        if node is None or node.leaf("Line ID") is None:
            return   # UBL requires the line's identifier
        rl = self.cac(parent, "ReceiptLine")
        self.cbc(rl, "ID", node.leaf("Line ID"))
        self.cbc(rl, "Note", node.leaf("Note"))
        self.quantity(rl, "ReceivedQuantity", node.leaf("Received Quantity"))
        self.quantity(rl, "ShortQuantity", node.leaf("Short Quantity"))
        self.token(rl, "ShortageActionCode", node.leaf("Shortage Action"), "shortage-action")
        self.quantity(rl, "RejectedQuantity", node.leaf("Rejected Quantity"))
        self.token(rl, "RejectReasonCode", node.leaf("Reject Reason"), "reject-reason")
        self.cbc(rl, "RejectReason", node.leaf("Reject Reason Description"))
        self.token(rl, "RejectActionCode", node.leaf("Reject Action"), "reject-action")
        self.token(rl, "QuantityDiscrepancyCode", node.leaf("Quantity Discrepancy"), "quantity-discrepancy")
        self.quantity(rl, "OversupplyQuantity", node.leaf("Oversupply Quantity"))
        self.cbc(rl, "ReceivedDate", node.leaf("Received Date"))
        self.token(rl, "TimingComplaintCode", node.leaf("Timing Complaint"), "timing-complaint")
        self.cbc(rl, "TimingComplaint", node.leaf("Timing Complaint Description"))
        ref = node.get("Order Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:
            r = self.cac(rl, "OrderLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.cbc(r, "SalesOrderLineID", ref.leaf("Sales Order Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
        ref = node.get("Despatch Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:
            r = self.cac(rl, "DespatchLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
            self.docref(r, "DocumentReference", ref.get("Document Reference"))
        if node.get("Item") is not None:
            self.item(rl, node.get("Item"))


# ================================================================ reader
def read_receipt_advice(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 ReceiptAdvice by label path in the Receipt Advice model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{RECEIPT_NS}}}ReceiptAdvice", root.tag
    r = _ReceiptReader()
    out = r.out
    h = KR + ("Receipt Advice Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Receipt Advice ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:DocumentStatusCode", h + ("Document Status",))
    r.text(root, "cbc:ReceiptAdviceTypeCode", h + ("Receipt Advice Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.order_reference(root, KR + ("Order Reference",))
    r.docref(root, "cac:DespatchDocumentReference", KR + ("Despatch Document Reference", "Document Reference"))
    r.customer_party(root, "cac:DeliveryCustomerParty", KR + ("Delivery Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:DespatchSupplierParty", KR + ("Despatch Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:BuyerCustomerParty", KR + ("Buyer Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:SellerSupplierParty", KR + ("Seller Supplier Party", "Supplier Party"))
    r.receipt_shipment(r.one(root, "cac:Shipment"), KR + ("Receipt Shipment",))
    lines = root.findall("cac:ReceiptLine", NS)
    assert len(lines) <= LINES, f"the Receipt Advice model carries {LINES} lines; the document has {len(lines)}"
    for n, rl in enumerate(lines, start=1):
        r.receipt_line(rl, KR + ("Receipt Lines", f"Receipt Line {n}", "Receipt Line"))
    return out


class _ReceiptReader(_DispatchReader):
    def receipt_shipment(self, s, to: tuple[str, ...]):
        if s is None:
            return
        self.text(s, "cbc:ID", to + ("Shipment ID",))
        c = self.one(s, "cac:Consignment")
        if c is not None:
            self.text(c, "cbc:ID", to + ("Consignment", "Consignment ID"))
            self.text(c, "cbc:CarrierAssignedID", to + ("Consignment", "Carrier Assigned ID"))
            self.party_from(self.one(c, "cac:CarrierParty"), to + ("Consignment", "Carrier Party", "Party"))
        d = self.one(s, "cac:Delivery")
        if d is not None:
            self.delivery(d, to + ("Delivery",))
            self.text(d, "cbc:ActualDeliveryDate", to + ("Actual Delivery Date",))
            self.text(d, "cbc:ActualDeliveryTime", to + ("Actual Delivery Time",))
        units = s.findall("cac:TransportHandlingUnit", NS)
        assert len(units) <= UNITS, f"the Receipt Advice model carries {UNITS} received handling units; the document has {len(units)}"
        for n, u in enumerate(units, start=1):
            self.received_unit(u, to + ("Received Handling Units", f"Received Handling Unit {n}", "Received Handling Unit"))

    def received_unit(self, u, to: tuple[str, ...]):
        self.text(u, "cbc:ID", to + ("Transport Handling Unit ID",))
        self.pallet_equipment(u, to + ("Pallet Identification",))
        self.unit_documents(u, {PACK_SPECIFICATION_DOCUMENT: to + ("Pack Specification Version",), PACK_IN_FORCE_DOCUMENT: to + ("Pack Specification in Force",)})
        by_component = {component: label for label, component in CHECKS}
        for st in u.findall("cac:Status", NS):
            description = self.one(st, "cbc:Description")
            indication = self.one(st, "cbc:IndicationIndicator")
            if indication is not None and description is not None and (description.text or "").strip() in by_component:
                self.bool(st, "cbc:IndicationIndicator", to + (by_component[(description.text or "").strip()],))
                continue
            self.text(st, "cbc:ConditionCode", to + ("Receiving Condition",))
            self.text(st, "cbc:ReferenceDate", to + ("Received Date",))
            self.text(st, "cbc:ReferenceTime", to + ("Received Time",))
            self.text(st, "cbc:Description", to + ("Exception Description",))

    def receipt_line(self, rl, to: tuple[str, ...]):
        self.text(rl, "cbc:ID", to + ("Line ID",))
        self.text(rl, "cbc:Note", to + ("Note",))
        self.quantity(rl, "cbc:ReceivedQuantity", to + ("Received Quantity",))
        self.quantity(rl, "cbc:ShortQuantity", to + ("Short Quantity",))
        self.text(rl, "cbc:ShortageActionCode", to + ("Shortage Action",))
        self.quantity(rl, "cbc:RejectedQuantity", to + ("Rejected Quantity",))
        self.text(rl, "cbc:RejectReasonCode", to + ("Reject Reason",))
        self.text(rl, "cbc:RejectReason", to + ("Reject Reason Description",))
        self.text(rl, "cbc:RejectActionCode", to + ("Reject Action",))
        self.text(rl, "cbc:QuantityDiscrepancyCode", to + ("Quantity Discrepancy",))
        self.quantity(rl, "cbc:OversupplyQuantity", to + ("Oversupply Quantity",))
        self.text(rl, "cbc:ReceivedDate", to + ("Received Date",))
        self.text(rl, "cbc:TimingComplaintCode", to + ("Timing Complaint",))
        self.text(rl, "cbc:TimingComplaint", to + ("Timing Complaint Description",))
        ref = self.one(rl, "cac:OrderLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Order Line Reference", "Line ID"))
            self.text(ref, "cbc:SalesOrderLineID", to + ("Order Line Reference", "Sales Order Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Order Line Reference", "Line Status"))
        ref = self.one(rl, "cac:DespatchLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Despatch Line Reference", "Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Despatch Line Reference", "Line Status"))
            self.docref(ref, "cac:DocumentReference", to + ("Despatch Line Reference", "Document Reference"))
        self.item(rl, to + ("Item",))


def projected_receipt(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL ReceiptAdvice can carry: everything but NOT_PROJECTED and NOT_PROJECTED_UNDER."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        out[path] = v
    return out
