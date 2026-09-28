#!/usr/bin/env python3
"""
Generate the year of orders for both stacks.

The retailer, Kestrel Mercantile, is the system of record for its purchase orders: each order is
generated as a record of the published Order model and loaded into the retailer's stack. On the way
out of that stack every record is written as a UBL 2.3 Order document into
``app/sdc4/import_data/exchange/``. On the way in to the supplier's stack, Halvorsen Foods, each
document is read back into a record by the translator: the supplier's record names the document it
came from as the PROV entity the activity used, the translator as the agent, and the document as the
audit's location. Two stacks, one component set, the document a projection between them.

    python datagen/generate_all.py            # HALVORSEN_ORDERS=52 by default: a year of weekly orders
    HALVORSEN_ORDERS=260 python datagen/generate_all.py

Writes app/sdc4/import_data/retailer/order/, app/sdc4/import_data/exchange/, app/sdc4/import_data/halvorsen/order/.
Every UBL document is validated against the OASIS Order schema before it is written.
"""
from __future__ import annotations

import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ubl"))
from halvorsen import generate  # noqa: E402
from order import read_order, validate_ubl, write_order  # noqa: E402
from shared import IMPORT_ROOT, SUPPLIER_TRANSLATOR, record, write_record  # noqa: E402

ORDERS = int(os.environ.get("HALVORSEN_ORDERS", "52"))
SEED = os.environ.get("HALVORSEN_SEED", "halvorsen-2026")


def main():
    t0 = time.time()
    retailer_dir = os.path.join(IMPORT_ROOT, "retailer", "order")
    exchange_dir = os.path.join(IMPORT_ROOT, "exchange")
    supplier_dir = os.path.join(IMPORT_ROOT, "halvorsen", "order")
    for d in (retailer_dir, exchange_dir, supplier_dir):
        os.makedirs(d, exist_ok=True)
        for f in glob.glob(os.path.join(d, "*.xml")):
            os.remove(f)
    print("=" * 60)
    print(f"HalvorsenDemo generator: {ORDERS} orders, seed {SEED!r}")
    print("=" * 60)
    n = 0
    for h, _values, xml in generate(ORDERS, seed=SEED):
        # 1. the retailer's record, the system of record
        write_record(retailer_dir, "order", xml, name=h["order_id"].lower())
        # 2. the document written on the way out: a conformant UBL 2.3 Order
        ubl = write_order(xml)
        errors = validate_ubl(ubl)
        assert not errors, (h["order_id"], errors[:2])
        path = os.path.join(exchange_dir, f"{h['order_id']}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + ubl)
        # 3. the document read on the way in: the supplier's record, from the document alone
        with open(path, encoding="utf-8") as f:
            received = f.read()
        values = read_order(received)
        supplier = record("Order", values, document_id=h["order_id"], buyer=h["buyer"], when=f"{h['issued']}T{h['received_time']}",
                          source=(f"urn:kestrel:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order received from Kestrel Mercantile"),
                          agent=SUPPLIER_TRANSLATOR, current_state="OrderProcessing")
        write_record(supplier_dir, "order", supplier, name=h["order_id"].lower())
        n += 1
    print(f"  retailer records  {n:>6,}   {retailer_dir}")
    print(f"  UBL documents     {n:>6,}   {exchange_dir}")
    print(f"  supplier records  {n:>6,}   {supplier_dir}")
    print(f"Completed in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
