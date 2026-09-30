"""The Settlement Receipts held in settlement/: each names a record the generator still writes byte for byte, and verifies with nothing from the issuer."""
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "settlement"))
sys.path.insert(0, os.path.join(ROOT, "datagen"))
from entries import norm  # noqa: E402
INDEX = os.path.join(ROOT, "settlement", "index.json")
pytestmark = pytest.mark.skipif(not os.path.exists(INDEX), reason="no settlements issued yet (make settle)")


def entries():
    return json.load(open(INDEX, encoding="utf-8"))


def test_every_receipt_names_bytes_the_generator_still_writes(tmp_path):
    import subprocess
    env = dict(os.environ, HALVORSEN_IMPORT_DIR=str(tmp_path), HALVORSEN_ORDERS="52")
    subprocess.run([sys.executable, os.path.join(ROOT, "datagen", "generate_all.py")], check=True, env=env, capture_output=True)
    for e in map(norm, entries()):
        path = tmp_path.joinpath(*e["record_dir"].split("/")) / e["record_file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == e["record_sha256"], e["document_id"]
        receipt = json.load(open(os.path.join(ROOT, "settlement", "receipts", f"{e['receipt_id']}.json"), encoding="utf-8"))
        assert receipt["payload_hash"] == e["record_sha256"]
    settled = sorted(p.name for p in (tmp_path / "retailer" / "receipt_advice").glob("*-settled.xml"))
    assert len(settled) == sum(1 for e in map(norm, entries()) if e["kind"] == "permit" and e["decision"] == "PERMIT" and e["model"] == "Receipt Advice")
    for name in settled:
        xml = (tmp_path / "retailer" / "receipt_advice" / name).read_text(encoding="utf-8")
        assert "<current-state>OrderProcessing</current-state>" in xml and "urn:vsl:receipt:" in xml and "Kestrel Mercantile settlement agent" in xml
    torvale = sorted(p.name for p in (tmp_path / "halvorsen" / "torvale_order").glob("*-settled.xml"))
    assert len(torvale) == sum(1 for e in map(norm, entries()) if e["kind"] == "permit" and e["decision"] == "PERMIT" and e["model"] == "Torvale Order")
    for name in torvale:
        xml = (tmp_path / "halvorsen" / "torvale_order" / name).read_text(encoding="utf-8")
        assert "<current-state>OrderInTransit</current-state>" in xml and "urn:vsl:receipt:" in xml and "Halvorsen Foods settlement agent" in xml


def test_every_receipt_verifies_offline_against_the_record_and_schema_bytes(tmp_path):
    import subprocess
    import verify_all
    env = dict(os.environ, HALVORSEN_IMPORT_DIR=str(tmp_path), HALVORSEN_ORDERS="52")
    subprocess.run([sys.executable, os.path.join(ROOT, "datagen", "generate_all.py")], check=True, env=env, capture_output=True)
    keyset = verify_all.key_documents()
    for e in entries():
        r = verify_all.check(e, keyset, import_root=str(tmp_path))
        assert r["payload_matches"] and r["schema_matches"], (e["receipt_id"], r)
        assert r["verified"], (e["receipt_id"], r["failures"])
        if e["kind"] == "permit":
            assert r["decision"] == "PERMIT" and r["triggers"] == 2
        else:
            assert r["decision"] == "DENY"
