# The saved questions

Two queries against the knowledge graph each stack projects, one named graph per record. Each anchors on a published component by its `ct_id`; the reifier is addressed by its label and its component is read from its IRI, so nothing in a triple term is left unbound (a triple term with the component unbound makes GraphDB scan every reifier).

| # | File | What it shows |
|---|------|---------------|
| 1 | `01_the_order_as_a_record.rq` | Every value one order carries, by component, in the stack you ask: the retailer's record, or the supplier's read from the document |
| 2 | `02_the_party_is_one_component.rq` | Every party the records name, grouped by the Default Organization Name component, with the orders each appears on |

## What each returned (release 4.1.0, 52 orders, GraphDB idle)

| # | Rows | Time | Retailer | Supplier |
|---|---|---|---|---|
| 1 | 187 | 0.5 s | every value of order KM-PO-2026-000001, the activity reading "Generated the Order" | the same values, the activity reading "Read the Order", the entity the document `KM-PO-2026-000001.xml` |
| 2 | 2 | 0.02 s | Halvorsen Foods, Inc. on 52 orders; Kestrel Mercantile, Inc. on 52 | the same two rows: the party is the same component on both sides |

Both stacks answer the same questions; what differs is the provenance each record carries.
