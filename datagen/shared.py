"""
Shared glue for the business document generators and readers.

A generator (or a reader of a document received) names the values a record has by label
path in the published model and calls ``record()``. The engine fills the model's own
instance template; the schema decides everything else. Every record states where it came
from: the PROV activity that produced it, the agent (the translator or the generator), the
document the activity used as the PROV entity, the audit event, and the Business Document
Audit naming the translator as the system and the document as the location. The record's
subject is the order identifier; the provider is the buyer.
"""
from __future__ import annotations

import os
import random
import re
from datetime import datetime

from engine import Template
from schema import DMLIB, Schema

ROOT = os.path.join(os.path.dirname(__file__), "..")
LIBRARY_VERSION = open(os.path.join(ROOT, "app", "sdc4", "VERSION"), encoding="utf-8").read().strip()
IMPORT_ROOT = os.environ.get("HALVORSEN_IMPORT_DIR") or os.path.join(ROOT, "app", "sdc4", "import_data")
#: The retailer's order system generates its records; the supplier's translator reads the documents it receives.
GENERATOR = "Kestrel Mercantile order system"
GENERATOR_ID = f"urn:kestrel:order-system:{LIBRARY_VERSION}"
TRANSLATOR = "Halvorsen Foods document translator"
TRANSLATOR_ID = f"urn:halvorsen:translator:{LIBRARY_VERSION}"
RETAILER_SYSTEM = (GENERATOR_ID, GENERATOR, "Generated")
SUPPLIER_TRANSLATOR = (TRANSLATOR_ID, TRANSLATOR, "Read")
_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def cuid_generator(rng: random.Random | None = None) -> str:
    r = rng or random
    return r.choice(_ID_ALPHABET[:26]) + "".join(r.choices(_ID_ALPHABET, k=23))


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


# ─── Models ──────────────────────────────────────────────────────────────────
_MODELS: dict[str, str] = {}


def model_ct(title: str) -> str:
    if not _MODELS:
        for name in sorted(os.listdir(DMLIB)):
            m = re.match(r"dm-([a-z0-9]{24})\.xsd$", name)
            if m:
                s = Schema.for_dm(m.group(1))
                _MODELS[s.label.get(s.dm, "")] = m.group(1)
    hits = [ct for t, ct in _MODELS.items() if t == title]
    assert len(hits) == 1, (title, hits)
    return hits[0]


def template(title: str) -> Template:
    return Template.for_dm(model_ct(title))


# ─── Governance ──────────────────────────────────────────────────────────────
_counter = 0


def record(title: str, values: dict, *, document_id: str, buyer: str, source: tuple[str, str, str], when: str,
           agent: tuple[str, str, str] = (GENERATOR_ID, GENERATOR, "Generated"), current_state: str | None = "OrderProcessing",
           instance_id: str | None = None, rng: random.Random | None = None) -> str:
    """One instance of the model titled ``title``.

    ``values`` maps label paths to values (a string, a Quantity, a bool, or None to leave the fact out).
    ``document_id`` is the business document's identifier (the record's subject); ``buyer`` the buyer's name (the
    provider party); ``source`` the document the activity used as (identifier, label, description): the file read,
    or the projection written; ``agent`` the (identifier, name, verb) of the software that produced the record.
    """
    global _counter
    _counter += 1
    t = template(title)
    vals = {k: v for k, v in values.items() if v is not None}
    src_id, src_label, src_desc = source
    agent_id, agent_name, verb = agent
    vals.update({
        "Order Governed Record/PROV Activity/Activity Identifier": f"urn:axius-sdc:business-documents:activity:{_counter:08d}",
        "Order Governed Record/PROV Activity/Activity Label": f"{verb} the {title} {document_id}",
        "Order Governed Record/PROV Activity/Activity Type": "RecordGeneration" if verb == "Generated" else "DocumentTranslation",
        "Order Governed Record/PROV Activity/Activity Description": f"{title} {document_id} {verb.lower()} as a governed record by the {agent_name} from {src_label}.",
        "Order Governed Record/PROV Activity/Activity Status": "ActivityCompleted",
        "Order Governed Record/PROV Activity/Started At": when,
        "Order Governed Record/PROV Activity/Ended At": when,
        "Order Governed Record/PROV Activity/Used Entity Reference": src_id,
        "Order Governed Record/PROV Activity/Was Associated With Reference": agent_id,
        "Order Governed Record/PROV Agent/Agent Identifier": agent_id,
        "Order Governed Record/PROV Agent/Agent Name": agent_name,
        "Order Governed Record/PROV Agent/PROV Agent Type": "SoftwareAgent",
        "Order Governed Record/PROV Agent/Software Name": agent_name,
        "Order Governed Record/PROV Agent/Software Version": LIBRARY_VERSION,
        "Order Governed Record/PROV Agent/Agent Organization Name": "Halvorsen Foods, Inc." if verb == "Read" else "Kestrel Mercantile, Inc.",
        "Order Governed Record/PROV Entity/Entity Identifier": src_id,
        "Order Governed Record/PROV Entity/Entity Label": src_label,
        "Order Governed Record/PROV Entity/Entity Description": src_desc,
        "Order Governed Record/PROV Entity/PROV Entity Type": "Entity",
        "Order Governed Record/Audit Event/Audit Event Identifier": f"urn:axius-sdc:business-documents:audit:{_counter:08d}",
        "Order Governed Record/Audit Event/Audit Event Action": "C",
        "Order Governed Record/Audit Event/Audit Event Outcome": "0",
        "Order Governed Record/Audit Event/Audit Recorded At": when,
        "Order Governed Record/Audit Event/Audit Agent Reference": agent_id,
        "Order Governed Record/Audit Event/Audit Entity Reference": src_id,
        "Order Governed Record/Audit Event/Data Subject Reference": f"urn:order:{document_id}",
        "Order Governed Record/Audit Event/Purpose of Use": "HOPERAT",
        "Order Governed Record/Audit Event/Confidentiality": "N",
        "Order Governed Record/Audit Event/Provenance Agent Type": "transformer" if verb != "Generated" else "author",
        "Order Governed Record/Audit Event/System Identifier": agent_id,
        "Order Governed Record/Audit Event/System Location Name": "Duluth, Minnesota" if verb == "Read" else "Chicago, Illinois",
    })
    return t.instance(vals, instance_id=instance_id or cuid_generator(rng), current_state=current_state, timestamp=when,
                      subject=("Order", document_id), provider=("Buyer", buyer),
                      audit={"system_id": agent_id, "user": agent_name, "timestamp": when,
                             "values": {"Business Document Audit/PROV Entity/Entity Identifier": src_id, "Business Document Audit/PROV Entity/Entity Label": src_label,
                                        "Business Document Audit/PROV Entity/Entity Description": src_desc}},
                      attestation={"reason": f"{verb} from {src_label} without alteration of the values", "committer": agent_name, "committed": when, "pending": False})


def write_record(directory: str, prefix: str, xml: str, name: str | None = None) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{prefix}-{name or cuid_generator()}.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml)
    return path
