"""
The keys every Receipt here is verified against, each in the role the verifier gives it.

The issuer's published key document, as saved (issuer-keys.json), supplies the issuer's keys; each party's key
document (keys/*-key.json) supplies that party's. **The roles come from which file a key is in, never from the
Receipt.** Letting the Receipt's own `signatures` say which keys are the issuer's lets a party key sign as the
issuer, and merging documents last-wins lets a later document replace a key or clear a revocation: the two
defects sdcreceipt 4.3.3 removed from its own command line (Timothy Lee's 4.3.x review, F-01 and F-02;
GHSA-gwhr-82j5-883w). `settlement/verify_all.py` and the Settlements page both load keys here, so they cannot
drift apart.
"""
from __future__ import annotations

from pathlib import Path


def key_roles(settlement_dir: Path):
    """
    ``(issuer_keys, party_keys)`` from the documents held in ``settlement_dir``.

    Each document is added with ``KeySet.add_document``, which refuses a key_id another document already supplied,
    and a key_id in both roles is refused. Raises ``sdcreceipt.party.PartyError`` when either happens, or when a
    document cannot be read; ``party_keys`` is None when no party document is held.
    """
    from sdcreceipt.party import KeySet, PartyError, load_key_set_file

    settlement_dir = Path(settlement_dir)
    issuer = KeySet()
    issuer_doc = settlement_dir / "issuer-keys.json"
    if issuer_doc.exists():
        issuer.add_document(load_key_set_file(issuer_doc), f"issuer document {issuer_doc.name}")

    parties = KeySet()
    for path in sorted((settlement_dir / "keys").glob("*-key.json")):
        parties.add_document(load_key_set_file(path), f"party document {path.name}")

    both = sorted(set(issuer) & set(parties))
    if both:
        raise PartyError(
            f"key_id {both[0]!r} appears in both the issuer's document and a party's. "
            "One key has one role; refusing to guess which."
        )
    return issuer, (parties or None)
