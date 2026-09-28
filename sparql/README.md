# The saved questions

Two queries against the knowledge graph each stack projects, one named graph per record. Each anchors on a published component by its `ct_id`; the reifier is addressed by its label and its component is read from its IRI, so nothing in a triple term is left unbound (a triple term with the component unbound makes GraphDB scan every reifier).

| # | File | What it shows |
|---|------|---------------|
| 1 | `01_the_order_as_a_record.rq` | Every value one order carries, by component, in the stack you ask: the retailer's record, or the supplier's read from the document |
| 2 | `02_the_party_is_one_component.rq` | Every party the records name, grouped by the Default Organization Name component, with the orders each appears on |

## What each returned (release 4.1.1, 52 orders and 52 responses, GraphDB idle)

| # | Rows | Time | Retailer | Supplier |
|---|---|---|---|---|
| 1 | 187 | 0.6 s | every value of order KM-PO-2026-000001, the activity reading "Generated the Order" | the same values, the activity reading "Read the Order", the entity the document `KM-PO-2026-000001.xml` |
| 2 | 2 | 0.02 s | Halvorsen Foods, Inc. on 104 documents; Kestrel Mercantile, Inc. on 104 | the same two rows: the party is the same component in both models and on both sides |
| 3 | 52 | 0.03 s | every response joined to its order; the response type and the line answers | the same 52 rows, the responses generated here and the orders read |

Both stacks answer the same questions; what differs is the provenance each record carries.

| 3 | `03_the_answer_line_by_line.rq` | Each response joined to the order it answers on the Order ID, the answer to the order as a whole, and the answers its lines carry (release 4.1.1) |

A reifier is keyed by component and record, so a component the model composes ten times (the lines) shares its reifier across the lines of one record in the graph. Which answers a response holds is the graph's question; which line carries which answer is the record's, on its Table pane.
