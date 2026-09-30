"""
Load SPARQL .rq files from the /sparql/ directory.
"""
from pathlib import Path
from django.conf import settings

# Docker mount at /sparql (see docker-compose.yml), fallback to host path
_docker_path = Path('/sparql')
_host_path = settings.BASE_DIR.parent.parent / 'sparql'
SPARQL_DIR = _docker_path if _docker_path.exists() else _host_path

QUERY_CATALOG = {
    1: {
        'file': '01_the_order_as_a_record.rq',
        'title': 'The order as a record',
        'description': 'Every value one order carries in this stack, by component: the record the document was written from, or read into.',
        'domains': ['Order'],
    },
    2: {
        'file': '02_the_party_is_one_component.rq',
        'title': 'The party is one component',
        'description': 'Every party the records name, grouped by the Default Organization Name component, with the orders each appears on.',
        'domains': ['Order'],
    },
    3: {
        'file': '03_the_answer_line_by_line.rq',
        'title': 'The answer, line by line',
        'description': 'Each response joined to the order it answers on the Order ID, with the answer to every line.',
        'domains': ['Order', 'Order Response'],
    },
    4: {
        'file': '04_the_rule_that_changed.rq',
        'title': 'The rule that changed',
        'description': 'Each despatch advice joined to its order, with the pack specification version its pallets were packed to and the day it was sent; the version in force changed on 1 July.',
        'domains': ['Order', 'Despatch Advice'],
    },
    5: {
        'file': '05_the_identifier_that_expired.rq',
        'title': 'The identifier that expired',
        'description': 'Each despatch advice with its pallet identifiers, the earliest day one of them stops being valid, and the day the advice was sent.',
        'domains': ['Despatch Advice'],
    },
    6: {
        'file': '06_the_verdict_in_the_record.rq',
        'title': 'The verdict, in the record',
        'description': 'Each receipt advice with the dispatch it answers, the day received, the two answers its pallets carry (the identifier within its period, the pack specification in force), the decision, and the exception.',
        'domains': ['Despatch Advice', 'Receipt Advice'],
    },
    7: {
        'file': '07_the_bill_for_what_arrived.rq',
        'title': 'The bill, for what arrived',
        'description': 'Each invoice joined to the receipt it settles, the dispatch and the order, with the amount due, the deposit deducted, and the receiver\'s conditions on the pallets.',
        'domains': ['Receipt Advice', 'Invoice'],
    },
    8: {
        'file': '08_the_verdict_settled.rq',
        'title': 'The verdict, settled',
        'description': 'Each settled receipt advice paired with its original: the Settlement Receipt its provenance names, the state reached, and the conditions the original carried.',
        'domains': ['Receipt Advice'],
    },
    9: {
        'file': '09_two_profiles.rq',
        'title': 'Two profiles',
        'description': 'Every order in this stack by the model that governs it: Kestrel\'s under the Order model with its delivery terms, Torvale\'s under the Torvale Order model with its terms, pack specification version and delivery window.',
        'domains': ['Order', 'Torvale Order'],
    },
}


def load_query(num):
    """Read a single .rq file and return its text."""
    entry = QUERY_CATALOG.get(num)
    if not entry:
        return None
    path = SPARQL_DIR / entry['file']
    if not path.exists():
        return None
    return path.read_text()


def load_all_queries():
    """Return all queries with metadata and SPARQL text."""
    result = {}
    for num, meta in QUERY_CATALOG.items():
        sparql = load_query(num)
        result[num] = {**meta, 'sparql': sparql or ''}
    return result
