"""
The DespatchAdvice's open projection: a conformant OASIS UBL 2.3 DespatchAdvice written from a governed record, and read into one.

    from ubl.despatch_advice import write_despatch_advice, read_despatch_advice, validate_ubl_despatch
    ubl_xml = write_despatch_advice(instance_xml)
    assert not validate_ubl_despatch(ubl_xml)
    values = read_despatch_advice(ubl_xml)

The despatch advice composes the Order's parties, delivery, item and document references, so its
writer and reader are the Order's and the OrderResponse's with the shipment added. Where the record
names something UBL has no element for, the projection says where it went:

- The transport handling unit's identifier is the GS1 Serial Shipping Container Code, written as
  ``cbc:ID`` with the scheme named; its kind and the package's kind are this library's tokens with
  ``listURI``, as every token of the library travels.
- The pallet as an asset is ``cac:TransportEquipment``: its identifier with the scheme as
  ``schemeName`` (``schemeID`` GRAI for GS1's). UBL gives no equipment a validity period, so the
  identifier's period travels as the equipment's ``cac:ShipmentDocumentReference`` of type
  ``Pallet identification`` with ``cac:ValidityPeriod``. That period is the fined notice's fact.
- The receiver's pack specification is a document the receiver publishes, so the version the unit
  was packed to is the unit's ``cac:ShipmentDocumentReference`` of type ``Pack specification``.
- The layers on the pallet and the cases in a layer are UBL's own containment: the package's
  ``cac:ContainedPackage`` at level ``Layer`` with its quantity, holding one at level ``Case``.
- The loaded pallet's height and weight are the package's ``cac:MeasurementDimension`` by attribute.
- The unit's temperature range is ``cac:MinimumTemperature`` and ``cac:MaximumTemperature``, the
  measure in UN/ECE Recommendation 20 codes (CEL, KEL) for the Default library's SI symbols.

Two leaves of every party have no home in a UBL Contact (NOT_PROJECTED, from the Order); nothing else
of the record is left out.
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

DESPATCH_CT = "cacl4njrwanj15g3p3so8t6h"
DESPATCH_NS = "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
NSMAP_DESPATCH = {None: DESPATCH_NS, "cac": CAC, "cbc": CBC}
UBL_DESPATCH_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-DespatchAdvice-2.3.xsd")
DR = ("Despatch Advice Governed Record", "Despatch Advice")
#: The pallet identifier schemes with a UN/ECE 3055 agency: GS1's Global Returnable Asset Identifier.
PALLET_SCHEMES = {"Global Returnable Asset Identifier (GS1)": ("GRAI", "9")}
SSCC = ("SSCC", "9", "Serial Shipping Container Code (GS1)")
#: The pack specification's measures and the attribute each is written under in a MeasurementDimension.
PACK_DIMENSIONS = (("Pallet Height", "Height"), ("Weight", "Weight"))
PALLET_ID_DOCUMENT = "Pallet identification"
PACK_SPECIFICATION_DOCUMENT = "Pack specification"
UNITS = 6
LINES = 10


@lru_cache(maxsize=None)
def ubl_despatch_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_DESPATCH_XSD)


def validate_ubl_despatch(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 DespatchAdvice schema; empty when conformant."""
    return [str(e) for e in ubl_despatch_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


# ================================================================ writer
def write_despatch_advice(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(DESPATCH_CT))
    d = tree.get(*DR)
    assert d is not None, "no Despatch Advice cluster in the instance"
    w = _DespatchWriter()
    root = etree.Element(f"{{{DESPATCH_NS}}}DespatchAdvice", nsmap=NSMAP_DESPATCH)
    h = d.get("Despatch Advice Document") or Node("Despatch Advice Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Despatch Advice ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.token(root, "DocumentStatusCode", h.leaf("Document Status"), "document-status")
    w.token(root, "DespatchAdviceTypeCode", h.leaf("Despatch Advice Type"), "despatch-advice-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.order_reference(root, d.get("Order Reference"))
    w.docref(root, "AdditionalDocumentReference", d.get("Additional Document Reference", "Document Reference"))
    # UBL requires the despatching supplier and the delivery customer, every member optional: present even when the record has none
    w.supplier_party(root, "DespatchSupplierParty", d.get("Despatch Supplier Party", "Supplier Party"))
    w.required(root, "DespatchSupplierParty")
    w.customer_party(root, "DeliveryCustomerParty", d.get("Delivery Customer Party", "Customer Party"))
    w.required(root, "DeliveryCustomerParty")
    w.customer_party(root, "BuyerCustomerParty", d.get("Buyer Customer Party", "Customer Party"))
    w.supplier_party(root, "SellerSupplierParty", d.get("Seller Supplier Party", "Supplier Party"))
    w.customer_party(root, "OriginatorCustomerParty", d.get("Originator Customer Party", "Customer Party"))
    w.shipment(root, d.get("Shipment"))
    lines = d.get("Despatch Lines") or Node("Despatch Lines")
    for n in range(1, LINES + 1):
        w.despatch_line(root, lines.get(f"Despatch Line {n}", "Despatch Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _DespatchWriter(_ResponseWriter):
    def required(self, parent, name: str):
        """An aggregate UBL requires, empty when the record has nothing for it (every member of the two parties is optional)."""
        if parent.find(f"cac:{name}", NS) is None:
            self.cac(parent, name)

    def shipment(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "Shipment")
        self.cbc(el, "ID", node.leaf("Shipment ID"))
        self.cbc(el, "HandlingInstructions", node.leaf("Handling Instructions"))
        self.quantity(el, "GrossWeightMeasure", node.leaf("Gross Weight"), si=True)
        self.quantity(el, "NetWeightMeasure", node.leaf("Net Weight"), si=True)
        self.quantity(el, "GrossVolumeMeasure", node.leaf("Gross Volume"), si=True)
        self.quantity(el, "NetVolumeMeasure", node.leaf("Net Volume"), si=True)
        self.number(el, "TotalGoodsItemQuantity", node.leaf("Total Goods Item Quantity"))
        self.number(el, "TotalTransportHandlingUnitQuantity", node.leaf("Total Transport Handling Unit Quantity"))
        self.consignment(el, node.get("Consignment"))
        self.delivery(el, node.get("Delivery"))
        units = node.get("Transport Handling Units") or Node("Transport Handling Units")
        for n in range(1, UNITS + 1):
            self.handling_unit(el, units.get(f"Transport Handling Unit {n}", "Transport Handling Unit"))
        self.drop_if_empty(el)

    def consignment(self, parent, node: Node | None):
        """The consignment. UBL requires its identifier; a carrier without one has no consignment to ride on."""
        if node is None or node.leaf("Consignment ID") is None:
            return
        el = self.cac(parent, "Consignment")
        self.cbc(el, "ID", node.leaf("Consignment ID"))
        self.cbc(el, "CarrierAssignedID", node.leaf("Carrier Assigned ID"))
        if node.get("Carrier Party", "Party") is not None:
            cp = self.cac(el, "CarrierParty")
            self.party_into(cp, node.get("Carrier Party", "Party"))
            self.drop_if_empty(cp)

    def handling_unit(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "TransportHandlingUnit")
        self.cbc(el, "ID", node.leaf("Transport Handling Unit ID"), schemeID=SSCC[0], schemeAgencyID=SSCC[1], schemeName=SSCC[2])
        self.token(el, "TransportHandlingUnitTypeCode", node.leaf("Transport Handling Unit Type"), "transport-handling-unit-type")
        self.cbc(el, "HandlingInstructions", node.leaf("Handling Instructions"))
        self.number(el, "TotalPackageQuantity", node.leaf("Total Package Quantity"))
        self.cbc(el, "ShippingMarks", node.leaf("Shipping Marks"))
        pallet = node.get("Pallet Identification")
        if pallet is not None and pallet.leaf("Pallet ID") is not None:
            te = self.cac(el, "TransportEquipment")
            self.scheme(te, "ID", pallet.leaf("Pallet ID"), pallet.leaf("Pallet ID Scheme"), PALLET_SCHEMES)
            if pallet.get("Date Range") is not None:
                ref = self.cac(te, "ShipmentDocumentReference")
                self.cbc(ref, "ID", pallet.leaf("Pallet ID"))
                self.cbc(ref, "DocumentType", PALLET_ID_DOCUMENT)
                self.period(ref, "ValidityPeriod", pallet)
        for label, name in (("Minimum Temperature", "MinimumTemperature"), ("Maximum Temperature", "MaximumTemperature")):
            if node.leaf(label) is not None:
                t = self.cac(el, name)
                self.cbc(t, "AttributeID", label.split()[0])
                self.quantity(t, "Measure", node.leaf(label), si=True)
        package = node.get("Package")
        spec = None if package is None else package.get("Pack Specification")
        if spec is not None and spec.leaf("Pack Specification Version") is not None:
            ref = self.cac(el, "ShipmentDocumentReference")
            self.cbc(ref, "ID", spec.leaf("Pack Specification Version"))
            self.cbc(ref, "DocumentType", PACK_SPECIFICATION_DOCUMENT)
        self.package(el, package)
        self.drop_if_empty(el)

    def package(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "Package")
        self.cbc(el, "ID", node.leaf("Package ID"))
        self.number(el, "Quantity", node.leaf("Package Quantity"))
        self.token(el, "PackagingTypeCode", node.leaf("Packaging Type"), "packaging-type")
        spec = node.get("Pack Specification")
        if spec is not None:
            if spec.leaf("Layers per Pallet") is not None or spec.leaf("Cases per Layer") is not None:
                layer = self.cac(el, "ContainedPackage")
                self.number(layer, "Quantity", spec.leaf("Layers per Pallet"))
                self.cbc(layer, "PackageLevelCode", "Layer")
                if spec.leaf("Cases per Layer") is not None:
                    case = self.cac(layer, "ContainedPackage")
                    self.number(case, "Quantity", spec.leaf("Cases per Layer"))
                    self.cbc(case, "PackageLevelCode", "Case")
            for label, attribute in PACK_DIMENSIONS:
                if spec.leaf(label) is not None:
                    dim = self.cac(el, "MeasurementDimension")
                    self.cbc(dim, "AttributeID", attribute)
                    self.quantity(dim, "Measure", spec.leaf(label), si=True)
        self.drop_if_empty(el)

    def despatch_line(self, parent, node: Node | None):
        if node is None or node.leaf("Line ID") is None:
            return   # UBL requires the line's identifier
        dl = self.cac(parent, "DespatchLine")
        self.cbc(dl, "ID", node.leaf("Line ID"))
        self.cbc(dl, "Note", node.leaf("Note"))
        self.token(dl, "LineStatusCode", node.leaf("Line Status"), "line-status")
        self.quantity(dl, "DeliveredQuantity", node.leaf("Delivered Quantity"))
        self.quantity(dl, "BackorderQuantity", node.leaf("Backorder Quantity"))
        self.cbc(dl, "BackorderReason", node.leaf("Backorder Reason"))
        self.quantity(dl, "OutstandingQuantity", node.leaf("Outstanding Quantity"))
        self.cbc(dl, "OutstandingReason", node.leaf("Outstanding Reason"))
        ref = node.get("Order Line Reference")
        if ref is not None and ref.leaf("Line ID") is not None:   # UBL requires one; without it the document is not conformant, and says so
            r = self.cac(dl, "OrderLineReference")
            self.cbc(r, "LineID", ref.leaf("Line ID"))
            self.cbc(r, "SalesOrderLineID", ref.leaf("Sales Order Line ID"))
            self.token(r, "LineStatusCode", ref.leaf("Line Status"), "line-status")
        self.docref(dl, "DocumentReference", node.get("Line Document Reference", "Document Reference"))
        self.item(dl, node.get("Item"))


# ================================================================ reader
def read_despatch_advice(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 DespatchAdvice by label path in the Despatch Advice model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{DESPATCH_NS}}}DespatchAdvice", root.tag
    r = _DespatchReader()
    out = r.out
    h = DR + ("Despatch Advice Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Despatch Advice ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:DocumentStatusCode", h + ("Document Status",))
    r.text(root, "cbc:DespatchAdviceTypeCode", h + ("Despatch Advice Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.order_reference(root, DR + ("Order Reference",))
    r.docref(root, "cac:AdditionalDocumentReference", DR + ("Additional Document Reference", "Document Reference"))
    r.supplier_party(root, "cac:DespatchSupplierParty", DR + ("Despatch Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:DeliveryCustomerParty", DR + ("Delivery Customer Party", "Customer Party"))
    r.customer_party(root, "cac:BuyerCustomerParty", DR + ("Buyer Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:SellerSupplierParty", DR + ("Seller Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:OriginatorCustomerParty", DR + ("Originator Customer Party", "Customer Party"))
    r.shipment(r.one(root, "cac:Shipment"), DR + ("Shipment",))
    lines = root.findall("cac:DespatchLine", NS)
    assert len(lines) <= LINES, f"the Despatch Advice model carries {LINES} lines; the document has {len(lines)}"
    for n, dl in enumerate(lines, start=1):
        r.despatch_line(dl, DR + ("Despatch Lines", f"Despatch Line {n}", "Despatch Line"))
    return out


class _DespatchReader(_ResponseReader):
    def shipment(self, s, to: tuple[str, ...]):
        if s is None:
            return
        self.text(s, "cbc:ID", to + ("Shipment ID",))
        self.text(s, "cbc:HandlingInstructions", to + ("Handling Instructions",))
        self.quantity(s, "cbc:GrossWeightMeasure", to + ("Gross Weight",), si=True)
        self.quantity(s, "cbc:NetWeightMeasure", to + ("Net Weight",), si=True)
        self.quantity(s, "cbc:GrossVolumeMeasure", to + ("Gross Volume",), si=True)
        self.quantity(s, "cbc:NetVolumeMeasure", to + ("Net Volume",), si=True)
        self.number(s, "cbc:TotalGoodsItemQuantity", to + ("Total Goods Item Quantity",), "count")
        self.number(s, "cbc:TotalTransportHandlingUnitQuantity", to + ("Total Transport Handling Unit Quantity",), "count")
        c = self.one(s, "cac:Consignment")
        if c is not None:
            self.text(c, "cbc:ID", to + ("Consignment", "Consignment ID"))
            self.text(c, "cbc:CarrierAssignedID", to + ("Consignment", "Carrier Assigned ID"))
            self.party_from(self.one(c, "cac:CarrierParty"), to + ("Consignment", "Carrier Party", "Party"))
        self.delivery(self.one(s, "cac:Delivery"), to + ("Delivery",))
        units = s.findall("cac:TransportHandlingUnit", NS)
        assert len(units) <= UNITS, f"the Despatch Advice model carries {UNITS} transport handling units; the document has {len(units)}"
        for n, u in enumerate(units, start=1):
            self.handling_unit(u, to + ("Transport Handling Units", f"Transport Handling Unit {n}", "Transport Handling Unit"))

    def handling_unit(self, u, to: tuple[str, ...]):
        self.text(u, "cbc:ID", to + ("Transport Handling Unit ID",))
        self.text(u, "cbc:TransportHandlingUnitTypeCode", to + ("Transport Handling Unit Type",))
        self.text(u, "cbc:HandlingInstructions", to + ("Handling Instructions",))
        self.number(u, "cbc:TotalPackageQuantity", to + ("Total Package Quantity",), "count")
        self.text(u, "cbc:ShippingMarks", to + ("Shipping Marks",))
        te = self.one(u, "cac:TransportEquipment")
        if te is not None and self.one(te, "cbc:ID") is not None:
            pid = self.one(te, "cbc:ID")
            p = to + ("Pallet Identification",)
            self.put(p + ("Pallet ID Scheme",), self.scheme(pid, p + ("Pallet ID Scheme",), PALLET_SCHEMES, "Mutually agreed"))
            self.put(p + ("Pallet ID",), (pid.text or "").strip())
            for ref in te.findall("cac:ShipmentDocumentReference", NS):
                if (self.one(ref, "cbc:DocumentType") is not None and self.one(ref, "cbc:DocumentType").text == PALLET_ID_DOCUMENT):
                    self.period(ref, "cac:ValidityPeriod", p)
        for label, name in (("Minimum Temperature", "cac:MinimumTemperature"), ("Maximum Temperature", "cac:MaximumTemperature")):
            t = self.one(u, name)
            if t is not None:
                self.quantity(t, "cbc:Measure", to + (label,), si=True)
        for ref in u.findall("cac:ShipmentDocumentReference", NS):
            if self.one(ref, "cbc:DocumentType") is not None and self.one(ref, "cbc:DocumentType").text == PACK_SPECIFICATION_DOCUMENT:
                self.text(ref, "cbc:ID", to + ("Package", "Pack Specification", "Pack Specification Version"))
        self.package(self.one(u, "cac:Package"), to + ("Package",))

    def package(self, p, to: tuple[str, ...]):
        if p is None:
            return
        self.text(p, "cbc:ID", to + ("Package ID",))
        self.number(p, "cbc:Quantity", to + ("Package Quantity",), "count")
        self.text(p, "cbc:PackagingTypeCode", to + ("Packaging Type",))
        spec = to + ("Pack Specification",)
        for layer in p.findall("cac:ContainedPackage", NS):
            if self.one(layer, "cbc:PackageLevelCode") is not None and self.one(layer, "cbc:PackageLevelCode").text == "Layer":
                self.number(layer, "cbc:Quantity", spec + ("Layers per Pallet",), "count")
                for case in layer.findall("cac:ContainedPackage", NS):
                    if self.one(case, "cbc:PackageLevelCode") is not None and self.one(case, "cbc:PackageLevelCode").text == "Case":
                        self.number(case, "cbc:Quantity", spec + ("Cases per Layer",), "count")
        by_attribute = {a: label for label, a in PACK_DIMENSIONS}
        for d in p.findall("cac:MeasurementDimension", NS):
            label = by_attribute.get((self.one(d, "cbc:AttributeID").text or "").strip())
            if label:
                self.quantity(d, "cbc:Measure", spec + (label,), si=True)

    def despatch_line(self, dl, to: tuple[str, ...]):
        self.text(dl, "cbc:ID", to + ("Line ID",))
        self.text(dl, "cbc:Note", to + ("Note",))
        self.text(dl, "cbc:LineStatusCode", to + ("Line Status",))
        self.quantity(dl, "cbc:DeliveredQuantity", to + ("Delivered Quantity",))
        self.quantity(dl, "cbc:BackorderQuantity", to + ("Backorder Quantity",))
        self.text(dl, "cbc:BackorderReason", to + ("Backorder Reason",))
        self.quantity(dl, "cbc:OutstandingQuantity", to + ("Outstanding Quantity",))
        self.text(dl, "cbc:OutstandingReason", to + ("Outstanding Reason",))
        ref = self.one(dl, "cac:OrderLineReference")
        if ref is not None:
            self.text(ref, "cbc:LineID", to + ("Order Line Reference", "Line ID"))
            self.text(ref, "cbc:SalesOrderLineID", to + ("Order Line Reference", "Sales Order Line ID"))
            self.text(ref, "cbc:LineStatusCode", to + ("Order Line Reference", "Line Status"))
        self.docref(dl, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))
        self.item(dl, to + ("Item",))


def projected_despatch(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL DespatchAdvice can carry: everything but NOT_PROJECTED and NOT_PROJECTED_UNDER."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        out[path] = v
    return out
