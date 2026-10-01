# HalvorsenDemo

Halvorsen Foods is a fictitious food manufacturer. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This is the demonstration in which the verdict survives a question. Two stacks on one machine, the supplier and the retailer, exchange business documents as governed records composed from the published component libraries and the business documents library built from the OASIS Universal Business Language and GS1 identifiers, with the document written on the way out of one stack and read on the way in to the other. Every record carries its provenance and the model that governs it. The document is a projection of the record.

**Scheduled for the first quarter of 2027. Private until it ships.** This is release 4.1.8: the five documents, the exchange in both directions, the deductions settled with Settlement Receipts that verify offline, a second retailer's order profile as a model on the same components, and all nine beats. Built on the CordovaOS 4.4.2 skeleton, the way the FAIR Data Demo was.

## Two guides, depending on why you are here

- [For the people who sign](app/sdc4/docs/FOR-DECISION-MAKERS.md): what the two stacks show, in plain terms.
- [For the people who run it](app/sdc4/docs/FOR-IT-STAFF.md): the stacks, the exchange, the loader, the queries.

## Run it locally

```bash
git clone https://github.com/SemanticDataCharter/HalvorsenDemo.git
cd HalvorsenDemo
make demo
```

`make demo` starts both stacks, generates a year of purchase orders, responses, dispatch advices, receipt advices and invoices on the host (about thirty seconds), with the second retailer's twelve monthly orders, and loads each side. Then open:

- http://localhost:18300/console/ the retailer, Kestrel Mercantile: 52 orders its order system generated, 52 responses, 52 dispatch advices and 52 invoices read from the UBL 2.3 documents the supplier sent, and 52 receipt advices its receiving system generated on the day each shipment arrived, every pallet checked that day.
- http://localhost:18200/console/ the supplier, Halvorsen Foods: the same 52 orders and 52 receipt advices, each read from the UBL 2.3 document the retailer sent, 52 responses its order system generated within a day of each order, 52 dispatch advices its warehouse system generated the day before each delivery window, 52 invoices its billing system generated for what each receipt says arrived, and 12 orders from a second retailer, Torvale Markets, each read from its UBL 2.3 Order into Torvale's own profile model.

Measured on the first run of 4.1.8: 268 records and 268 named graphs on the retailer (52 of each of the five documents and the eight settled receipt advices) and 273 on the supplier (the same 52 of each, the 12 Torvale orders under the Torvale Order model, and the one of them settled to transit), none invalid, the loader's per-model times summing to 25 seconds a side; the nine saved queries answer in 9.5, 0.04, 0.04, 0.12, 0.07, 0.03, 0.04, 0.04 and 4.3 seconds on a cold store, the ninth 0.04 warm (`sparql/README.md`); query 9 lists 64 orders on the supplier by the model that governs each, 52 on the retailer. Ten Settlement Receipts are held and verify on both stacks: nine PERMIT with both parties' triggers, one DENY; the tenth names the Torvale Order model by its schema bytes and the supplier's record of Torvale's first order by its bytes, released to transit between Torvale and Halvorsen. The Settlements page on each stack finds every record the Receipts name that the stack holds, byte for byte, as it was read in: the eight receipt advices on the retailer, the Torvale order on the supplier. The Profiles page on either stack shows the first order of each retailer under both models: each accepted under its own, each refused under the other's, the refusals named. Of the 52 receipts, eight are in the OrderProblem state: four for a pallet identifier that lapsed the day after dispatch, two for a unit packed to the pack specification the retailer replaced in July, and two for shipments that left on 30 June packed to the version in force that day and arrived on 1 July, when it no longer was. The last two are the story's notice exactly, and nobody generated them on purpose.

`make down` stops both. Two stacks need about 14 GB of RAM; `HALVORSEN_ORDERS=260 make demo` generates five years.

## What runs in this release

| Beat | What it shows | Where |
|---|---|---|
| 1. The order as a record | One order as table, document and graph; beside it the UBL Order it was written to, byte for byte the same when read back | the console, either stack; saved query 1 |
| 2. The party is one component | Buyer, seller and delivery party on the same Default `organization-name` and address components a NIEM person and a FHIR organization compose | saved query 2, the entity graph |
| 3. The answer, line by line | Each response joined to its order on the Order ID, the same component in both models; accepted, cut, rejected or substituted, line by line on the record's table pane | saved query 3, the console |
| 4. The rule that changed | Each dispatch joined to its order, the pack specification version its pallets were packed to beside the day it was sent; the retailer's version changed on 1 July, and a later dispatch packed to the January version is the notice of the story | saved query 4 |
| 5. The identifier that expired | Each dispatch with its pallet identifiers and the earliest day one stops being valid; where that is the day the advice was sent, the notice went out inside the period and the goods arrive outside it | saved query 5, the record's table pane |
| 6. The verdict, in the record | Each receipt joined to its dispatch, the day received, the two answers every pallet carries (the identifier within its period, the version in force), the receiver's decision and the exception where there is one; a failing pallet puts the record in OrderProblem | saved query 6, the record's table pane |
| 7. The bill, for what arrived | Each invoice joined to the receipt it settles, the dispatch and the order; the amount due and the deposit deducted beside the receiver's conditions on the pallets: the bill and the exception it will be argued over, in one row | saved query 7 |
| 8. The verdict, settled | Each deduction settled once, live, as the receipt advice's transition from OrderProblem to OrderProcessing: the deduction notice as the condition, the issuer's signed Settlement Receipt, both parties' triggers, one refusal kept beside them; verified here with nothing from the issuer, the settled record's provenance naming the Receipt | the Settlements page, saved query 8 |
| 9. Two profiles | A second retailer publishes its order profile as a model on the same components: the one delivery rule it accepts, the pack specification version and the delivery window it requires, as assertions in the model's schema. Its orders are read into that model beside the first retailer's; one order of each, under both models, shows what each refuses; one Receipt names the Torvale model, so the verdict says which profile governed | saved query 9, the Profiles page, the Settlements page |

The console's question, on either stack: where did every record come from, and what does it hold? The retailer's records name its order system as the PROV agent; the supplier's name the document each was read from and the translator that read it. The store answers from the bound components.

## How it was built

1. The Order, Order Response, Despatch Advice, Receipt Advice and Invoice models, and the Torvale Order profile: 345 components authored from the UBL 2.3 common library and GS1's identifiers on the Default and ProvGov libraries by identifier slot, published in the SDCStudio project Business Documents, the ProvGov `order` workflow bound. The Torvale Order model composes the same components with three of its own (a terms token narrowed to DDP, a pack specification version, a delivery window) and requires the last two by assertions in its schema, which SDCStudio's generator emits (#719). The applications SDCStudio generated for them are in `app/sdc4/order/`, `app/sdc4/order_response/`, `app/sdc4/despatch_advice/`, `app/sdc4/receipt_advice/`, `app/sdc4/invoice/` and `app/sdc4/torvale_order/`, verbatim; the packages and the app zips as downloaded are in `sdcstudio_downloads/`.
2. The exchange: `ubl/order.py`, `ubl/order_response.py`, `ubl/dispatch_advice.py`, `ubl/receipt_advice.py` and `ubl/invoice.py` write a conformant UBL 2.3 document from a record and read one into a record; `datagen/` generates the retailer's orders and receipts and the supplier's responses, dispatch advices and invoices on the template engine, writes each as a document, validates it against the OASIS schema of its type, and reads it back on the other side. `ubl/order.py` takes a profile: the same writer and reader serve Kestrel's Order and Torvale's, the requirements in UBL's own places (the pack specification version as an additional document reference, the window as the requested delivery period's duration); `ubl/profiles.py` reads what a model requires from its schema's assertions and names what it refuses. `datagen/torvale.py` generates Torvale's monthly orders. `datagen/tests/` holds the six round trips and the two-models exhibit. Where UBL has no element for what a record names, the module says where it went: the pallet as transport equipment with its identifier's validity period as the equipment's document reference, the pack specification version as the unit's document reference, the receiver's checks on the receipt date as the unit's statuses.
3. The settlement: `make settle`, with an issuer token, settles every receipt advice in OrderProblem against SDCStudio's Verifiable Settlement Layer, one credit a Receipt, and one Torvale order's release to transit under its profile, so a Receipt names the Torvale model by its schema bytes (issued in 4.1.8): the deduction notice is the condition, the fictitious parties sign with keys generated on the spot (their key documents are committed, the private keys are not), and everything the issuer returns lands under `settlement/`. `make generate` then writes the settled records where the Receipt's bytes still match, and `make verify-settlements` and the Settlements page verify every Receipt with `sdcreceipt` against the issuer's published key document as saved, the parties' key documents, the record's bytes and the schema's bytes. Nothing at `make demo` reaches the issuer. The generated data carries a pinned data version (`LIBRARY_VERSION` in `datagen/shared.py`), not the release number, so a release that changes nothing in the data leaves the bytes the Receipts name unchanged.
4. The stack: the CordovaOS 4.4.2 skeleton (settings, compose, batch loader, console, demo pages, entity graph) run twice from one compose file, `env/halvorsen.env` and `env/retailer.env` giving each its project name, ports and data directory.

## Repository structure

- `app/sdc4/`: the Django project; `order/`, `order_response/`, `despatch_advice/`, `receipt_advice/`, `invoice/` and `torvale_order/` the generated applications; `mediafiles/dmlib/` the six packages; `console/`, `demo/` the skeleton's pages, adapted; `docs/` the two guides.
- `datagen/`: the engine, the schema reader, the order, response, dispatch, receipt, invoice and Torvale order generators and the exchange driver; `datagen/records/` the five library token records the writer maps codes with.
- `ubl/`: the Order (by profile), OrderResponse, DespatchAdvice, ReceiptAdvice and Invoice writers and readers, the profiles module and the instance reader. `data/ubl-2.3/`: the five OASIS document schemas with their import closure, and the OASIS examples.
- Names: a name taken from a standard is written as the standard writes it (DespatchAdvice, Despatch Advice, Catalogue); everything we write ourselves is en-US (dispatch).
- `sparql/`: the saved queries of the walk-through. `profiles/`: the two-models exhibit the generator writes. `settlement/`: the settle, settled-records and verify scripts, the conditions, the Receipts and responses, the key documents. `env/`: the two stacks' settings. `sdcstudio_downloads/`: the model packages and the apps, as SDCStudio produced them.

## Related

- [CordovaOS](https://github.com/Axius-SDC/CordovaOS): the skeleton, and a fictional nation's ten government domains on it.
- [FAIR Data Demo](https://github.com/SemanticDataCharter/FAIR_Data_Demo): three federal health studies on one component library, on the same skeleton.

## License

Apache-2.0. Halvorsen Foods and Kestrel Mercantile are fictitious; every identifier is GS1-shaped under a prefix GS1 does not issue.
