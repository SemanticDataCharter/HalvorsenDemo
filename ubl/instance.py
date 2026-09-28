"""
Read a generated instance back into a tree of labels and values: the inverse of the engine's fill.

The engine (datagen/engine.py) fills a model's template from label paths; a writer needs the
same view of an instance it did not build, so this module walks the instance by its labels
and the schema's component types, never by element ids:

    tree = read_tree(xml_text, Schema.for_dm(ct))
    order = tree.get("Order Governed Record", "Order")
    order.leaf("Order Document", "Order ID")                  -> "PO-2026-000412"
    order.leaf("Anticipated Monetary Total", "Payable Amount") -> Quantity("1834.50", "USD")

A leaf's value has the engine's shape: a string for XdString, XdToken and XdTemporal, a
``Quantity(magnitude, unit)`` for XdQuantity and XdCount, a bool for XdBoolean, an
``(ordinal, symbol)`` pair for XdOrdinal, and an ``EV(code)`` where the instance states an
absence. ``paths()`` flattens a tree into the label paths the engine takes, so a record can
be compared with what a document round trip gives back.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "datagen"))
from engine import EV, EV_NAMES, Quantity, _tag  # noqa: E402
from schema import Schema  # noqa: E402

CONTAINERS = ("location", "party-details", "workflow")   # non-component elements the walk looks inside


@dataclass
class Node:
    label: str
    value: Any = None
    kids: dict[str, "Node"] = field(default_factory=dict)

    def get(self, *labels: str) -> "Node | None":
        node = self
        for label in labels:
            node = node.kids.get(label)
            if node is None:
                return None
        return node

    def leaf(self, *labels: str) -> Any:
        node = self.get(*labels)
        return None if node is None else node.value

    def paths(self, prefix: tuple[str, ...] = ()) -> dict[str, Any]:
        """Every leaf under this node by its label path from the prefix, joined the way the engine keys them."""
        out = {}
        for label, kid in self.kids.items():
            p = prefix + (label,)
            if kid.kids:
                out.update(kid.paths(p))
            elif kid.value is not None:
                out["/".join(p)] = kid.value
        return out


def read_tree(xml_text: str, schema: Schema) -> Node:
    root = etree.fromstring(xml_text.encode() if isinstance(xml_text, str) else xml_text)
    top = Node("")
    _walk(root, top, schema)
    return top


def _walk(el, node: Node, schema: Schema):
    for child in el:
        tag = _tag(child)
        if tag.startswith("ms-"):
            ct = tag[3:]
            base = schema.base.get(ct, "")
            if base == "XdAdapterType":
                _walk(child, node, schema)
                continue
            label = (child.findtext("label") or "").strip()
            if base in ("ClusterType", "AuditType", "PartyType"):
                sub = Node(label)
                node.kids[label] = sub
                _walk(child, sub, schema)
            else:
                node.kids[label] = Node(label, value=_value(child, base))
        elif tag in CONTAINERS:
            _walk(child, node, schema)


def _value(el, base: str):
    for c in el:
        t = _tag(c)
        if t in EV_NAMES:
            return EV(t)
    if base == "XdStringType":
        return el.findtext("xdstring-value")
    if base == "XdTokenType":
        return el.findtext("xdtoken-value")
    if base == "XdTemporalType":
        return next((c.text for c in el if _tag(c).startswith("xdtemporal-")), None)
    if base in ("XdQuantityType", "XdCountType", "XdFloatType", "XdDoubleType"):
        kind = {"XdQuantityType": "xdquantity", "XdCountType": "xdcount", "XdFloatType": "xdfloat", "XdDoubleType": "xddouble"}[base]
        units = el.find(f"{kind}-units")
        return Quantity(el.findtext(f"{kind}-value"), units.findtext("xdstring-value") if units is not None else "")
    if base == "XdBooleanType":
        return el.find("true-value") is not None
    if base == "XdOrdinalType":
        return (el.findtext("ordinal"), el.findtext("symbol"))
    if base == "XdLinkType":
        return el.findtext("link")
    if base == "XdFileType":
        return el.findtext("uri")
    return None
