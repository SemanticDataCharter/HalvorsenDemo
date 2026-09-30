"""
The settlements page: every Settlement Receipt held in settlement/, verified here with nothing from the issuer.

A Receipt names the record it settled by the hash of its bytes and the schema by the hash of its bytes. This
module finds the record in this stack's store by its document identifier, checks the record's bytes as read in, hashes the schema in the
model library, and runs sdcreceipt's verifier over the Receipt with the issuer's published key document and
the parties' key documents as saved beside it. The page shows what verified and what did not, and links the
Receipt to the record it names and to the settled record whose provenance names the Receipt.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

from sdc4_shared.utils.dm_registry import get_dm_registry

_docker_path = Path('/settlement')
_host_path = settings.BASE_DIR.parent.parent / 'settlement'
SETTLEMENT_DIR = _docker_path if _docker_path.exists() else _host_path
if str(SETTLEMENT_DIR) not in sys.path:
    sys.path.insert(0, str(SETTLEMENT_DIR))
from entries import RECEIPT_ADVICE_CT, norm  # noqa: E402


def _load(name: str):
    p = SETTLEMENT_DIR / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def key_documents():
    """Every key document held: the issuer's as saved, and each party's, merged into one key set."""
    from sdcreceipt.party import KeySet, load_key_set_file
    keyset = KeySet()
    for path in [SETTLEMENT_DIR / 'issuer-keys.json'] + sorted((SETTLEMENT_DIR / 'keys').glob('*-key.json')):
        if path.exists():
            keyset.merge(load_key_set_file(path))
    return keyset


def split_keys(receipt, keyset):
    """The Receipt says which key ids signed it; the verifier wants the issuer's keys and the parties' apart."""
    from sdcreceipt.party import KeySet
    issuer_ids = {sig.get('key_id') for sig in receipt.get('signatures', []) if isinstance(sig, dict)}
    issuer, parties = KeySet(), KeySet()
    for key_id, key in keyset.items():
        target = issuer if key_id in issuer_ids else parties
        target[key_id] = key
        if key_id in keyset.status:
            target.status[key_id] = keyset.status[key_id]
    return issuer, (parties or None)


#: Where this stack's own records were read from: the Receipt names the record by the bytes on the wire, and the
#: loader re-serializes what it stores, so the bytes come from the import directory, not from the store. In the
#: container the stack's own import directory is mounted at /app/import_data; on the host every stack's is under
#: import_data/<stack>/, and the entry says which.
_import_docker = Path('/app/import_data')
_import_host = settings.BASE_DIR / 'import_data'


def records_of(ct_id: str) -> List[Dict[str, str]]:
    """Every record of a model in the store: its instance id and XML."""
    model = get_dm_registry().get(ct_id)
    if model is None:
        return []
    return [{'instance_id': i, 'xml': x or ''} for i, x in model.objects.values_list('instance_id', 'xml_content')]


def record_bytes(record_dir: str, record_file: str):
    """The record as it was read in, when this stack read it; None on the other stack."""
    path = _import_docker / record_dir.rsplit('/', 1)[-1] / record_file if _import_docker.exists() else _import_host.joinpath(*record_dir.split('/')) / record_file
    return path.read_bytes() if path.exists() else None


def by_identifier(ct_id: str, id_label: str):
    """The original records of a model by their document identifier, and the settled ones by the Receipt their provenance names."""
    settled_by_receipt: Dict[str, str] = {}
    original_by_id: Dict[str, str] = {}
    for a in records_of(ct_id):
        if 'urn:vsl:receipt:' in a['xml']:
            for piece in a['xml'].split('urn:vsl:receipt:')[1:]:
                settled_by_receipt[piece.split('<', 1)[0].strip()] = a['instance_id']
        else:
            for piece in a['xml'].split(f'<label>{id_label}</label>')[1:2]:
                value = piece.split('<xdstring-value>', 1)[1].split('<', 1)[0] if '<xdstring-value>' in piece else ''
                if value:
                    original_by_id[value] = a['instance_id']
    return original_by_id, settled_by_receipt


def settlements() -> Dict[str, Any]:
    index = _load('index.json') or []
    if not index:
        return {'rows': [], 'issued': False}
    try:
        keyset = key_documents()
    except Exception as exc:   # sdcreceipt missing or a malformed document: the page says so on every row
        keyset, key_error = None, str(exc)
    else:
        key_error = None
    entries = [norm(e) for e in index]
    lookups = {(e['model_ct'], e['id_label']): by_identifier(e['model_ct'], e['id_label']) for e in entries}
    dmlib = Path(settings.BASE_DIR) / 'mediafiles' / 'dmlib'
    rows: List[Dict[str, Any]] = []
    for entry in entries:
        original_by_id, settled_by_receipt = lookups[(entry['model_ct'], entry['id_label'])]
        receipt = _load(f"receipts/{entry['receipt_id']}.json") or {}
        condition = _load(entry['condition_file']) or {}
        payload = record_bytes(entry['record_dir'], entry['record_file'])
        payload_matches = payload is not None and hashlib.sha256(payload).hexdigest() == receipt.get('payload_hash')
        record = {'instance_id': original_by_id[entry['document_id']]} if entry['document_id'] in original_by_id else None
        schema_path = dmlib / f"dm-{receipt.get('schema_ct_id', '')}.xsd"
        schema_ok = schema_path.exists() and hashlib.sha256(schema_path.read_bytes()).hexdigest() == receipt.get('schema_hash')
        verified, failures = False, [key_error] if key_error else []
        if keyset is not None and receipt:
            try:
                from sdcreceipt import verify
                issuer, parties = split_keys(receipt, keyset)
                result = verify(receipt, issuer_keys=issuer, party_keys=parties if entry['decision'] == 'PERMIT' else None,
                                payload=payload if payload_matches else None)   # a copy that is not the bytes named (the supplier's, read from the document) is not the payload
                # a DENY attests a refusal and accepts no triggers: its settlement is never complete, and that is not a failure
                deny = entry['decision'] == 'DENY'
                failures = [str(f) for f in result.failures if not (deny and getattr(f, 'name', '') == 'settlement.complete')]
                verified = not failures
            except Exception as exc:   # a missing library or a malformed file: say so on the page rather than fail it
                verified, failures = False, [str(exc)]
        rows.append({
            'document_id': entry['document_id'], 'model': entry['model'], 'ct_id': entry['model_ct'], 'order_id': entry['order_id'], 'invoice_id': entry.get('invoice_id'),
            'kind': entry['kind'], 'from_state': entry['from_state'], 'target_state': entry['target_state'], 'decision': entry['decision'], 'settleable': entry['settleable'],
            'receipt_id': entry['receipt_id'], 'timestamp': receipt.get('timestamp', ''), 'triggers': len(receipt.get('settlement', {}).get('triggers', [])),
            'parties': receipt.get('settlement', {}).get('parties', []), 'verified': verified, 'failures': failures,
            'record_found': record is not None, 'record_instance': record['instance_id'] if record else None, 'payload_here': payload is not None, 'payload_matches': payload_matches,
            'settled_instance': settled_by_receipt.get(entry['receipt_id']), 'schema_ok': schema_ok,
            'payload_hash': receipt.get('payload_hash', ''), 'schema_hash': receipt.get('schema_hash', ''), 'condition_hash': receipt.get('settlement', {}).get('condition_hash', ''),
            'deduction': condition.get('deduction_amount'), 'pallets': condition.get('pallets', []), 'profile': condition.get('profile'), 'condition_json': json.dumps(condition, indent=2), 'receipt_json': json.dumps(receipt, indent=2),
        })
    return {'rows': rows, 'issued': True,
            'verified': sum(r['verified'] for r in rows), 'permits': sum(r['decision'] == 'PERMIT' for r in rows), 'denies': sum(r['decision'] == 'DENY' for r in rows),
            'models': sorted({r['model'] for r in rows}), 'ct_id': RECEIPT_ADVICE_CT}
