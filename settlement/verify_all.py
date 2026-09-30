#!/usr/bin/env python3
"""
Verify every Receipt in settlement/ with nothing from the issuer: the issuer's published key document as
saved here, the parties' key documents, the model's schema bytes in mediafiles/dmlib, and the record's
own bytes as the generator writes them.

    python settlement/verify_all.py            # after make generate

Prints one line per Receipt and exits non-zero if any fails. This is what the demo page runs, and what
`make verify-settlements` runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "datagen"))
from shared import DMLIB, IMPORT_ROOT  # noqa: E402
from sdcreceipt import verify  # noqa: E402
from sdcreceipt.party import KeySet, load_key_set_file  # noqa: E402


def key_documents():
    """Every key document held here, merged into one key set: the issuer's as saved, and each party's."""
    keyset = KeySet()
    for path in [HERE / "issuer-keys.json"] + sorted((HERE / "keys").glob("*-key.json")):
        if path.exists():
            keyset.merge(load_key_set_file(path))
    return keyset


def split_keys(receipt: dict, keyset: KeySet):
    """The Receipt says which key ids signed it (the issuer's) and which are parties; the verifier wants them apart."""
    issuer_ids = {sig.get("key_id") for sig in receipt.get("signatures", []) if isinstance(sig, dict)}
    issuer, parties = KeySet(), KeySet()
    for key_id, key in keyset.items():
        target = issuer if key_id in issuer_ids else parties
        target[key_id] = key
        if key_id in keyset.status:
            target.status[key_id] = keyset.status[key_id]
    return issuer, (parties or None)


def expected_failures(receipt: dict, result) -> tuple[list, bool]:
    """A DENY Receipt attests a refusal and accepts no triggers, so its settlement can never be complete; every other check must pass."""
    deny = receipt.get("governance", {}).get("decision") == "DENY"
    failures = [f for f in result.failures if not (deny and getattr(f, "name", "") == "settlement.complete")]
    return [str(f) for f in failures], not failures


def check(entry: dict, keyset: KeySet, import_root: str = IMPORT_ROOT, dmlib: str = DMLIB) -> dict:
    receipt = json.loads((HERE / "receipts" / f"{entry['receipt_id']}.json").read_text(encoding="utf-8"))
    issuer, parties = split_keys(receipt, keyset)
    payload_path = Path(import_root) / "retailer" / "receipt_advice" / entry["record_file"]
    payload = payload_path.read_bytes() if payload_path.exists() else None
    schema_path = Path(dmlib) / f"dm-{receipt['schema_ct_id']}.xsd"
    schema_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest() if schema_path.exists() else None
    result = verify(receipt, issuer_keys=issuer, party_keys=parties if entry["decision"] == "PERMIT" else None, payload=payload)
    failures, verified = expected_failures(receipt, result)
    return {
        "receipt_advice_id": entry["receipt_advice_id"], "receipt_id": entry["receipt_id"], "decision": receipt["governance"]["decision"], "kind": entry["kind"],
        "verified": verified, "failures": failures, "record": dict(result.record) if hasattr(result, "record") and isinstance(result.record, dict) else str(getattr(result, "record", "")),
        "payload_present": payload is not None, "payload_matches": payload is not None and hashlib.sha256(payload).hexdigest() == receipt["payload_hash"],
        "schema_matches": schema_hash == receipt["schema_hash"], "triggers": len(receipt.get("settlement", {}).get("triggers", [])), "parties": receipt.get("settlement", {}).get("parties", []),
        "timestamp": receipt.get("timestamp", ""),
    }


def main() -> int:
    index_path = HERE / "index.json"
    if not index_path.exists():
        print("no settlements yet: run settlement/settle.py with an issuer token")
        return 0
    keyset = key_documents()
    bad = 0
    for entry in json.loads(index_path.read_text(encoding="utf-8")):
        r = check(entry, keyset)
        ok = r["verified"] and r["payload_matches"] and r["schema_matches"]
        bad += not ok
        print(f"{'VERIFIED' if ok else 'FAILED  '} {r['receipt_advice_id']} {r['decision']:<6} receipt {r['receipt_id']} triggers {r['triggers']} payload {'ok' if r['payload_matches'] else 'MISMATCH'} schema {'ok' if r['schema_matches'] else 'MISMATCH'}"
              + (f"  {r['failures']}" if r["failures"] else ""))
    print(f"{bad} failed" if bad else "every Receipt verifies against the record bytes and the schema bytes held here")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
