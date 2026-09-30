"""
The settlements page: every Settlement Receipt held in settlement/, verified here with nothing from the issuer.

A Receipt names the record it settled by the hash of its bytes and the schema by the hash of its bytes. This
module finds the record in this stack's store by hashing every receipt advice's XML, hashes the schema in the
model library, and runs sdcreceipt's verifier over the Receipt with the issuer's published key document and
the parties' key documents as saved beside it. The page shows what verified and what did not, and links the
Receipt to the record it names and to the settled record whose provenance names the Receipt.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings

from sdc4_shared.utils.dm_registry import get_dm_registry

_docker_path = Path('/settlement')
_host_path = settings.BASE_DIR.parent.parent / 'settlement'
SETTLEMENT_DIR = _docker_path if _docker_path.exists() else _host_path
RECEIPT_ADVICE_CT = 'tog0v0p1zit1xwpxysxwpf3d'


def _load(name: str):
    p = SETTLEMENT_DIR / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def key_documents():
    issuer = _load('issuer-keys.json')
    docs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((SETTLEMENT_DIR / 'keys').glob('*-key.json'))]
    if not docs:
        return issuer, None
    if all('keys' in d for d in docs):
        return issuer, {'keys': [k for d in docs for k in d['keys']]}
    merged: Dict[str, Any] = {}
    for d in docs:
        merged.update(d)
    return issuer, merged


def records_by_hash() -> Dict[str, Dict[str, str]]:
    """Every receipt advice in the store, by the sha256 of its XML, with the settled one that names a Receipt."""
    model = get_dm_registry().get(RECEIPT_ADVICE_CT)
    out: Dict[str, Dict[str, str]] = {}
    if model is None:
        return out
    for instance_id, xml in model.objects.values_list('instance_id', 'xml_content'):
        if xml:
            out[hashlib.sha256(xml.encode('utf-8')).hexdigest()] = {'instance_id': instance_id, 'xml': xml}
    return out


def settlements() -> Dict[str, Any]:
    index = _load('index.json') or []
    if not index:
        return {'rows': [], 'issued': False}
    issuer, parties = key_documents()
    by_hash = records_by_hash()
    settled_by_receipt: Dict[str, str] = {}
    for entry in by_hash.values():
        if 'urn:vsl:receipt:' in entry['xml']:
            for line in entry['xml'].split('urn:vsl:receipt:')[1:]:
                settled_by_receipt[line.split('<', 1)[0].strip()] = entry['instance_id']
    dmlib = Path(settings.BASE_DIR) / 'mediafiles' / 'dmlib'
    rows: List[Dict[str, Any]] = []
    for entry in index:
        receipt = _load(f"receipts/{entry['receipt_id']}.json") or {}
        condition = _load(entry['condition_file']) or {}
        record = by_hash.get(receipt.get('payload_hash', ''))
        schema_path = dmlib / f"dm-{receipt.get('schema_ct_id', '')}.xsd"
        schema_ok = schema_path.exists() and hashlib.sha256(schema_path.read_bytes()).hexdigest() == receipt.get('schema_hash')
        verified, failures = False, ['sdcreceipt is not installed'] if issuer is None else []
        if issuer is not None and receipt:
            try:
                from sdcreceipt import verify
                result = verify(receipt, issuer_keys=issuer, party_keys=parties if entry['decision'] == 'PERMIT' else None,
                                payload=record['xml'].encode('utf-8') if record else None)
                verified, failures = bool(result.ok), list(result.failures)
            except Exception as exc:   # a missing library or a malformed file: say so on the page rather than fail it
                verified, failures = False, [str(exc)]
        rows.append({
            'receipt_advice_id': entry['receipt_advice_id'], 'order_id': entry['order_id'], 'invoice_id': entry.get('invoice_id'),
            'kind': entry['kind'], 'target_state': entry['target_state'], 'decision': entry['decision'], 'settleable': entry['settleable'],
            'receipt_id': entry['receipt_id'], 'timestamp': receipt.get('timestamp', ''), 'triggers': len(receipt.get('settlement', {}).get('triggers', [])),
            'parties': receipt.get('settlement', {}).get('parties', []), 'verified': verified, 'failures': failures,
            'record_found': record is not None, 'record_instance': record['instance_id'] if record else None,
            'settled_instance': settled_by_receipt.get(entry['receipt_id']), 'schema_ok': schema_ok,
            'payload_hash': receipt.get('payload_hash', ''), 'schema_hash': receipt.get('schema_hash', ''), 'condition_hash': receipt.get('settlement', {}).get('condition_hash', ''),
            'deduction': condition.get('deduction_amount'), 'pallets': condition.get('pallets', []), 'condition_json': json.dumps(condition, indent=2), 'receipt_json': json.dumps(receipt, indent=2),
        })
    return {'rows': rows, 'issued': True, 'issuer_key_ids': [k.get('key_id') or k.get('kid') for k in (issuer or {}).get('keys', [])] if isinstance(issuer, dict) else [],
            'verified': sum(r['verified'] for r in rows), 'permits': sum(r['decision'] == 'PERMIT' for r in rows), 'denies': sum(r['decision'] == 'DENY' for r in rows),
            'ct_id': RECEIPT_ADVICE_CT}
