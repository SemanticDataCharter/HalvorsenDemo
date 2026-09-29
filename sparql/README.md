# The saved questions

Seven queries against the knowledge graph each stack projects, one named graph per record. Each anchors on a published component by its `ct_id`; the reifier is addressed by its label and its component is read from its IRI, so nothing in a triple term is left unbound (a triple term with the component unbound makes GraphDB scan every reifier).

| # | File | What it shows |
|---|------|---------------|
| 1 | `01_the_order_as_a_record.rq` | Every value one order carries, by component, in the stack you ask: the retailer's record, or the supplier's read from the document |
| 2 | `02_the_party_is_one_component.rq` | Every party the records name, grouped by the Default Organization Name component, with the orders each appears on |
| 3 | `03_the_answer_line_by_line.rq` | Each response joined to the order it answers on the Order ID, the answer to the order as a whole, and the answers its lines carry |
| 4 | `04_the_rule_that_changed.rq` | Each dispatch advice joined to its order on the Order ID, the pack specification version its pallets were packed to, the pallet count, and the day it was sent |
| 5 | `05_the_identifier_that_expired.rq` | Each dispatch advice with its pallet identifiers, the earliest day one of them stops being valid, the day the advice was sent, and the verdict the two dates give |
| 6 | `06_the_verdict_in_the_record.rq` | Each receipt advice joined to the dispatch it answers, the day received, the receiver's decision on its pallets, and the exception where there is one |
| 7 | `07_the_bill_for_what_arrived.rq` | Each invoice joined to the receipt it settles, the dispatch and the order, with the amount due, the deposit deducted, and the receiver's conditions on the pallets |

## What each returned (release 4.1.5, 52 of each of the five documents, GraphDB cold)

| # | Rows | Time | Retailer | Supplier |
|---|---|---|---|---|
| 1 | 190 | 4.6 s | every value of order KM-PO-2026-000001 (190 since 4.1.4: the three booleans now reach the graph), the activity reading "Generated the Order" | the same values, the activity reading "Read the Order", the entity the document `KM-PO-2026-000001.xml` |
| 2 | 3 | 0.19 s | Halvorsen Foods, Inc. and Kestrel Mercantile, Inc. on all 260 documents; Northline Freight, LLC, the carrier, on the 104 dispatches and receipts | the same three rows: the party is the same component in the five models and on both sides |
| 3 | 52 | 0.16 s | every response joined to its order; the response type and the line answers | the same 52 rows, the responses generated here and the orders read |
| 4 | 52 | 0.68 s | every dispatch joined to its order with its pack specification version and pallet count; two after 1 July name `KM-PACK-2026-01` | the same 52 rows, the dispatches generated here and the orders read |
| 5 | 52 | 0.16 s | every dispatch with its pallet identifiers and the earliest validity end; four read `lapses on dispatch` | the same 52 rows |
| 6 | 52 | 0.62 s | every receipt joined to its dispatch with the day received, its pallets' two answers, its conditions and its exceptions; eight read `Accepted with exception` with a `false` beside it, two of them shipments that crossed 1 July in transit | the same 52 rows, the receipts read here and the dispatches generated |
| 7 | 52 | 0.04 s | every invoice joined to its receipt, its dispatch and its order, with the day due, the amount payable, the deposit where one was paid (five) and the receiver's conditions; eight bills stand beside an exception | the same 52 rows, the invoices generated here and the receipts read |

Both stacks answer the same questions; what differs is the provenance each record carries.

A reifier is keyed by component and record, so a component the model composes ten times (the lines) or six times (the pallets) shares its reifier across the lines or pallets of one record in the graph, and a Default component used twice in one record (the date range of a pallet's validity and of the delivery window; the issue date of the advice and of the order it references) shares it too. Which answers a response holds, or the earliest day a dispatch's identifiers stop being valid, is the graph's question; which line or which pallet is the record's, on its Table pane. Queries 4 and 5 say so in their comments and take the later issue date and the earliest end. Query 6 binds the two boolean answers beside the receiving condition and the exception; on the first run of 4.1.3 the answers were absent from the graph, the generated application naming a boolean's value by an element the reference model does not have (SDCStudio #714, fixed the same day, the applications regenerated for 4.1.4).
