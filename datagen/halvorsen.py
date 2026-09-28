"""
The Halvorsen orders: a retailer's purchase orders to Halvorsen Foods, generated on the template engine.

Halvorsen Foods is fictitious and always said so; so is the retailer, Kestrel Mercantile. A seeded
random stream draws a year of orders (one to six lines each) from Halvorsen's catalog, the same on
every run. Each order is one instance of the published Order model, with the buyer, the seller, the
delivery to the retailer's distribution center, the payment terms, the tax total, the anticipated
monetary total, and the lines; the UBL projection of each is written beside it.

    python datagen/halvorsen.py --orders 24 --out out/halvorsen
    -> out/halvorsen/records/order-<instance id>.xml  and  out/halvorsen/ubl/<order id>.xml

The identifiers are GS1-shaped with valid check digits under a prefix GS1 does not issue, so
nothing here can be mistaken for a real company's key.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ubl"))
from engine import Quantity  # noqa: E402
from shared import RETAILER_SYSTEM, cuid_generator, record, write_record  # noqa: E402

O = "Order Governed Record/Order/"
CURRENCY = "USD"


def gs1_check(digits: str) -> str:
    """A GS1 key with its check digit (GLN and GTIN-13 are 13 digits, GTIN-14 fourteen; the weights are 3 and 1 from the right)."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return digits + str((10 - total % 10) % 10)


# Fictitious. The prefix 0000 is not a GS1 company prefix.
HALVORSEN = {
    "name": "Halvorsen Foods, Inc.", "gln": gs1_check("000000100001"), "endpoint": gs1_check("000000100001"), "company_id": "MN-41-2207731",
    "address": {"line1": "400 Mill Street", "city": "Duluth", "state": "MN", "zip": "55802"},
    "contact": {"name": "Order desk", "department": "Customer service", "phone": "+1 218 555 0140", "email": "orders@halvorsenfoods.example"},
}
KESTREL = {
    "name": "Kestrel Mercantile, Inc.", "gln": gs1_check("000000200001"), "endpoint": gs1_check("000000200001"), "company_id": "IL-77-5590012",
    "address": {"line1": "1200 West Fulton Market", "line2": "Suite 400", "city": "Chicago", "state": "IL", "zip": "60607"},
    "contact": {"name": "Grocery buying office", "department": "Merchandising", "phone": "+1 312 555 0188", "email": "grocery.buying@kestrelmercantile.example"},
    "dc": {"gln": gs1_check("000000200002"), "name": "Kestrel Mercantile DC 2 (Joliet)", "line1": "2900 Channahon Road", "city": "Joliet", "state": "IL", "zip": "60436"},
}
CATALOG = [   # (Halvorsen's item number, name, description, GTIN-14 body, case price in USD per CS, units per case, case weight kg, case volume L)
    ("HF-1001", "Halvorsen Rye Crispbread 250 g", "Whole-grain rye crispbread, 250 g carton, 12 per case", "1000000100001", "31.20", 12, "3.40", "9.600"),
    ("HF-1002", "Halvorsen Seeded Crispbread 250 g", "Rye crispbread with sunflower and sesame, 250 g carton, 12 per case", "1000000100002", "33.60", 12, "3.45", "9.600"),
    ("HF-2001", "Halvorsen Lingonberry Preserve 400 g", "Lingonberry preserve, 400 g glass jar, 6 per case", "1000000100003", "27.90", 6, "4.10", "4.200"),
    ("HF-2002", "Halvorsen Cloudberry Preserve 400 g", "Cloudberry preserve, 400 g glass jar, 6 per case", "1000000100004", "41.40", 6, "4.10", "4.200"),
    ("HF-3001", "Halvorsen Brown Cheese 500 g", "Whey cheese, 500 g block, 8 per case, chilled", "1000000100005", "38.80", 8, "4.60", "5.100"),
    ("HF-4001", "Halvorsen Fish Cakes 1 kg", "Cod fish cakes, 1 kg tray, 6 per case, chilled", "1000000100006", "52.20", 6, "6.90", "8.400"),
    ("HF-5001", "Halvorsen Oat Porridge 1 kg", "Rolled oats, 1 kg bag, 10 per case", "1000000100007", "24.50", 10, "10.30", "16.000"),
    ("HF-5002", "Halvorsen Muesli 750 g", "Oat and fruit muesli, 750 g bag, 8 per case", "1000000100008", "29.60", 8, "6.40", "12.800"),
]
ITEM_CLASS = {"HF-1": "50181900", "HF-2": "50171700", "HF-3": "50131800", "HF-4": "50121500", "HF-5": "50221100"}   # UNSPSC families


def money(v) -> str:
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def party(prefix: str, p: dict, role: str) -> dict:
    """The Party cluster under a Customer Party or Supplier Party prefix."""
    a = p["address"]
    v = {
        prefix + "Party/Endpoint ID": p["endpoint"],
        prefix + "Party/Party Identification/Party Identification Scheme": "Global Location Number (GS1)",
        prefix + "Party/Party Identification/Party Identification Value": p["gln"],
        prefix + "Party/Organization Name": p["name"],
        prefix + "Party/US Address/Address (Line 1)": a["line1"],
        prefix + "Party/US Address/Address (Line 2)": a.get("line2"),
        prefix + "Party/US Address/City Name": a["city"],
        prefix + "Party/US Address/US State Code": a["state"],
        prefix + "Party/US Address/US ZIP Code": a["zip"],
        prefix + "Party/US Address/Country Code ISO 3166": "US",
        prefix + "Party/US Address/Address Use": "work",
        prefix + "Party/Party Legal Entity/Registration Name": p["name"],
        prefix + "Party/Party Legal Entity/Company ID": p["company_id"],
        prefix + "Party/Party Contact/Contact Name": p["contact"]["name"],
        prefix + "Party/Party Contact/Contact Department": p["contact"]["department"],
        prefix + "Party/Party Contact/Contact Point/Phone Number": p["contact"]["phone"],
        prefix + "Party/Party Contact/Contact Point/Email Address": p["contact"]["email"],
    }
    return v


def order_values(n: int, rng: random.Random, year: int = 2026) -> tuple[dict, dict]:
    """The values of one order by label path, and its header facts (id, issue date, buyer) for the record."""
    issued = date(year, 1, 5) + timedelta(days=rng.randrange(0, 360))
    order_id = f"KM-PO-{year}-{n:06d}"
    lines = rng.sample(CATALOG, k=rng.randint(1, 6))
    dc = KESTREL["dc"]
    start = issued + timedelta(days=rng.randint(7, 14))
    v = {
        O + "Order Document/Customization ID": "https://axius-sdc.com/library/business/order-governed-record",
        O + "Order Document/Profile ID": "urn:axius-sdc:business-documents:profile:order-only:1",
        O + "Order Document/Order ID": order_id,
        O + "Order Document/Copy Indicator": False,
        O + "Order Document/Document UUID": f"{rng.getrandbits(32):08x}-{rng.getrandbits(16):04x}-4{rng.getrandbits(12):03x}-{rng.getrandbits(16):04x}-{rng.getrandbits(48):012x}",
        O + "Order Document/Issue Date": issued.isoformat(),
        O + "Order Document/Issue Time": f"{rng.randint(7, 17):02d}:{rng.randint(0, 59):02d}:00",
        O + "Order Document/Order Type": "Standard order",
        O + "Order Document/Note": "Deliver to the dock door named on the appointment; chilled lines at 2 to 4 degrees Celsius.",
        O + "Order Document/Document Currency": CURRENCY,
        O + "Order Document/Customer Reference": f"KM-BUY-{rng.randint(100, 999)}",
        O + "Order Document/Accounting Cost": "Grocery 4120",
        O + "Order Document/Line Count": Quantity(str(len(lines)), "items"),
        O + "Order Document/Validity Period/Date Range/Date Range Start": issued.isoformat(),
        O + "Order Document/Validity Period/Date Range/Date Range End": (issued + timedelta(days=30)).isoformat(),
        O + "Contract/Contract ID": "KM-HF-SA-2025-01",
        O + "Contract/Contract Issue Date": "2025-11-14",
        O + "Contract/Contract Type": "Supply agreement",
        O + "Buyer Customer Party/Customer Party/Supplier Assigned Account ID": "HF-CUST-00417",
        O + "Seller Supplier Party/Supplier Party/Customer Assigned Account ID": "KM-VEND-2291",
        O + "Delivery/Delivery ID": f"{order_id}-D1",
        O + "Delivery/Latest Delivery Date": (start + timedelta(days=3)).isoformat(),
        O + "Delivery/Delivery Location/Delivery Location ID": dc["gln"],
        O + "Delivery/Delivery Location/Delivery Location Name": dc["name"],
        O + "Delivery/Delivery Location/US Address/Address (Line 1)": dc["line1"],
        O + "Delivery/Delivery Location/US Address/City Name": dc["city"],
        O + "Delivery/Delivery Location/US Address/US State Code": dc["state"],
        O + "Delivery/Delivery Location/US Address/US ZIP Code": dc["zip"],
        O + "Delivery/Delivery Location/US Address/Country Code ISO 3166": "US",
        O + "Delivery/Requested Delivery Period/Date Range/Date Range Start": start.isoformat(),
        O + "Delivery/Requested Delivery Period/Date Range/Date Range End": (start + timedelta(days=3)).isoformat(),
        O + "Delivery Terms/Delivery Terms Code": "DAP",
        O + "Delivery Terms/Delivery Special Terms": "Appointment required 48 hours ahead; pallets to the retailer's pack specification in force on the delivery date.",
        O + "Payment Means/Payment Means": "Automated clearing house credit",
        O + "Payment Means/Payment Due Date": (issued + timedelta(days=30)).isoformat(),
        O + "Payment Terms/Payment Terms ID": "NET30-2/10",
        O + "Payment Terms/Note": "Net 30 days; 2 percent settlement discount for payment within 10 days.",
        O + "Payment Terms/Settlement Discount Percent": Quantity("2.0000", "%"),
        O + "Payment Terms/Payment Due Date": (issued + timedelta(days=30)).isoformat(),
        O + "Payment Terms/Settlement Period/Date Range/Date Range Start": issued.isoformat(),
        O + "Payment Terms/Settlement Period/Date Range/Date Range End": (issued + timedelta(days=10)).isoformat(),
    }
    v.update(party(O + "Buyer Customer Party/Customer Party/", KESTREL, "buyer"))
    v.update(party(O + "Seller Supplier Party/Supplier Party/", HALVORSEN, "seller"))
    total = Decimal("0")
    for i, (item_no, name, desc, gtin_body, price, per_case, kg, litre) in enumerate(lines, start=1):
        cases = rng.choice((6, 12, 18, 24, 36, 48))
        ext = Decimal(price) * cases
        total += ext
        L = O + f"Order Lines/Order Line {i}/Order Line/Line Item/"
        v.update({
            L + "Line ID": str(i),
            L + "Line Status": "No status",
            L + "Ordered Quantity": Quantity(str(cases), "CS"),
            L + "Line Extension Amount": Quantity(money(ext), CURRENCY),
            L + "Total Tax Amount": Quantity("0.00", CURRENCY),
            L + "Partial Delivery Allowed": False,
            L + "Back Order Allowed": True,
            L + "Price/Price Amount": Quantity(price + "00", CURRENCY),
            L + "Price/Base Quantity": Quantity("1", "CS"),
            L + "Price/Price Type": "Contract price",
            L + "Item/Item Name": name,
            L + "Item/Item Description": desc,
            L + "Item/Brand Name": "Halvorsen",
            L + "Item/Pack Quantity": Quantity(str(per_case), "items"),
            L + "Item/Buyer's Item Identification/Item Identification/Item Identification Scheme": "Buyer's item number",
            L + "Item/Buyer's Item Identification/Item Identification/Item Identification Value": f"KM-{10000 + int(item_no[3:])}",
            L + "Item/Seller's Item Identification/Item Identification/Item Identification Scheme": "Seller's item number",
            L + "Item/Seller's Item Identification/Item Identification/Item Identification Value": item_no,
            L + "Item/Standard Item Identification/Item Identification/Item Identification Scheme": "Global Trade Item Number (GS1)",
            L + "Item/Standard Item Identification/Item Identification/Item Identification Value": gs1_check(gtin_body),
            L + "Item/Commodity Classification/Item Classification Code": ITEM_CLASS[item_no[:4]],
            L + "Item/Tax Category/Tax Category ID": "E",
            L + "Item/Tax Category/Tax Category Name": "Exempt from tax",
            L + "Item/Tax Category/Tax Percent": Quantity("0.0000", "%"),
            L + "Item/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
            L + "Item/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
            L + "Item/Item Dimensions/Weight": Quantity(kg, "kg"),
            L + "Item/Item Dimensions/Volume": Quantity(litre, "L"),
        })
    v.update({
        O + "Tax Total/Tax Amount": Quantity("0.00", CURRENCY),
        O + "Tax Total/Tax Subtotal/Taxable Amount": Quantity(money(total), CURRENCY),
        O + "Tax Total/Tax Subtotal/Tax Amount": Quantity("0.00", CURRENCY),
        O + "Tax Total/Tax Subtotal/Tax Category/Tax Category ID": "E",
        O + "Tax Total/Tax Subtotal/Tax Category/Tax Category Name": "Exempt from tax",
        O + "Tax Total/Tax Subtotal/Tax Category/Tax Percent": Quantity("0.0000", "%"),
        O + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme ID": "IL-ROT",
        O + "Tax Total/Tax Subtotal/Tax Category/Tax Scheme/Tax Scheme Name": "Illinois Retailers' Occupation Tax",
        O + "Anticipated Monetary Total/Line Extension Total Amount": Quantity(money(total), CURRENCY),
        O + "Anticipated Monetary Total/Tax Exclusive Amount": Quantity(money(total), CURRENCY),
        O + "Anticipated Monetary Total/Tax Inclusive Amount": Quantity(money(total), CURRENCY),
        O + "Anticipated Monetary Total/Payable Amount": Quantity(money(total), CURRENCY),
    })
    return v, {"order_id": order_id, "issued": issued.isoformat(), "buyer": KESTREL["name"]}


def generate(orders: int, seed: str = "halvorsen-2026", year: int = 2026):
    """Yield (header, values, instance xml) for each order, the same sequence on every run."""
    rng = random.Random(seed)
    for n in range(1, orders + 1):
        values, h = order_values(n, rng, year)
        when = f"{h['issued']}T{rng.randint(7, 17):02d}:{rng.randint(0, 59):02d}:00"
        h["received_time"] = f"{rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}:00"   # when the supplier's translator read the document
        xml = record("Order", values, document_id=h["order_id"], buyer=h["buyer"], when=when,
                     source=(f"urn:kestrel:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order written from this record for the supplier"),
                     agent=RETAILER_SYSTEM, instance_id=cuid_generator(rng), rng=rng)
        yield h, values, xml


def main():
    from order import validate_ubl, write_order
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--orders", type=int, default=24)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "out", "halvorsen"))
    ap.add_argument("--seed", default="halvorsen-2026")
    a = ap.parse_args()
    n = 0
    for h, _values, xml in generate(a.orders, a.seed):
        write_record(os.path.join(a.out, "records"), "order", xml, name=h["order_id"].lower())
        ubl = write_order(xml)
        errors = validate_ubl(ubl)
        assert not errors, (h["order_id"], errors[:2])
        write_record(os.path.join(a.out, "ubl"), "ubl-order", ubl, name=h["order_id"].lower())
        n += 1
    print(f"{n} orders written to {os.path.abspath(a.out)}: the records and their UBL 2.3 projections, every projection conformant")


if __name__ == "__main__":
    main()
