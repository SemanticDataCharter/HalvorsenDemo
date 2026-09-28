"""
The Order's open projection: a conformant OASIS UBL 2.3 Order written from a governed record, and read into one.

    from ubl.order import write_order, read_order, validate_ubl
    ubl_xml = write_order(instance_xml)         # the record's Order cluster as a UBL 2.3 Order document
    assert not validate_ubl(ubl_xml)            # against the OASIS Order schema as published (data/ubl-2.3/xsd)
    values = read_order(ubl_xml)                # label paths -> values, the engine's input for a new record

The record is the system of record; the document is a projection of it. Every value the record
carries has a home in the UBL Order or is listed in NOT_PROJECTED (a contact point's method and
use, which UBL's Contact does not carry; the type of a catalog reference, which UBL's
CatalogueReference fixes). Tokens whose list is this library's (order type, line status, price
type, address use) travel as the token's value with ``listURI`` naming the published component;
tokens taken from UBL's UN/ECE default lists (payment means, allowance and charge reason) travel
as the list's code with the name beside it; an identifier's scheme travels as ``schemeName``,
with ``schemeID`` and the agency for GS1 and Dun & Bradstreet; amounts carry ``currencyID``;
quantities carry the UN/ECE Recommendation 20 ``unitCode``, the Default library's SI unit
symbols mapped to it. Element order is the UBL schema's; nothing goes in UBLExtensions.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any

import yaml
from lxml import etree

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "datagen"))
from engine import Quantity  # noqa: E402
from instance import Node, read_tree  # noqa: E402
from schema import Schema  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
ORDER_CT = "h8bttbt9afwzf9zs4jhae566"
ORDER_NS = "urn:oasis:names:specification:ubl:schema:xsd:Order-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
NSMAP = {None: ORDER_NS, "cac": CAC, "cbc": CBC}
NS = {"cac": CAC, "cbc": CBC, "o": ORDER_NS}
UBL_XSD = os.path.join(ROOT, "data", "ubl-2.3", "xsd", "maindoc", "UBL-Order-2.3.xsd")
LIB = "https://axius-sdc.com/library/business/"
DEFAULT = "https://axius-sdc.com/library/default/"
UBL_VERSION = "2.3"
R = ("Order Governed Record", "Order")   # the record's data cluster
#: Values of the record that have no home in a UBL Order (by the leaf's label, or by the path's cluster and the leaf).
NOT_PROJECTED = {"Contact Method", "Contact Use"}
NOT_PROJECTED_UNDER = {("Catalogue Reference", "Document Type")}
#: UN/ECE Recommendation 20 codes for the unit symbols the Default library's SI unit lists carry.
REC20 = {"mm": "MMT", "cm": "CMT", "m": "MTR", "km": "KMT", "mg": "MGM", "g": "GRM", "kg": "KGM", "mL": "MLT", "L": "LTR"}
SYMBOL = {v: k for k, v in REC20.items()}
#: The identification schemes an identifier can name (this library's tokens) and the UN/ECE 3055 agency that issues them.
PARTY_SCHEMES = {"Global Location Number (GS1)": ("GLN", "9"), "DUNS number": ("DUNS", "16")}
ITEM_SCHEMES = {"Global Trade Item Number (GS1)": ("GTIN", "9")}
DIMENSIONS = (("Length/Distance", "Length"), ("Weight", "Weight"), ("Volume", "Volume"))
UNIT_DEFAULT = {"count": "items", "percent": "%", "ratio": "ratio"}


@lru_cache(maxsize=None)
def ubl_schema():
    import xmlschema
    return xmlschema.XMLSchema(UBL_XSD)


def validate_ubl(xml: str) -> list[str]:
    """Validation errors of a document against the OASIS UBL 2.3 Order schema; empty when conformant."""
    return [str(e) for e in ubl_schema().iter_errors(etree.fromstring(xml.encode() if isinstance(xml, str) else xml))]


@lru_cache(maxsize=None)
def codes(key: str) -> tuple[dict[str, str], dict[str, str]]:
    """value -> code and code -> value for a token record whose values come from a UBL default code list (the code is the fragment of each definition)."""
    with open(os.path.join(ROOT, "datagen", "records", f"{key}.yaml"), encoding="utf-8") as f:
        rec = yaml.safe_load(f)
    to_code = {e["value"]: e["definition"].rsplit("#", 1)[1] for e in rec["enumeration"]}
    return to_code, {c: v for v, c in to_code.items()}


# ================================================================ writer
def write_order(instance_xml: str) -> str:
    tree = read_tree(instance_xml, Schema.for_dm(ORDER_CT))
    o = tree.get(*R)
    assert o is not None, "no Order cluster in the instance"
    w = _Writer()
    root = etree.Element(f"{{{ORDER_NS}}}Order", nsmap=NSMAP)
    h = o.get("Order Document") or Node("Order Document")
    w.cbc(root, "UBLVersionID", UBL_VERSION)
    w.cbc(root, "CustomizationID", h.leaf("Customization ID"))
    w.cbc(root, "ProfileID", h.leaf("Profile ID"))
    w.cbc(root, "ProfileExecutionID", h.leaf("Profile Execution ID"))
    w.cbc(root, "ID", h.leaf("Order ID"))
    w.cbc(root, "SalesOrderID", h.leaf("Sales Order ID"))
    w.bool(root, "CopyIndicator", h.leaf("Copy Indicator"))
    w.cbc(root, "UUID", h.leaf("Document UUID"))
    w.cbc(root, "IssueDate", h.leaf("Issue Date"))
    w.cbc(root, "IssueTime", h.leaf("Issue Time"))
    w.token(root, "OrderTypeCode", h.leaf("Order Type"), "order-type")
    w.cbc(root, "Note", h.leaf("Note"))
    w.cbc(root, "DocumentCurrencyCode", h.leaf("Document Currency"))
    w.cbc(root, "PricingCurrencyCode", h.leaf("Pricing Currency"))
    w.cbc(root, "CustomerReference", h.leaf("Customer Reference"))
    w.cbc(root, "AccountingCost", h.leaf("Accounting Cost"))
    w.number(root, "LineCountNumeric", h.leaf("Line Count"))
    w.period(root, "ValidityPeriod", h.get("Validity Period"))
    w.docref(root, "QuotationDocumentReference", o.get("Quotation Document Reference", "Document Reference"))
    w.docref(root, "OriginatorDocumentReference", o.get("Originator Document Reference", "Document Reference"))
    w.catref(root, o.get("Catalogue Reference", "Document Reference"))
    w.docref(root, "AdditionalDocumentReference", o.get("Additional Document Reference", "Document Reference"))
    w.contract(root, o.get("Contract"))
    w.customer_party(root, "BuyerCustomerParty", o.get("Buyer Customer Party", "Customer Party"))
    w.supplier_party(root, "SellerSupplierParty", o.get("Seller Supplier Party", "Supplier Party"))
    w.customer_party(root, "OriginatorCustomerParty", o.get("Originator Customer Party", "Customer Party"))
    w.customer_party(root, "AccountingCustomerParty", o.get("Accounting Customer Party", "Customer Party"))
    w.delivery(root, o.get("Delivery"))
    w.delivery_terms(root, o.get("Delivery Terms"))
    w.payment_means(root, o.get("Payment Means"))
    w.payment_terms(root, o.get("Payment Terms"))
    w.allowance_charge(root, o.get("Allowance Charge"))
    w.tax_total(root, o.get("Tax Total"))
    w.monetary_total(root, o.get("Anticipated Monetary Total"))
    lines = o.get("Order Lines") or Node("Order Lines")
    for n in range(1, 11):
        w.order_line(root, lines.get(f"Order Line {n}", "Order Line"))
    return etree.tostring(root, pretty_print=True, encoding="unicode")


class _Writer:
    # ------------------------------------------------------------ elements
    @staticmethod
    def cbc(parent, element: str, value, **attrs):
        """A basic component, when there is a value; the attributes given (currencyID, unitCode, schemeID, listURI, name) go on it."""
        if value is None or value == "":
            return None
        el = etree.SubElement(parent, f"{{{CBC}}}{element}")
        el.text = str(value)
        for k, v in attrs.items():
            if v is not None:
                el.set(k, str(v))
        return el

    @staticmethod
    def cac(parent, name: str):
        return etree.SubElement(parent, f"{{{CAC}}}{name}")

    @staticmethod
    def drop_if_empty(el):
        if len(el) == 0:
            el.getparent().remove(el)
            return None
        return el

    def bool(self, parent, name, value):
        return self.cbc(parent, name, None if value is None else str(bool(value)).lower())

    def token(self, parent, name, value, key, lib=LIB):
        """A token of this library's own list: the value, and the published component as the list."""
        return self.cbc(parent, name, value, listURI=lib + key)

    def coded(self, parent, name, value, key):
        """A token taken from a UBL default list: the list's code, with the name beside it."""
        if value is None:
            return None
        to_code, _ = codes(key)
        return self.cbc(parent, name, to_code[value], name=value)

    def amount(self, parent, name, q: Quantity | None):
        return None if q is None else self.cbc(parent, name, q.magnitude, currencyID=q.unit)

    def quantity(self, parent, name, q: Quantity | None, si: bool = False):
        """A quantity with its UN/ECE unit code: trade units carry the code already; a Default library SI symbol (an item's dimensions) is mapped."""
        return None if q is None else self.cbc(parent, name, q.magnitude, unitCode=REC20.get(q.unit, q.unit) if si else q.unit)

    def number(self, parent, name, q: Quantity | None):
        """A count, a percentage or a ratio: the magnitude alone (the unit is the element's meaning)."""
        return None if q is None else self.cbc(parent, name, q.magnitude)

    def scheme(self, parent, name, value, scheme, table):
        if value is None:
            return None
        sid, agency = table.get(scheme, (None, None))
        return self.cbc(parent, name, value, schemeID=sid, schemeAgencyID=agency, schemeName=scheme)

    # ------------------------------------------------------------ shared shapes
    def period(self, parent, name, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "StartDate", node.leaf("Date Range", "Date Range Start"))
        self.cbc(el, "EndDate", node.leaf("Date Range", "Date Range End"))
        self.drop_if_empty(el)

    def docref(self, parent, name, node: Node | None):
        if node is None or node.leaf("Document Reference ID") is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "ID", node.leaf("Document Reference ID"))
        self.cbc(el, "IssueDate", node.leaf("Document Reference Issue Date"))
        self.cbc(el, "DocumentType", node.leaf("Document Type"))   # a text in UBL; the value is this library's token
        self.cbc(el, "DocumentDescription", node.leaf("Document Description"))

    def catref(self, parent, node: Node | None):
        """UBL's CatalogueReference is its own aggregate: identifier, issue date, description; the type is the element."""
        if node is None or node.leaf("Document Reference ID") is None:
            return
        el = self.cac(parent, "CatalogueReference")
        self.cbc(el, "ID", node.leaf("Document Reference ID"))
        self.cbc(el, "IssueDate", node.leaf("Document Reference Issue Date"))
        self.cbc(el, "Description", node.leaf("Document Description"))

    def contract(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "Contract")
        self.cbc(el, "ID", node.leaf("Contract ID"))
        self.cbc(el, "IssueDate", node.leaf("Contract Issue Date"))
        self.cbc(el, "ContractType", node.leaf("Contract Type"))
        self.drop_if_empty(el)

    def address(self, parent, name, node: Node | None):
        """The Default library's US or international address as a UBL postal address."""
        if node is None:
            return
        us = node.get("US Address")
        intl = node.get("International Address")
        a = us or intl
        if a is None:
            return
        el = self.cac(parent, name)
        self.token(el, "AddressTypeCode", a.leaf("Address Use"), "address-use", DEFAULT)
        self.cbc(el, "StreetName", a.leaf("Address (Line 1)"))
        self.cbc(el, "AdditionalStreetName", a.leaf("Address (Line 2)"))
        self.cbc(el, "CityName", a.leaf("City Name"))
        self.cbc(el, "PostalZone", a.leaf("US ZIP Code") if us else a.leaf("Postal Code"))
        if us:
            self.cbc(el, "CountrySubentityCode", a.leaf("US State Code"))
        else:
            self.cbc(el, "CountrySubentity", a.leaf("Region Name"))
        country = a.leaf("Country Code ISO 3166") or ("US" if us else None)
        if country:
            c = self.cac(el, "Country")
            self.cbc(c, "IdentificationCode", country)
        self.drop_if_empty(el)

    def party_into(self, el, node: Node | None):
        """A Party's members into an element of UBL's PartyType (cac:Party, cac:DeliveryParty)."""
        if node is None:
            return
        self.cbc(el, "WebsiteURI", node.leaf("Party Contact", "Contact Point", "Website URL"))
        self.cbc(el, "EndpointID", node.leaf("Endpoint ID"))
        pid = node.get("Party Identification")
        if pid is not None and pid.leaf("Party Identification Value") is not None:
            p = self.cac(el, "PartyIdentification")
            self.scheme(p, "ID", pid.leaf("Party Identification Value"), pid.leaf("Party Identification Scheme"), PARTY_SCHEMES)
        if node.leaf("Organization Name") is not None:
            pn = self.cac(el, "PartyName")
            self.cbc(pn, "Name", node.leaf("Organization Name"))
        self.address(el, "PostalAddress", node)
        ple = node.get("Party Legal Entity")
        if ple is not None:
            e = self.cac(el, "PartyLegalEntity")
            self.cbc(e, "RegistrationName", ple.leaf("Registration Name"))
            self.cbc(e, "CompanyID", ple.leaf("Company ID"))
            self.drop_if_empty(e)
        contact = node.get("Party Contact")
        if contact is not None:
            c = self.cac(el, "Contact")
            self.cbc(c, "Name", contact.leaf("Contact Name"))
            self.cbc(c, "JobTitle", contact.leaf("Contact Job Title"))
            self.cbc(c, "Department", contact.leaf("Contact Department"))
            self.cbc(c, "Telephone", contact.leaf("Contact Point", "Phone Number"))
            self.cbc(c, "Telefax", contact.leaf("Contact Point", "Fax Number"))
            self.cbc(c, "ElectronicMail", contact.leaf("Contact Point", "Email Address"))
            self.drop_if_empty(c)

    def customer_party(self, parent, name, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "CustomerAssignedAccountID", node.leaf("Customer Assigned Account ID"))
        self.cbc(el, "SupplierAssignedAccountID", node.leaf("Supplier Assigned Account ID"))
        if node.get("Party") is not None:
            self.party_into(self.cac(el, "Party"), node.get("Party"))
        self.drop_if_empty(el)

    def supplier_party(self, parent, name, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "CustomerAssignedAccountID", node.leaf("Customer Assigned Account ID"))
        if node.get("Party") is not None:
            self.party_into(self.cac(el, "Party"), node.get("Party"))
        self.drop_if_empty(el)

    def location(self, parent, name, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "ID", node.leaf("Delivery Location ID"))
        self.cbc(el, "Name", node.leaf("Delivery Location Name"))
        self.address(el, "Address", node)
        self.drop_if_empty(el)

    def delivery(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "Delivery")
        self.cbc(el, "ID", node.leaf("Delivery ID"))
        self.quantity(el, "Quantity", node.leaf("Delivery Quantity"))
        self.cbc(el, "LatestDeliveryDate", node.leaf("Latest Delivery Date"))
        self.location(el, "DeliveryLocation", node.get("Delivery Location"))
        self.period(el, "RequestedDeliveryPeriod", node.get("Requested Delivery Period"))
        if node.get("Delivery Party", "Party") is not None:
            dp = self.cac(el, "DeliveryParty")
            self.party_into(dp, node.get("Delivery Party", "Party"))
            self.drop_if_empty(dp)
        self.drop_if_empty(el)

    def delivery_terms(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "DeliveryTerms")
        self.cbc(el, "ID", node.leaf("Delivery Terms Code"), schemeName="Incoterms 2020")
        self.cbc(el, "SpecialTerms", node.leaf("Delivery Special Terms"))
        self.location(el, "DeliveryLocation", node.get("Delivery Location"))
        self.drop_if_empty(el)

    def payment_means(self, parent, node: Node | None):
        if node is None or node.leaf("Payment Means") is None:
            return   # UBL requires the code
        el = self.cac(parent, "PaymentMeans")
        self.coded(el, "PaymentMeansCode", node.leaf("Payment Means"), "payment-means")
        self.cbc(el, "PaymentDueDate", node.leaf("Payment Due Date"))
        self.cbc(el, "InstructionNote", node.leaf("Note"))

    def payment_terms(self, parent, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, "PaymentTerms")
        self.cbc(el, "ID", node.leaf("Payment Terms ID"))
        self.cbc(el, "Note", node.leaf("Note"))
        self.number(el, "SettlementDiscountPercent", node.leaf("Settlement Discount Percent"))
        self.number(el, "PenaltySurchargePercent", node.leaf("Penalty Surcharge Percent"))
        self.cbc(el, "PaymentDueDate", node.leaf("Payment Due Date"))
        self.period(el, "SettlementPeriod", node.get("Settlement Period"))
        self.drop_if_empty(el)

    def allowance_charge(self, parent, node: Node | None):
        if node is None or node.leaf("Charge Indicator") is None or node.leaf("Allowance Charge Amount") is None:
            return   # UBL requires the indicator and the amount
        el = self.cac(parent, "AllowanceCharge")
        self.bool(el, "ChargeIndicator", node.leaf("Charge Indicator"))
        self.coded(el, "AllowanceChargeReasonCode", node.leaf("Allowance Charge Reason"), "allowance-charge-reason")
        self.cbc(el, "AllowanceChargeReason", node.leaf("Allowance Charge Reason Text"))
        self.number(el, "MultiplierFactorNumeric", node.leaf("Multiplier Factor"))
        self.amount(el, "Amount", node.leaf("Allowance Charge Amount"))
        self.amount(el, "BaseAmount", node.leaf("Base Amount"))

    def tax_category(self, parent, name, node: Node | None):
        if node is None:
            return
        el = self.cac(parent, name)
        self.cbc(el, "ID", node.leaf("Tax Category ID"))
        self.cbc(el, "Name", node.leaf("Tax Category Name"))
        self.number(el, "Percent", node.leaf("Tax Percent"))
        ts = self.cac(el, "TaxScheme")   # required by UBL
        self.cbc(ts, "ID", node.leaf("Tax Scheme", "Tax Scheme ID"))
        self.cbc(ts, "Name", node.leaf("Tax Scheme", "Tax Scheme Name"))

    def tax_total(self, parent, node: Node | None):
        if node is None or node.leaf("Tax Amount") is None:
            return
        el = self.cac(parent, "TaxTotal")
        self.amount(el, "TaxAmount", node.leaf("Tax Amount"))
        sub = node.get("Tax Subtotal")
        if sub is not None and sub.leaf("Tax Amount") is not None:
            s = self.cac(el, "TaxSubtotal")
            self.amount(s, "TaxableAmount", sub.leaf("Taxable Amount"))
            self.amount(s, "TaxAmount", sub.leaf("Tax Amount"))
            self.tax_category(s, "TaxCategory", sub.get("Tax Category") or Node("Tax Category"))

    def monetary_total(self, parent, node: Node | None, name: str = "AnticipatedMonetaryTotal"):
        if node is None or node.leaf("Payable Amount") is None:
            return
        el = self.cac(parent, name)
        for name, label in (("LineExtensionAmount", "Line Extension Total Amount"), ("TaxExclusiveAmount", "Tax Exclusive Amount"), ("TaxInclusiveAmount", "Tax Inclusive Amount"),
                            ("AllowanceTotalAmount", "Allowance Total Amount"), ("ChargeTotalAmount", "Charge Total Amount"), ("PrepaidAmount", "Prepaid Amount"),
                            ("PayableRoundingAmount", "Payable Rounding Amount"), ("PayableAmount", "Payable Amount")):
            self.amount(el, name, node.leaf(label))

    def item_identification(self, parent, name, node: Node | None):
        if node is None or node.leaf("Item Identification Value") is None:
            return
        el = self.cac(parent, name)
        self.scheme(el, "ID", node.leaf("Item Identification Value"), node.leaf("Item Identification Scheme"), ITEM_SCHEMES)
        self.cbc(el, "ExtendedID", node.leaf("Item Extended ID"))

    def item(self, parent, node: Node | None):
        el = self.cac(parent, "Item")   # required by UBL, every member optional
        if node is None:
            return
        self.cbc(el, "Description", node.leaf("Item Description"))
        self.number(el, "PackQuantity", node.leaf("Pack Quantity"))
        self.number(el, "PackSizeNumeric", node.leaf("Pack Size"))
        self.cbc(el, "Name", node.leaf("Item Name"))
        self.cbc(el, "BrandName", node.leaf("Brand Name"))
        self.cbc(el, "ModelName", node.leaf("Model Name"))
        self.item_identification(el, "BuyersItemIdentification", node.get("Buyer's Item Identification", "Item Identification"))
        self.item_identification(el, "SellersItemIdentification", node.get("Seller's Item Identification", "Item Identification"))
        self.item_identification(el, "ManufacturersItemIdentification", node.get("Manufacturer's Item Identification", "Item Identification"))
        self.item_identification(el, "StandardItemIdentification", node.get("Standard Item Identification", "Item Identification"))
        cc = node.get("Commodity Classification")
        if cc is not None:
            c = self.cac(el, "CommodityClassification")
            self.cbc(c, "CommodityCode", cc.leaf("Commodity Code"))
            self.cbc(c, "ItemClassificationCode", cc.leaf("Item Classification Code"))
            self.drop_if_empty(c)
        self.tax_category(el, "ClassifiedTaxCategory", node.get("Tax Category"))
        dims = node.get("Item Dimensions")
        if dims is not None:
            for label, attribute in DIMENSIONS:
                q = dims.leaf(label)
                if q is not None:
                    d = self.cac(el, "Dimension")
                    self.cbc(d, "AttributeID", attribute)
                    self.quantity(d, "Measure", q, si=True)

    def price(self, parent, node: Node | None):
        if node is None or node.leaf("Price Amount") is None:
            return
        el = self.cac(parent, "Price")
        self.amount(el, "PriceAmount", node.leaf("Price Amount"))
        self.quantity(el, "BaseQuantity", node.leaf("Base Quantity"))
        self.token(el, "PriceTypeCode", node.leaf("Price Type"), "price-type")
        self.period(el, "ValidityPeriod", node.get("Price Validity Period"))

    def line_item(self, parent, name: str, li: Node | None, status=None, status_key: str = "line-status"):
        """A UBL LineItem (cac:LineItem, or a substitute line item) from a Line Item cluster; ``status`` overrides the line's own status (a response carries its answer there)."""
        if li is None or li.leaf("Line ID") is None:
            return None   # UBL requires the line item's identifier
        el = self.cac(parent, name)
        self.cbc(el, "ID", li.leaf("Line ID"))
        self.cbc(el, "Note", li.leaf("Note"))
        self.token(el, "LineStatusCode", status if status is not None else li.leaf("Line Status"), status_key)
        self.quantity(el, "Quantity", li.leaf("Ordered Quantity"))
        self.amount(el, "LineExtensionAmount", li.leaf("Line Extension Amount"))
        self.amount(el, "TotalTaxAmount", li.leaf("Total Tax Amount"))
        self.bool(el, "PartialDeliveryIndicator", li.leaf("Partial Delivery Allowed"))
        self.bool(el, "BackOrderAllowedIndicator", li.leaf("Back Order Allowed"))
        self.delivery(el, li.get("Delivery"))
        self.price(el, li.get("Price"))
        self.item(el, li.get("Item"))
        return el

    def order_line(self, parent, node: Node | None):
        if node is None:
            return
        li = node.get("Line Item")
        if li is None or li.leaf("Line ID") is None:
            return   # UBL requires the line item and its identifier
        ol = self.cac(parent, "OrderLine")
        self.line_item(ol, "LineItem", li)
        self.docref(ol, "DocumentReference", node.get("Line Document Reference", "Document Reference"))


# ================================================================ reader
def read_order(ubl_xml: str) -> dict[str, Any]:
    """The values of a UBL 2.3 Order by label path in the Order model, the engine's input for a record."""
    root = etree.fromstring(ubl_xml.encode() if isinstance(ubl_xml, str) else ubl_xml)
    assert root.tag == f"{{{ORDER_NS}}}Order", root.tag
    r = _Reader()
    out = r.out
    h = R + ("Order Document",)
    r.text(root, "cbc:CustomizationID", h + ("Customization ID",))
    r.text(root, "cbc:ProfileID", h + ("Profile ID",))
    r.text(root, "cbc:ProfileExecutionID", h + ("Profile Execution ID",))
    r.text(root, "cbc:ID", h + ("Order ID",))
    r.text(root, "cbc:SalesOrderID", h + ("Sales Order ID",))
    r.bool(root, "cbc:CopyIndicator", h + ("Copy Indicator",))
    r.text(root, "cbc:UUID", h + ("Document UUID",))
    r.text(root, "cbc:IssueDate", h + ("Issue Date",))
    r.text(root, "cbc:IssueTime", h + ("Issue Time",))
    r.text(root, "cbc:OrderTypeCode", h + ("Order Type",))
    r.text(root, "cbc:Note", h + ("Note",))
    r.text(root, "cbc:DocumentCurrencyCode", h + ("Document Currency",))
    r.currency = out.get("/".join(h + ("Document Currency",)))
    r.text(root, "cbc:PricingCurrencyCode", h + ("Pricing Currency",))
    r.text(root, "cbc:CustomerReference", h + ("Customer Reference",))
    r.text(root, "cbc:AccountingCost", h + ("Accounting Cost",))
    r.number(root, "cbc:LineCountNumeric", h + ("Line Count",), "count")
    r.period(root, "cac:ValidityPeriod", h + ("Validity Period",))
    r.docref(root, "cac:QuotationDocumentReference", R + ("Quotation Document Reference", "Document Reference"))
    r.docref(root, "cac:OriginatorDocumentReference", R + ("Originator Document Reference", "Document Reference"))
    r.catref(root, R + ("Catalogue Reference", "Document Reference"))
    r.contract(root, R + ("Contract",))
    r.docref(root, "cac:AdditionalDocumentReference", R + ("Additional Document Reference", "Document Reference"))
    r.customer_party(root, "cac:BuyerCustomerParty", R + ("Buyer Customer Party", "Customer Party"))
    r.supplier_party(root, "cac:SellerSupplierParty", R + ("Seller Supplier Party", "Supplier Party"))
    r.customer_party(root, "cac:OriginatorCustomerParty", R + ("Originator Customer Party", "Customer Party"))
    r.customer_party(root, "cac:AccountingCustomerParty", R + ("Accounting Customer Party", "Customer Party"))
    r.delivery(r.one(root, "cac:Delivery"), R + ("Delivery",))
    r.delivery_terms(root, R + ("Delivery Terms",))
    r.payment_means(root, R + ("Payment Means",))
    r.payment_terms(root, R + ("Payment Terms",))
    r.allowance_charge(root, R + ("Allowance Charge",))
    r.tax_total(root, R + ("Tax Total",))
    r.monetary_total(root, R + ("Anticipated Monetary Total",))
    lines = root.findall("cac:OrderLine", NS)
    assert len(lines) <= 10, f"the Order model carries ten lines; the document has {len(lines)}"
    for n, ol in enumerate(lines, start=1):
        r.order_line(ol, R + ("Order Lines", f"Order Line {n}", "Order Line"))
    return out


class _Reader:
    def __init__(self):
        self.out: dict[str, Any] = {}
        self.currency: str | None = None

    # ------------------------------------------------------------ primitives
    @staticmethod
    def one(el, path: str):
        return None if el is None else el.find(path, NS)

    def put(self, path: tuple[str, ...], value):
        if value is not None and value != "":
            self.out["/".join(path)] = value

    def text(self, el, path: str, to: tuple[str, ...]):
        e = self.one(el, path)
        self.put(to, None if e is None else (e.text or "").strip())
        return e

    def bool(self, el, path: str, to: tuple[str, ...]):
        e = self.one(el, path)
        if e is not None:
            self.put(to, (e.text or "").strip().lower() == "true")

    def amount(self, el, path: str, to: tuple[str, ...]):
        e = self.one(el, path)
        if e is not None:
            self.put(to, Quantity((e.text or "").strip(), e.get("currencyID") or self.currency or ""))

    def quantity(self, el, path: str, to: tuple[str, ...], si: bool = False):
        e = self.one(el, path)
        if e is not None:
            code = e.get("unitCode") or ""
            self.put(to, Quantity((e.text or "").strip(), SYMBOL.get(code, code) if si else code))

    def number(self, el, path: str, to: tuple[str, ...], kind: str):
        e = self.one(el, path)
        if e is not None:
            self.put(to, Quantity((e.text or "").strip(), UNIT_DEFAULT[kind]))

    def coded(self, el, path: str, to: tuple[str, ...], key: str):
        e = self.one(el, path)
        if e is not None:
            _, to_value = codes(key)
            code = (e.text or "").strip()
            assert code in to_value, f"{path}: code {code!r} is not in the {key} list"
            self.put(to, to_value[code])

    def scheme(self, e, to_scheme: tuple[str, ...], table: dict, fallback: str):
        name = e.get("schemeName")
        if name in table or name in _scheme_values(to_scheme[-1]):
            return name
        by_id = {sid: v for v, (sid, _) in table.items()}
        return by_id.get(e.get("schemeID"), fallback)

    # ------------------------------------------------------------ shared shapes
    def period(self, el, path: str, to: tuple[str, ...]):
        p = self.one(el, path)
        if p is not None:
            self.text(p, "cbc:StartDate", to + ("Date Range", "Date Range Start"))
            self.text(p, "cbc:EndDate", to + ("Date Range", "Date Range End"))

    def docref(self, el, path: str, to: tuple[str, ...]):
        d = self.one(el, path)
        if d is not None:
            self.text(d, "cbc:ID", to + ("Document Reference ID",))
            self.text(d, "cbc:IssueDate", to + ("Document Reference Issue Date",))
            self.text(d, "cbc:DocumentType", to + ("Document Type",))
            self.text(d, "cbc:DocumentDescription", to + ("Document Description",))

    def catref(self, el, to: tuple[str, ...]):
        d = self.one(el, "cac:CatalogueReference")
        if d is not None:
            self.text(d, "cbc:ID", to + ("Document Reference ID",))
            self.text(d, "cbc:IssueDate", to + ("Document Reference Issue Date",))
            self.text(d, "cbc:Description", to + ("Document Description",))

    def contract(self, el, to: tuple[str, ...]):
        c = self.one(el, "cac:Contract")
        if c is not None:
            self.text(c, "cbc:ID", to + ("Contract ID",))
            self.text(c, "cbc:IssueDate", to + ("Contract Issue Date",))
            self.text(c, "cbc:ContractType", to + ("Contract Type",))

    def address(self, el, path: str, to: tuple[str, ...]):
        """A UBL postal address into the Default library's US address (country US) or international address."""
        a = self.one(el, path)
        if a is None:
            return
        country = (self.one(a, "cac:Country/cbc:IdentificationCode").text or "").strip() if self.one(a, "cac:Country/cbc:IdentificationCode") is not None else None
        us = country == "US"
        t = to + ("US Address" if us else "International Address",)
        self.text(a, "cbc:StreetName", t + ("Address (Line 1)",))
        self.text(a, "cbc:AdditionalStreetName", t + ("Address (Line 2)",))
        self.text(a, "cbc:CityName", t + ("City Name",))
        if us:
            self.text(a, "cbc:CountrySubentityCode", t + ("US State Code",))
            self.text(a, "cbc:PostalZone", t + ("US ZIP Code",))
        else:
            self.text(a, "cbc:CountrySubentity", t + ("Region Name",))
            self.text(a, "cbc:PostalZone", t + ("Postal Code",))
        self.put(t + ("Country Code ISO 3166",), country)
        self.text(a, "cbc:AddressTypeCode", t + ("Address Use",))

    def party_from(self, p, to: tuple[str, ...]):
        """A UBL PartyType element (cac:Party, cac:DeliveryParty) into the Party cluster at ``to``."""
        if p is None:
            return
        self.text(p, "cbc:EndpointID", to + ("Endpoint ID",))
        pid = self.one(p, "cac:PartyIdentification/cbc:ID")
        if pid is not None:
            self.put(to + ("Party Identification", "Party Identification Scheme"), self.scheme(pid, to + ("Party Identification", "Party Identification Scheme"), PARTY_SCHEMES, "Mutually agreed"))
            self.put(to + ("Party Identification", "Party Identification Value"), (pid.text or "").strip())
        self.text(p, "cac:PartyName/cbc:Name", to + ("Organization Name",))
        self.address(p, "cac:PostalAddress", to)
        ple = self.one(p, "cac:PartyLegalEntity")
        if ple is not None:
            self.text(ple, "cbc:RegistrationName", to + ("Party Legal Entity", "Registration Name"))
            self.text(ple, "cbc:CompanyID", to + ("Party Legal Entity", "Company ID"))
        c = self.one(p, "cac:Contact")
        if c is not None:
            self.text(c, "cbc:Name", to + ("Party Contact", "Contact Name"))
            self.text(c, "cbc:JobTitle", to + ("Party Contact", "Contact Job Title"))
            self.text(c, "cbc:Department", to + ("Party Contact", "Contact Department"))
            self.text(c, "cbc:Telephone", to + ("Party Contact", "Contact Point", "Phone Number"))
            self.text(c, "cbc:Telefax", to + ("Party Contact", "Contact Point", "Fax Number"))
            self.text(c, "cbc:ElectronicMail", to + ("Party Contact", "Contact Point", "Email Address"))
        self.text(p, "cbc:WebsiteURI", to + ("Party Contact", "Contact Point", "Website URL"))

    def customer_party(self, el, path: str, to: tuple[str, ...]):
        cp = self.one(el, path)
        if cp is not None:
            self.text(cp, "cbc:CustomerAssignedAccountID", to + ("Customer Assigned Account ID",))
            self.text(cp, "cbc:SupplierAssignedAccountID", to + ("Supplier Assigned Account ID",))
            self.party_from(self.one(cp, "cac:Party"), to + ("Party",))

    def supplier_party(self, el, path: str, to: tuple[str, ...]):
        sp = self.one(el, path)
        if sp is not None:
            self.text(sp, "cbc:CustomerAssignedAccountID", to + ("Customer Assigned Account ID",))
            self.party_from(self.one(sp, "cac:Party"), to + ("Party",))

    def location(self, el, path: str, to: tuple[str, ...]):
        loc = self.one(el, path)
        if loc is not None:
            self.text(loc, "cbc:ID", to + ("Delivery Location ID",))
            self.text(loc, "cbc:Name", to + ("Delivery Location Name",))
            self.address(loc, "cac:Address", to)

    def delivery(self, d, to: tuple[str, ...]):
        if d is None:
            return
        self.text(d, "cbc:ID", to + ("Delivery ID",))
        self.quantity(d, "cbc:Quantity", to + ("Delivery Quantity",))
        self.text(d, "cbc:LatestDeliveryDate", to + ("Latest Delivery Date",))
        self.location(d, "cac:DeliveryLocation", to + ("Delivery Location",))
        self.period(d, "cac:RequestedDeliveryPeriod", to + ("Requested Delivery Period",))
        self.party_from(self.one(d, "cac:DeliveryParty"), to + ("Delivery Party", "Party"))

    def delivery_terms(self, el, to: tuple[str, ...]):
        dt = self.one(el, "cac:DeliveryTerms")
        if dt is not None:
            self.text(dt, "cbc:ID", to + ("Delivery Terms Code",))
            self.text(dt, "cbc:SpecialTerms", to + ("Delivery Special Terms",))
            self.location(dt, "cac:DeliveryLocation", to + ("Delivery Location",))

    def payment_means(self, el, to: tuple[str, ...]):
        pm = self.one(el, "cac:PaymentMeans")
        if pm is not None:
            self.coded(pm, "cbc:PaymentMeansCode", to + ("Payment Means",), "payment-means")
            self.text(pm, "cbc:PaymentDueDate", to + ("Payment Due Date",))
            self.text(pm, "cbc:InstructionNote", to + ("Note",))

    def payment_terms(self, el, to: tuple[str, ...]):
        pt = self.one(el, "cac:PaymentTerms")
        if pt is not None:
            self.text(pt, "cbc:ID", to + ("Payment Terms ID",))
            self.text(pt, "cbc:Note", to + ("Note",))
            self.number(pt, "cbc:SettlementDiscountPercent", to + ("Settlement Discount Percent",), "percent")
            self.number(pt, "cbc:PenaltySurchargePercent", to + ("Penalty Surcharge Percent",), "percent")
            self.text(pt, "cbc:PaymentDueDate", to + ("Payment Due Date",))
            self.period(pt, "cac:SettlementPeriod", to + ("Settlement Period",))

    def allowance_charge(self, el, to: tuple[str, ...]):
        ac = self.one(el, "cac:AllowanceCharge")
        if ac is not None:
            self.bool(ac, "cbc:ChargeIndicator", to + ("Charge Indicator",))
            self.coded(ac, "cbc:AllowanceChargeReasonCode", to + ("Allowance Charge Reason",), "allowance-charge-reason")
            self.text(ac, "cbc:AllowanceChargeReason", to + ("Allowance Charge Reason Text",))
            self.number(ac, "cbc:MultiplierFactorNumeric", to + ("Multiplier Factor",), "ratio")
            self.amount(ac, "cbc:Amount", to + ("Allowance Charge Amount",))
            self.amount(ac, "cbc:BaseAmount", to + ("Base Amount",))

    def tax_category(self, el, path: str, to: tuple[str, ...]):
        tc = self.one(el, path)
        if tc is not None:
            self.text(tc, "cbc:ID", to + ("Tax Category ID",))
            self.text(tc, "cbc:Name", to + ("Tax Category Name",))
            self.number(tc, "cbc:Percent", to + ("Tax Percent",), "percent")
            self.text(tc, "cac:TaxScheme/cbc:ID", to + ("Tax Scheme", "Tax Scheme ID"))
            self.text(tc, "cac:TaxScheme/cbc:Name", to + ("Tax Scheme", "Tax Scheme Name"))

    def tax_total(self, el, to: tuple[str, ...]):
        tt = self.one(el, "cac:TaxTotal")
        if tt is not None:
            self.amount(tt, "cbc:TaxAmount", to + ("Tax Amount",))
            st = self.one(tt, "cac:TaxSubtotal")
            if st is not None:
                self.amount(st, "cbc:TaxableAmount", to + ("Tax Subtotal", "Taxable Amount"))
                self.amount(st, "cbc:TaxAmount", to + ("Tax Subtotal", "Tax Amount"))
                self.tax_category(st, "cac:TaxCategory", to + ("Tax Subtotal", "Tax Category"))

    def monetary_total(self, el, to: tuple[str, ...], name: str = "AnticipatedMonetaryTotal"):
        mt = self.one(el, f"cac:{name}")
        if mt is not None:
            for name, label in (("LineExtensionAmount", "Line Extension Total Amount"), ("TaxExclusiveAmount", "Tax Exclusive Amount"), ("TaxInclusiveAmount", "Tax Inclusive Amount"),
                                ("AllowanceTotalAmount", "Allowance Total Amount"), ("ChargeTotalAmount", "Charge Total Amount"), ("PrepaidAmount", "Prepaid Amount"),
                                ("PayableRoundingAmount", "Payable Rounding Amount"), ("PayableAmount", "Payable Amount")):
                self.amount(mt, f"cbc:{name}", to + (label,))

    def item_identification(self, el, path: str, to: tuple[str, ...], fallback: str):
        ii = self.one(el, path)
        if ii is not None:
            i = self.one(ii, "cbc:ID")
            self.put(to + ("Item Identification Scheme",), self.scheme(i, to + ("Item Identification Scheme",), ITEM_SCHEMES, fallback))
            self.put(to + ("Item Identification Value",), (i.text or "").strip())
            self.text(ii, "cbc:ExtendedID", to + ("Item Extended ID",))

    def item(self, el, to: tuple[str, ...]):
        it = self.one(el, "cac:Item")
        if it is None:
            return
        self.text(it, "cbc:Description", to + ("Item Description",))
        self.number(it, "cbc:PackQuantity", to + ("Pack Quantity",), "count")
        self.number(it, "cbc:PackSizeNumeric", to + ("Pack Size",), "count")
        self.text(it, "cbc:Name", to + ("Item Name",))
        self.text(it, "cbc:BrandName", to + ("Brand Name",))
        self.text(it, "cbc:ModelName", to + ("Model Name",))
        self.item_identification(it, "cac:BuyersItemIdentification", to + ("Buyer's Item Identification", "Item Identification"), "Buyer's item number")
        self.item_identification(it, "cac:SellersItemIdentification", to + ("Seller's Item Identification", "Item Identification"), "Seller's item number")
        self.item_identification(it, "cac:ManufacturersItemIdentification", to + ("Manufacturer's Item Identification", "Item Identification"), "Manufacturer's item number")
        self.item_identification(it, "cac:StandardItemIdentification", to + ("Standard Item Identification", "Item Identification"), "Mutually agreed")
        self.text(it, "cac:CommodityClassification/cbc:CommodityCode", to + ("Commodity Classification", "Commodity Code"))
        self.text(it, "cac:CommodityClassification/cbc:ItemClassificationCode", to + ("Commodity Classification", "Item Classification Code"))
        self.tax_category(it, "cac:ClassifiedTaxCategory", to + ("Tax Category",))
        by_attribute = {a: label for label, a in DIMENSIONS}
        for d in it.findall("cac:Dimension", NS):
            label = by_attribute.get((self.one(d, "cbc:AttributeID").text or "").strip())
            if label:
                self.quantity(d, "cbc:Measure", to + ("Item Dimensions", label), si=True)

    def price(self, el, to: tuple[str, ...]):
        p = self.one(el, "cac:Price")
        if p is not None:
            self.amount(p, "cbc:PriceAmount", to + ("Price Amount",))
            self.quantity(p, "cbc:BaseQuantity", to + ("Base Quantity",))
            self.text(p, "cbc:PriceTypeCode", to + ("Price Type",))
            self.period(p, "cac:ValidityPeriod", to + ("Price Validity Period",))

    def line_item_from(self, li, t: tuple[str, ...], status_to: tuple[str, ...] | None = None):
        """A UBL LineItem into the Line Item cluster at ``t``; its status goes to ``status_to`` when given (a response's answer)."""
        if li is None:
            return
        self.text(li, "cbc:ID", t + ("Line ID",))
        self.text(li, "cbc:Note", t + ("Note",))
        self.text(li, "cbc:LineStatusCode", status_to if status_to is not None else t + ("Line Status",))
        self.quantity(li, "cbc:Quantity", t + ("Ordered Quantity",))
        self.amount(li, "cbc:LineExtensionAmount", t + ("Line Extension Amount",))
        self.amount(li, "cbc:TotalTaxAmount", t + ("Total Tax Amount",))
        self.bool(li, "cbc:PartialDeliveryIndicator", t + ("Partial Delivery Allowed",))
        self.bool(li, "cbc:BackOrderAllowedIndicator", t + ("Back Order Allowed",))
        self.delivery(self.one(li, "cac:Delivery"), t + ("Delivery",))
        self.price(li, t + ("Price",))
        self.item(li, t + ("Item",))

    def order_line(self, ol, to: tuple[str, ...]):
        self.line_item_from(self.one(ol, "cac:LineItem"), to + ("Line Item",))
        self.docref(ol, "cac:DocumentReference", to + ("Line Document Reference", "Document Reference"))



@lru_cache(maxsize=None)
def _scheme_values(label: str) -> tuple[str, ...]:
    key = {"Party Identification Scheme": "party-identification-scheme", "Item Identification Scheme": "item-identification-scheme"}[label]
    with open(os.path.join(ROOT, "datagen", "records", f"{key}.yaml"), encoding="utf-8") as f:
        return tuple(e["value"] for e in yaml.safe_load(f)["enumeration"])


def projected(values: dict[str, Any]) -> dict[str, Any]:
    """The record's values a UBL Order can carry: everything but NOT_PROJECTED."""
    out = {}
    for path, v in values.items():
        parts = path.split("/")
        if parts[-1] in NOT_PROJECTED or any((c, parts[-1]) in NOT_PROJECTED_UNDER for c in parts):
            continue
        out[path] = v
    return out
