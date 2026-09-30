#!/usr/bin/env python3
"""
Settle the deduction on every receipt advice in the OrderProblem state, live, against the issuer.

    SDCRECEIPT_TOKEN=... python settlement/settle.py        # or the token in settlement/.token (gitignored)

For each retailer receipt advice whose state is OrderProblem the script writes the deduction notice
(the condition: the invoice, three percent, the pallets and the rule each failed), asks the issuer to
settle the transition OrderProblem to OrderProcessing between the two parties, has both parties sign
their triggers and submits them, and fetches the Receipt as it finally stands. The first record is
also asked to go straight to OrderDelivered, which governance refuses: the DENY Receipt is kept beside
the others. Everything lands under settlement/: the conditions, the Receipts, the issuer's responses,
the parties' key documents and the issuer's, and index.json naming which record each Receipt names by
its bytes. Nothing here runs at `make demo`; `settlement/settled.py` and the demo page read what this
wrote, and `settlement/verify_all.py` verifies it with nothing from the issuer.

Each Receipt costs the issuer's account one credit. The parties' private keys stay in settlement/keys/
and are not committed; their key documents are.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "datagen"))
sys.path.insert(0, str(ROOT / "ubl"))
from invoice import INVOICE_CT, IR  # noqa: E402
from receipt_advice import KR, RECEIPT_CT  # noqa: E402
from instance import read_tree  # noqa: E402
from schema import Schema  # noqa: E402
from shared import IMPORT_ROOT  # noqa: E402
from sdcreceipt import issue  # noqa: E402
from sdcreceipt.party import generate_key, key_document, load_private_key, sign_trigger, write_private_key  # noqa: E402

ENDPOINT = os.environ.get("HALVORSEN_SETTLE_ENDPOINT", "https://sdcstudio.axius-sdc.com/api/v1/vsl/settle")
BASE = ENDPOINT.rsplit("/settle", 1)[0]
ORIGIN = ENDPOINT.split("/api/", 1)[0]
#: The two parties. The issuer fetches each party's key document over HTTPS when a trigger arrives, so the identifiers
#: must resolve: fictitious companies own no domain, so their documents are published on the company site under a path
#: for this demonstration. The verifier here takes the same documents from settlement/keys/ and never fetches them.
PARTIES = {"kestrel": "https://axius-sdc.com/vsl/parties/kestrel-mercantile/vsl-key.json", "halvorsen": "https://axius-sdc.com/vsl/parties/halvorsen-foods/vsl-key.json"}
DEDUCTION_PERCENT = Decimal("3")
KEYS = HERE / "keys"
CONDITIONS = HERE / "conditions"
RECEIPTS = HERE / "receipts"
RESPONSES = HERE / "responses"


def token() -> str:
    t = os.environ.get("SDCRECEIPT_TOKEN") or ((HERE / ".token").read_text().strip() if (HERE / ".token").exists() else "")
    if not t:
        raise SystemExit("no token: set SDCRECEIPT_TOKEN or write it to settlement/.token (gitignored)")
    return t


def party_keys() -> dict:
    """The parties' keys: generated on first use, the private key kept here and the key document beside it."""
    KEYS.mkdir(exist_ok=True)
    out = {}
    for name, key_id in PARTIES.items():
        pem = KEYS / f"{name}.pem"
        if not pem.exists():
            key = generate_key()
            write_private_key(key, pem)
            (KEYS / f"{name}-key.json").write_text(json.dumps(key_document(key, key_id), indent=2) + "\n")
            print(f"  generated {name}'s key for {key_id}")
        out[name] = (key_id, load_private_key(pem))
    return out


def problem_records() -> list[Path]:
    files = sorted(glob.glob(os.path.join(IMPORT_ROOT, "retailer", "receipt_advice", "receipt_advice-*.xml")))
    return [Path(f) for f in files if "-settled" not in f and "<current-state>OrderProblem</current-state>" in Path(f).read_text(encoding="utf-8")]


def invoice_for(receipt_id: str):
    for f in sorted(glob.glob(os.path.join(IMPORT_ROOT, "retailer", "invoice", "invoice-*.xml"))):
        text = Path(f).read_text(encoding="utf-8")
        if f">{receipt_id}<" in text:
            return read_tree(text, Schema.for_dm(INVOICE_CT)).get(*IR)
    return None


def deduction_notice(record_text: str) -> dict:
    """The condition: what the retailer deducts, against which pallets and rules, on the record's own facts."""
    k = read_tree(record_text, Schema.for_dm(RECEIPT_CT)).get(*KR)
    receipt_id = k.leaf("Receipt Advice Document", "Receipt Advice ID")
    inv = invoice_for(receipt_id)
    payable = inv.leaf("Legal Monetary Total", "Payable Amount") if inv is not None else None
    amount = (Decimal(payable.magnitude) * DEDUCTION_PERCENT / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if payable else None
    pallets = []
    units = k.get("Receipt Shipment", "Received Handling Units")
    for n in range(1, 7):
        u = None if units is None else units.get(f"Received Handling Unit {n}", "Received Handling Unit")
        if u is None or u.leaf("Receiving Condition") != "Accepted with exception":
            continue
        pallets.append({
            "sscc": u.leaf("Transport Handling Unit ID"), "pallet_id": u.leaf("Pallet Identification", "Pallet ID"),
            "identifier_valid_to": u.leaf("Pallet Identification", "Date Range", "Date Range End"), "identifier_valid_on_receipt": u.leaf("Pallet ID Valid on Receipt"),
            "packed_to": u.leaf("Pack Specification Version"), "in_force_on_receipt": u.leaf("Pack Specification in Force"), "pack_specification_compliant": u.leaf("Pack Specification Compliant"),
            "received_on": u.leaf("Received Date"), "finding": u.leaf("Exception Description"),
        })
    return {
        "notice": "Deduction notice", "issued_by": "Kestrel Mercantile, Inc.", "to": "Halvorsen Foods, Inc.",
        "order_id": k.leaf("Order Reference", "Order ID"), "dispatch_id": k.leaf("Despatch Document Reference", "Document Reference", "Document Reference ID"),
        "receipt_id": receipt_id, "invoice_id": None if inv is None else inv.leaf("Invoice Document", "Invoice ID"),
        "received_on": k.leaf("Receipt Shipment", "Actual Delivery Date"),
        "deduction_percent": str(DEDUCTION_PERCENT), "deduction_amount": None if amount is None else {"magnitude": str(amount), "unit": payable.unit},
        "invoice_payable": None if payable is None else {"magnitude": payable.magnitude, "unit": payable.unit},
        "pallets": pallets,
        "resolution": "The deduction is agreed by both parties; the receipt advice moves from OrderProblem to OrderProcessing and the balance is paid against the invoice.",
    }


def post_json(url: str, body: dict) -> dict:
    issue.check_endpoint(url, what="submit URL")
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"error: {exc.code} from {url}: {exc.read().decode('utf-8', errors='replace')[:600]}")


def get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    tok = token()
    for d in (CONDITIONS, RECEIPTS, RESPONSES):
        d.mkdir(exist_ok=True)
    keys = party_keys()
    parties = [kid for kid, _ in keys.values()]
    (HERE / "issuer-keys.json").write_text(json.dumps(get_json(f"{ORIGIN}/.well-known/sdcstudio-signing-keys.json"), indent=2) + "\n")
    print(f"issuer {ORIGIN}: signing keys saved; parties {', '.join(parties)}")
    index_path = HERE / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    done = {(e["record_sha256"], e["kind"]) for e in index}   # a rerun picks up where it stopped; a Receipt already held is not bought twice
    records = problem_records()
    print(f"{len(records)} receipt advices in OrderProblem, {len(index)} Receipts already held")
    for i, path in enumerate(records):
        text = path.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        condition = deduction_notice(text)
        rid = condition["receipt_id"]
        (CONDITIONS / f"{rid}.json").write_text(json.dumps(condition, indent=2) + "\n")
        asks = [("permit", "OrderProcessing")] + ([("deny", "OrderDelivered")] if i == 0 else [])
        for kind, target in asks:
            if (sha, kind) in done:
                continue
            try:
                response = issue.settle(text, endpoint=ENDPOINT, token=tok, current_state="OrderProblem", target_state=target, condition=condition, parties=parties)
            except issue.SettleError as exc:   # a refusal the issuer explains (INDETERMINATE, a bad state) is kept as text, not as a Receipt
                print(f"  {rid} -> {target}: {exc}")
                (RESPONSES / f"{rid}-{kind}-error.txt").write_text(str(exc) + "\n")
                continue
            receipt, envelope = issue.split_response(response)
            receipt_id = receipt["receipt_id"]
            decision = receipt["governance"]["decision"]
            settleable = bool(envelope.get("governance", {}).get("settleable", decision == "PERMIT"))
            (RESPONSES / f"{receipt_id}.json").write_text(json.dumps(envelope, indent=2) + "\n")
            (RECEIPTS / f"{receipt_id}.json").write_text(json.dumps(receipt, indent=2) + "\n")   # as issued, before any trigger
            if settleable:
                for name, (kid, key) in keys.items():
                    trigger = sign_trigger(key, receipt, kid)
                    post_json(f"{BASE}/trigger", trigger)
                final = get_json(f"{BASE}/receipt/{receipt_id}")
                receipt = final.get("receipt", final) if isinstance(final, dict) else receipt
            (RECEIPTS / f"{receipt_id}.json").write_text(json.dumps(receipt, indent=2) + "\n")
            triggers = len(receipt.get("settlement", {}).get("triggers", []))
            print(f"  {rid} -> {target}: {decision}{'' if settleable else ' (not settleable)'}, receipt {receipt_id}, {triggers} triggers, {envelope.get('wallet', {}).get('charged', '?')} charged")
            index.append({"receipt_advice_id": rid, "order_id": condition["order_id"], "invoice_id": condition["invoice_id"], "record_file": path.name, "record_sha256": sha,
                          "kind": kind, "target_state": target, "receipt_id": receipt_id, "decision": decision, "settleable": settleable, "triggers": triggers,
                          "condition_file": f"conditions/{rid}.json", "settled_on": receipt.get("timestamp", "")[:10] or date.today().isoformat()})
            index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"{len(index)} Receipts in settlement/receipts; index.json written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
