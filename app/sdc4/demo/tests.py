"""
The entity graph is derived, never invented: every node is a record the query returned, every edge
a value two of them share in an identifier component. These tests feed the builder canned
triple-store answers and check the shape it hands the page, and that the walk-through and the
query catalog agree.
"""
import json

from django.test import SimpleTestCase

from . import entity_graph as eg
from .narrative import BEATS, COMING
from .sparql_loader import QUERY_CATALOG, SPARQL_DIR

SDC4 = eg.SDC4


def _res(rows):
    return {'head': {'vars': list(rows[0]) if rows else []},
            'results': {'bindings': [{k: {'type': 'uri' if str(v).startswith('http') else 'literal', 'value': v}
                                      for k, v in r.items()} for r in rows]}}


class FakeClient:
    def __init__(self, nodes, titles, values, parties, fail=False):
        self.nodes, self.titles, self.values, self.parties, self.fail = nodes, titles, values, parties, fail
        self.queries = []

    def query_sparql(self, q):
        self.queries.append(q)
        if self.fail:
            raise RuntimeError('down')
        if 'sdc4:partyRef' in q:
            return _res(self.parties)
        if 'VALUES ?ra ' in q:
            return _res(self.values)
        if 'VALUES ?r ' in q:
            return _res(self.titles)
        return _res(self.nodes)


ORDER_1 = f'{SDC4}i-order0000000000000000001'
ORDER_2 = f'{SDC4}i-order0000000000000000002'
DM = f'{SDC4}dm-h8bttbt9afwzf9zs4jhae566'
ORDER_ID = f'{SDC4}mc-wtnd4hzyrntlwtp4z3l1gcpr'


class EntityGraphTests(SimpleTestCase):
    def test_two_records_of_the_same_order_join_on_the_order_id(self):
        client = FakeClient(
            nodes=[{'inst': ORDER_1, 'dm': DM, 'status': 'valid', 'title': 'Order'},
                   {'inst': ORDER_2, 'dm': DM, 'status': 'valid', 'title': 'Order'}],
            titles=[{'inst': ORDER_1, 'label': 'Order ID', 'v': 'KM-PO-2026-000001'},
                    {'inst': ORDER_2, 'label': 'Order ID', 'v': 'KM-PO-2026-000001'}],
            values=[{'a': ORDER_1, 'mc': ORDER_ID, 'v': 'KM-PO-2026-000001', 'la': 'Order ID'},
                    {'a': ORDER_2, 'mc': ORDER_ID, 'v': 'KM-PO-2026-000001', 'la': 'Order ID'}],
            parties=[])
        g = eg.build([ORDER_1, ORDER_2], client)
        # two record nodes and one node for the identifier they share: the join drawn as a thing on the screen
        self.assertEqual(len(g['nodes']), 3)
        self.assertEqual(sum(1 for n in g['nodes'] if 'i-order' in json.dumps(n)), 2)
        self.assertTrue(g['edges'], g)
        self.assertTrue(any('KM-PO-2026-000001' in json.dumps(e) or 'KM-PO-2026-000001' in json.dumps(n) for e in g['edges'] for n in g['nodes']), g)

    def test_a_store_that_is_down_leaves_the_graph_empty_with_a_reason(self):
        g = eg.build([ORDER_1], FakeClient([], [], [], [], fail=True))
        self.assertEqual(g['nodes'], [])
        self.assertTrue(g['reason'])

    def test_no_records_no_graph(self):
        g = eg.build([], FakeClient([], [], [], []))
        self.assertEqual(g['nodes'], [])


class WalkThroughTests(SimpleTestCase):
    def test_every_beat_has_a_saved_query_on_disk(self):
        for beat in BEATS:
            entry = QUERY_CATALOG[beat['query_number']]
            self.assertTrue((SPARQL_DIR / entry['file']).exists(), entry['file'])

    def test_the_beats_and_the_ones_to_come_make_seven(self):
        self.assertEqual(len(BEATS) + len(COMING), 7)   # the six of the plan, and the answer line by line the OrderResponse added
