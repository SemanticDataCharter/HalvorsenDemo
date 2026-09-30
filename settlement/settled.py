"""
The settled records: for every PERMIT Receipt in settlement/, a new record of the same document in the state the
settlement reached, whose provenance names the Receipt: a receipt advice in the retailer's store, or the Torvale
order in the supplier's.

A Receipt names the record it settled by the hash of its bytes. The generator is deterministic, so the
bytes it writes at `make generate` are the bytes the issuer signed; this module checks that before it
writes anything, and writes nothing for a record whose bytes have changed. The settled record carries
the same values as the original, its state OrderProcessing, the Receipt as the PROV entity the settlement
activity used, and the settlement agent; the original stays in the store beside it, so the two records
of one receipt advice show the transition and what permitted it.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "datagen"))
sys.path.insert(0, str(ROOT / "ubl"))
sys.path.insert(0, str(HERE))
from entries import norm  # noqa: E402
from instance import read_tree  # noqa: E402
from order import TORVALE  # noqa: E402
from receipt_advice import KR, RECEIPT_CT  # noqa: E402
from schema import Schema  # noqa: E402
from shared import LIBRARY_VERSION, cuid_generator, record, write_record  # noqa: E402

ROOTS = {RECEIPT_CT: KR, TORVALE.ct: TORVALE.root}


def settlement_agent(system: str, name: str) -> tuple[str, str, str]:
    return (f"urn:{system}:settlement-agent:{LIBRARY_VERSION}", name, "Settled")


def index() -> list[dict]:
    p = HERE / "index.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def write_settled_records(import_root: str) -> tuple[int, int]:
    """Write one settled record per PERMIT Receipt whose record bytes match; return (written, skipped)."""
    written = skipped = 0
    for entry in map(norm, index()):
        if entry["kind"] != "permit" or entry["decision"] != "PERMIT":
            continue
        directory = os.path.join(import_root, *entry["record_dir"].split("/"))
        path = Path(directory) / entry["record_file"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["record_sha256"]:
            print(f"  settlement: {entry['record_file']} is not the bytes Receipt {entry['receipt_id']} names; no settled record written")
            skipped += 1
            continue
        receipt = json.loads((HERE / "receipts" / f"{entry['receipt_id']}.json").read_text(encoding="utf-8"))
        text = path.read_text(encoding="utf-8")
        root = ROOTS[entry["model_ct"]]
        values = read_tree(text, Schema.for_dm(entry["model_ct"])).get(*root).paths(root)
        did = entry["document_id"]
        when = receipt["timestamp"][:19]
        xml = record(entry["model"], values, document_id=did, buyer=entry["buyer"], when=when,
                     source=(f"urn:vsl:receipt:{receipt['receipt_id']}", f"{receipt['receipt_id']}.json",
                             f"Settlement Receipt {receipt['receipt_id']}: governance {receipt['governance']['decision']} for {entry['from_state']} to {entry['target_state']}, "
                             f"condition {receipt['settlement']['condition_hash'][:16]}, payload {receipt['payload_hash'][:16]}, {len(receipt['settlement'].get('triggers', []))} triggers"),
                     agent=settlement_agent(*entry["agent"]), current_state=entry["target_state"], instance_id=cuid_generator(random.Random(receipt["receipt_id"])))
        write_record(directory, entry["record_dir"].rsplit("/", 1)[-1], xml, name=f"{did.lower()}-settled")
        written += 1
    return written, skipped


if __name__ == "__main__":
    from shared import IMPORT_ROOT
    w, s = write_settled_records(IMPORT_ROOT)
    print(f"{w} settled records written, {s} skipped")
