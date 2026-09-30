"""
The index of Receipts held (settlement/index.json), one entry a Receipt, normalized.

The first Receipts settled receipt advices between Kestrel Mercantile and Halvorsen Foods, and their entries name the
record by receipt_advice_id under retailer/receipt_advice. Later entries may name a record of another model held in
another stack's import directory (a Torvale Order in the supplier's); every field a reader needs has a default, so
the older entries read the same as the newer.
"""
from __future__ import annotations

RECEIPT_ADVICE_CT = "tog0v0p1zit1xwpxysxwpf3d"

#: model ct -> (title, the label of the document's identifier, the retailer whose record it is, the settlement agent's system and name)
MODELS = {
    RECEIPT_ADVICE_CT: ("Receipt Advice", "Receipt Advice ID", "Kestrel Mercantile, Inc.", ("kestrel", "Kestrel Mercantile settlement agent")),
    "cq1fjrvyn0fxl1kyk9y3kr1w": ("Torvale Order", "Order ID", "Torvale Markets, Inc.", ("halvorsen", "Halvorsen Foods settlement agent")),
}


def norm(entry: dict) -> dict:
    """The entry with every field filled: the model, the record directory, the identifier and the state it left."""
    e = dict(entry)
    e.setdefault("model_ct", RECEIPT_ADVICE_CT)
    title, id_label, buyer, agent = MODELS[e["model_ct"]]
    e.setdefault("model", title)
    e.setdefault("id_label", id_label)
    e.setdefault("buyer", buyer)
    e.setdefault("document_id", e.get("receipt_advice_id"))
    e.setdefault("record_dir", "retailer/receipt_advice")
    e.setdefault("from_state", "OrderProblem")
    e["agent"] = agent
    return e
