# The saved questions

Five queries against the knowledge graph each stack projects, one named graph per record. Each anchors on a published component by its `ct_id`; the reifier is addressed by its label and its component is read from its IRI, so nothing in a triple term is left unbound (a triple term with the component unbound makes GraphDB scan every reifier).

| # | File | What it shows |
|---|------|---------------|
| 1 | `01_the_order_as_a_record.rq` | Every value one order carries, by component, in the stack you ask: the retailer's record, or the supplier's read from the document |
| 2 | `02_the_party_is_one_component.rq` | Every party the records name, grouped by the Default Organization Name component, with the orders each appears on |
| 3 | `03_the_answer_line_by_line.rq` | Each response joined to the order it answers on the Order ID, the answer to the order as a whole, and the answers its lines carry |
| 4 | `04_the_rule_that_changed.rq` | Each despatch advice joined to its order on the Order ID, the pack specification version its pallets were packed to, the pallet count, and the day it was sent |
| 5 | `05_the_identifier_that_expired.rq` | Each despatch advice with its pallet identifiers, the earliest day one of them stops being valid, the day the advice was sent, and the verdict the two dates give |

## What each returned (release 4.1.2, 52 orders, 52 responses and 52 despatch advices, GraphDB cold)

| # | Rows | Time | Retailer | Supplier |
|---|---|---|---|---|
| 1 | 187 | 1.7 s | every value of order KM-PO-2026-000001, the activity reading "Generated the Order" | the same values, the activity reading "Read the Order", the entity the document `KM-PO-2026-000001.xml` |
| 2 | 3 | 0.01 s | Halvorsen Foods, Inc. and Kestrel Mercantile, Inc. on every document; Northline Freight, LLC, the carrier, on the 52 despatches | the same three rows: the party is the same component in the three models and on both sides |
| 3 | 52 | 0.08 s | every response joined to its order; the response type and the line answers | the same 52 rows, the responses generated here and the orders read |
| 4 | 52 | 0.03 s | every despatch joined to its order with its pack specification version and pallet count; two after 1 July name `KM-PACK-2026-01` | the same 52 rows, the despatches generated here and the orders read |
| 5 | 52 | 0.03 s | every despatch with its pallet identifiers and the earliest validity end; four read `lapses on despatch` | the same 52 rows |

Both stacks answer the same questions; what differs is the provenance each record carries.

A reifier is keyed by component and record, so a component the model composes ten times (the lines) or six times (the pallets) shares its reifier across the lines or pallets of one record in the graph, and a Default component used twice in one record (the date range of a pallet's validity and of the delivery window; the issue date of the advice and of the order it references) shares it too. Which answers a response holds, or the earliest day a despatch's identifiers stop being valid, is the graph's question; which line or which pallet is the record's, on its Table pane. Queries 4 and 5 say so in their comments and take the later issue date and the earliest end.
