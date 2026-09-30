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


def key_documents() -> tuple[dict, dict]:
    issuer = json.loads((HERE / "issuer-keys.json").read_text(encoding="utf-8"))
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "keys").glob("*-key.json"))]
    parties = {"keys": [k for d in docs for k in d.get("keys", [])]} if docs and "keys" in docs[0] else (docs[0] if docs else None)
    if docs and "keys" not in docs[0]:
        parties = {}
        for d in docs:
            parties.update(d)
    return issuer, parties


def check(entry: dict, issuer: dict, parties: dict, import_root: str = IMPORT_ROOT, dmlib: str = DMLIB) -> dict:
    receipt = json.loads((HERE / "receipts" / f"{entry['receipt_id']}.json").read_text(encoding="utf-8"))
    payload_path = Path(import_root) / "retailer" / "receipt_advice" / entry["record_file"]
    payload = payload_path.read_bytes() if payload_path.exists() else None
    schema_path = Path(dmlib) / f"dm-{receipt['schema_ct_id']}.xsd"
    schema_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest() if schema_path.exists() else None
    result = verify(receipt, issuer_keys=issuer, party_keys=parties if entry["decision"] == "PERMIT" else None, payload=payload)
    return {
        "receipt_advice_id": entry["receipt_advice_id"], "receipt_id": entry["receipt_id"], "decision": receipt["governance"]["decision"], "kind": entry["kind"],
        "verified": bool(result.ok), "failures": list(result.failures), "record": dict(result.record) if hasattr(result, "record") and isinstance(result.record, dict) else str(getattr(result, "record", "")),
        "payload_present": payload is not None, "payload_matches": payload is not None and hashlib.sha256(payload).hexdigest() == receipt["payload_hash"],
        "schema_matches": schema_hash == receipt["schema_hash"], "triggers": len(receipt.get("settlement", {}).get("triggers", [])), "parties": receipt.get("settlement", {}).get("parties", []),
        "timestamp": receipt.get("timestamp", ""),
    }


def main() -> int:
    index_path = HERE / "index.json"
    if not index_path.exists():
        print("no settlements yet: run settlement/settle.py with an issuer token")
        return 0
    issuer, parties = key_documents()
    bad = 0
    for entry in json.loads(index_path.read_text(encoding="utf-8")):
        r = check(entry, issuer, parties)
        ok = r["verified"] and r["payload_matches"] and r["schema_matches"]
        bad += not ok
        print(f"{'VERIFIED' if ok else 'FAILED  '} {r['receipt_advice_id']} {r['decision']:<6} receipt {r['receipt_id']} triggers {r['triggers']} payload {'ok' if r['payload_matches'] else 'MISMATCH'} schema {'ok' if r['schema_matches'] else 'MISMATCH'}"
              + (f"  {r['failures']}" if r["failures"] else ""))
    print(f"{bad} failed" if bad else "every Receipt verifies against the record bytes and the schema bytes held here")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
