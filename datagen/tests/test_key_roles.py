"""
The keys the settlements are verified against take their role from the file they are in, never from the Receipt
(issue #19). The arrangement this replaces let the Receipt's own `signatures` say which keys were the issuer's, after
a last-wins merge of every document: a party could add a key to its own document and sign as the issuer, the
defect sdcreceipt 4.3.3 removed from its command line (F-01, F-02; GHSA-gwhr-82j5-883w).
"""
import base64
import copy
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(__file__)
ROOT = Path(HERE, "..", "..").resolve()
sys.path.insert(0, str(ROOT / "settlement"))
sys.path.insert(0, str(ROOT / "datagen"))
INDEX = ROOT / "settlement" / "index.json"
pytestmark = pytest.mark.skipif(not INDEX.exists(), reason="no settlements issued yet (make settle)")

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, utils  # noqa: E402
from key_roles import key_roles  # noqa: E402
from sdcreceipt import verify  # noqa: E402
from sdcreceipt.party import PartyError, public_key_pem  # noqa: E402
from sdcreceipt.verify import canonical_content, receipt_digest  # noqa: E402


@pytest.fixture
def held(tmp_path):
    """A copy of the key documents held in settlement/, to tamper with."""
    shutil.copy(ROOT / "settlement" / "issuer-keys.json", tmp_path / "issuer-keys.json")
    (tmp_path / "keys").mkdir()
    for path in (ROOT / "settlement" / "keys").glob("*-key.json"):
        shutil.copy(path, tmp_path / "keys" / path.name)
    return tmp_path


def _a_permit_receipt():
    entry = next(e for e in json.loads(INDEX.read_text()) if e.get("decision") == "PERMIT")
    return json.loads((ROOT / "settlement" / "receipts" / f"{entry['receipt_id']}.json").read_text())


def test_the_held_documents_load_in_their_roles():
    issuer, parties = key_roles(ROOT / "settlement")
    assert set(issuer) == {k["key_id"] for k in json.loads((ROOT / "settlement" / "issuer-keys.json").read_text())["keys"]}
    receipt = _a_permit_receipt()
    assert set(receipt["settlement"]["parties"]) <= set(parties)
    assert not set(issuer) & set(parties)


def test_a_party_document_cannot_supply_an_issuer_key(held):
    """F-01 on the demo: a key a party publishes signs a forged Receipt; the Receipt names it as the issuer's."""
    attacker = ec.generate_private_key(ec.SECP256R1())
    party_doc = held / "keys" / "halvorsen-key.json"
    doc = json.loads(party_doc.read_text())
    doc["keys"].append({"key_id": "attacker-issuer-key", "alg": "ES256", "public_key_pem": public_key_pem(attacker),
                        "status": "active"})
    party_doc.write_text(json.dumps(doc))

    forged = copy.deepcopy(_a_permit_receipt())
    forged["payload_hash"] = "0" * 64
    forged["receipt_hash"] = hashlib.sha256(canonical_content(forged)).hexdigest()
    r, s = utils.decode_dss_signature(attacker.sign(receipt_digest(forged), ec.ECDSA(utils.Prehashed(hashes.SHA256()))))
    sig = base64.urlsafe_b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).rstrip(b"=").decode()
    forged["signatures"] = [{"alg": "ES256", "key_id": "attacker-issuer-key", "sig": sig}]

    issuer, parties = key_roles(held)
    assert "attacker-issuer-key" not in issuer
    result = verify(forged, issuer_keys=issuer, party_keys=parties)
    assert not result.ok
    assert "signature[attacker-issuer-key]" in {c.name for c in result.failures}


def test_a_party_document_republishing_an_issuer_key_id_is_refused(held):
    issuer_entry = json.loads((held / "issuer-keys.json").read_text())["keys"][0]
    party_doc = held / "keys" / "kestrel-key.json"
    doc = json.loads(party_doc.read_text())
    doc["keys"].append(issuer_entry)
    party_doc.write_text(json.dumps(doc))
    with pytest.raises(PartyError, match="one role"):
        key_roles(held)


def test_two_party_documents_claiming_one_key_id_are_refused(held):
    """F-02: last-wins would let the later document replace the key or clear a revocation."""
    first = json.loads((held / "keys" / "kestrel-key.json").read_text())
    (held / "keys" / "zz-copy-key.json").write_text(json.dumps(first))
    with pytest.raises(PartyError, match="exactly one document"):
        key_roles(held)
