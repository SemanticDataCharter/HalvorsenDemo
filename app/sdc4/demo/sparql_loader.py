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
