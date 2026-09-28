# The saved questions

Two queries against the knowledge graph each stack projects, one named graph per record. Each anchors on a published component by its `ct_id`; the reifier is addressed by its label and its component is read from its IRI, so nothing in a triple term is left unbound (a triple term with the component unbound makes GraphDB scan every reifier).

| # | File | What it shows |
|---|------|---------------|
| 1 | `01_the_order_as_a_record.rq` | Every value one order carries, by component, in the stack you ask: the retailer's record, or the supplier's read from the document |
| 2 | `02_the_party_is_one_component.rq` | Every party the records name, grouped by the Default Organization Name component, with the orders each appears on |

The results are measured at release and recorded here.
