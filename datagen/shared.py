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
#: The retailer's order system generates its orders and its translator reads the responses it receives;
#: the supplier's order system generates its responses, its warehouse system the dispatch advices, and its translator reads the orders it receives.
GENERATOR = "Kestrel Mercantile order system"
GENERATOR_ID = f"urn:kestrel:order-system:{LIBRARY_VERSION}"
TRANSLATOR = "Halvorsen Foods document translator"
TRANSLATOR_ID = f"urn:halvorsen:translator:{LIBRARY_VERSION}"
RETAILER_SYSTEM = (GENERATOR_ID, GENERATOR, "Generated")
SUPPLIER_TRANSLATOR = (TRANSLATOR_ID, TRANSLATOR, "Read")
SUPPLIER_SYSTEM = (f"urn:halvorsen:order-system:{LIBRARY_VERSION}", "Halvorsen Foods order system", "Generated")
RETAILER_TRANSLATOR = (f"urn:kestrel:translator:{LIBRARY_VERSION}", "Kestrel Mercantile document translator", "Read")
SUPPLIER_WAREHOUSE = (f"urn:halvorsen:warehouse-system:{LIBRARY_VERSION}", "Halvorsen Foods warehouse system", "Generated")
RETAILER_RECEIVING = (f"urn:kestrel:receiving-system:{LIBRARY_VERSION}", "Kestrel Mercantile receiving system", "Generated")
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
    G = f"{title} Governed Record/"   # every model's data cluster is "<title> Governed Record"
    vals.update({G + k: v for k, v in {
        "PROV Activity/Activity Identifier": f"urn:halvorsen-demo:activity:{_counter:08d}",
        "PROV Activity/Activity Label": f"{verb} the {title} {document_id}",
        "PROV Activity/Activity Type": "RecordGeneration" if verb == "Generated" else "DocumentTranslation",
        "PROV Activity/Activity Description": f"{title} {document_id} {verb.lower()} as a governed record by the {agent_name} from {src_label}.",
        "PROV Activity/Activity Status": "ActivityCompleted",
        "PROV Activity/Started At": when,
        "PROV Activity/Ended At": when,
        "PROV Activity/Used Entity Reference": src_id,
        "PROV Activity/Was Associated With Reference": agent_id,
        "PROV Agent/Agent Identifier": agent_id,
        "PROV Agent/Agent Name": agent_name,
        "PROV Agent/PROV Agent Type": "SoftwareAgent",
        "PROV Agent/Software Name": agent_name,
        "PROV Agent/Software Version": LIBRARY_VERSION,
        "PROV Agent/Agent Organization Name": "Halvorsen Foods, Inc." if verb == "Read" else "Kestrel Mercantile, Inc.",
        "PROV Entity/Entity Identifier": src_id,
        "PROV Entity/Entity Label": src_label,
        "PROV Entity/Entity Description": src_desc,
        "PROV Entity/PROV Entity Type": "Entity",
        "Audit Event/Audit Event Identifier": f"urn:halvorsen-demo:audit:{_counter:08d}",
        "Audit Event/Audit Event Action": "C",
        "Audit Event/Audit Event Outcome": "0",
        "Audit Event/Audit Recorded At": when,
        "Audit Event/Audit Agent Reference": agent_id,
        "Audit Event/Audit Entity Reference": src_id,
        "Audit Event/Data Subject Reference": f"urn:order:{document_id}",
        "Audit Event/Purpose of Use": "HOPERAT",
        "Audit Event/Confidentiality": "N",
        "Audit Event/Provenance Agent Type": "transformer" if verb != "Generated" else "author",
        "Audit Event/System Identifier": agent_id,
        "Audit Event/System Location Name": "Duluth, Minnesota" if verb == "Read" else "Chicago, Illinois",
    }.items()})
    return t.instance(vals, instance_id=instance_id or cuid_generator(rng), current_state=current_state, timestamp=when,
                      subject=(title, document_id), provider=("Buyer" if title in ("Order", "Receipt Advice") else "Seller", buyer),
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
