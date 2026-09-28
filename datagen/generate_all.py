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

Then the supplier answers: each response is generated as a record in the supplier's stack, written as a UBL 2.3
OrderResponse into the exchange, and read back into the retailer's stack by the retailer's translator.

Writes app/sdc4/import_data/{retailer,halvorsen}/{order,order_response}/ and app/sdc4/import_data/exchange/.
Every UBL document is validated against the OASIS schema of its type before it is written.
"""
from __future__ import annotations

import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ubl"))
from halvorsen import generate  # noqa: E402
from halvorsen_responses import respond  # noqa: E402
from order import read_order, validate_ubl, write_order  # noqa: E402
from order_response import read_order_response, validate_ubl_response, write_order_response  # noqa: E402
from shared import IMPORT_ROOT, RETAILER_TRANSLATOR, SUPPLIER_TRANSLATOR, record, write_record  # noqa: E402

ORDERS = int(os.environ.get("HALVORSEN_ORDERS", "52"))
SEED = os.environ.get("HALVORSEN_SEED", "halvorsen-2026")


def main():
    import random
    t0 = time.time()
    dirs = {name: os.path.join(IMPORT_ROOT, *parts) for name, parts in {
        "retailer_orders": ("retailer", "order"), "supplier_orders": ("halvorsen", "order"),
        "supplier_responses": ("halvorsen", "order_response"), "retailer_responses": ("retailer", "order_response"), "exchange": ("exchange",)}.items()}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
        for f in glob.glob(os.path.join(d, "*.xml")):
            os.remove(f)
    print("=" * 60)
    print(f"HalvorsenDemo generator: {ORDERS} orders and their responses, seed {SEED!r}")
    print("=" * 60)
    rng = random.Random(SEED + ":responses")
    n = 0
    for h, values, xml in generate(ORDERS, seed=SEED):
        # 1. the retailer's order, the system of record; written out as a UBL Order; read in by the supplier
        write_record(dirs["retailer_orders"], "order", xml, name=h["order_id"].lower())
        ubl = write_order(xml)
        assert not validate_ubl(ubl), (h["order_id"], validate_ubl(ubl)[:2])
        path = os.path.join(dirs["exchange"], f"{h['order_id']}.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + ubl)
        with open(path, encoding="utf-8") as f:
            received = read_order(f.read())
        supplier_order = record("Order", received, document_id=h["order_id"], buyer=h["buyer"], when=f"{h['issued']}T{h['received_time']}",
                                source=(f"urn:kestrel:order:{h['order_id']}:ubl", f"{h['order_id']}.xml", "The UBL 2.3 Order received from Kestrel Mercantile"),
                                agent=SUPPLIER_TRANSLATOR, current_state="OrderProcessing")
        write_record(dirs["supplier_orders"], "order", supplier_order, name=h["order_id"].lower())
        # 2. the supplier's response, its system of record; written out as a UBL OrderResponse; read in by the retailer
        rh, rvalues, rxml = respond(h, values, rng)
        write_record(dirs["supplier_responses"], "order_response", rxml, name=rh["response_id"].lower())
        rubl = write_order_response(rxml)
        assert not validate_ubl_response(rubl), (rh["response_id"], validate_ubl_response(rubl)[:2])
        rpath = os.path.join(dirs["exchange"], f"{rh['response_id']}.xml")
        with open(rpath, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + rubl)
        with open(rpath, encoding="utf-8") as f:
            rreceived = read_order_response(f.read())
        retailer_response = record("Order Response", rreceived, document_id=rh["response_id"], buyer=rh["seller"], when=f"{rh['issued']}T{rng.randint(9, 17):02d}:{rng.randint(0, 59):02d}:00",
                                   source=(f"urn:halvorsen:response:{rh['response_id']}:ubl", f"{rh['response_id']}.xml", "The UBL 2.3 OrderResponse received from Halvorsen Foods"),
                                   agent=RETAILER_TRANSLATOR, current_state="OrderProcessing")
        write_record(dirs["retailer_responses"], "order_response", retailer_response, name=rh["response_id"].lower())
        n += 1
    for name, d in dirs.items():
        print(f"  {name:<20} {len(glob.glob(os.path.join(d, '*.xml'))):>6,}   {d}")
    print(f"Completed in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
