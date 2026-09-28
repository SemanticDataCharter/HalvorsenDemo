# HalvorsenDemo

Halvorsen Foods is a fictitious food manufacturer. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This is the demonstration in which the verdict survives a question. Two stacks on one machine, the supplier and the retailer, exchange business documents as governed records composed from the published component libraries and the business documents library built from the OASIS Universal Business Language and GS1 identifiers, with the document written on the way out of one stack and read on the way in to the other. Every record carries its provenance and the model that governs it. The document is a projection of the record.

**Scheduled for the first quarter of 2027. Private until it ships.** This is release 4.1.2: the Order, the Order Response and the Despatch Advice, the exchange in both directions, and five beats. Built on the CordovaOS 4.4.2 skeleton, the way the FAIR Data Demo was.

## Two guides, depending on why you are here

- [For the people who sign](app/sdc4/docs/FOR-DECISION-MAKERS.md): what the two stacks show, in plain terms.
- [For the people who run it](app/sdc4/docs/FOR-IT-STAFF.md): the stacks, the exchange, the loader, the queries.

## Run it locally

```bash
git clone https://github.com/SemanticDataCharter/HalvorsenDemo.git
cd HalvorsenDemo
make demo
```

`make demo` starts both stacks, generates a year of purchase orders, responses and despatch advices on the host (about twenty seconds), and loads each side. Then open:

- http://localhost:18300/console/ the retailer, Kestrel Mercantile: 52 orders its order system generated, 52 responses read from the UBL 2.3 OrderResponse documents the supplier sent back, and 52 despatch advices read from the UBL 2.3 DespatchAdvice documents that followed.
- http://localhost:18200/console/ the supplier, Halvorsen Foods: the same 52 orders, each read from the UBL 2.3 Order the retailer sent, 52 responses its order system generated within a day of each, and 52 despatch advices its warehouse system generated the day before each delivery window.

Measured on the first run of 4.1.2: 156 records and 156 named graphs on each side, 52 orders, 52 responses and 52 despatch advices, none invalid, loaded in 28 seconds on the retailer and 23 on the supplier; the console question answers 156 records with 104 read from a document on the retailer and 52 on the supplier; the five saved queries answer in 1.7, 0.01, 0.08, 0.03 and 0.03 seconds on a cold store (`sparql/README.md`). Of the 52 despatches, four carry a pallet identifier that lapses on the day of despatch and two are packed to the pack specification the retailer replaced in July; both queries name them.

`make down` stops both. Two stacks need about 14 GB of RAM; `HALVORSEN_ORDERS=260 make demo` generates five years.

## What runs in this release

| Beat | What it shows | Where |
|---|---|---|
| 1. The order as a record | One order as table, document and graph; beside it the UBL Order it was written to, byte for byte the same when read back | the console, either stack; saved query 1 |
| 2. The party is one component | Buyer, seller and delivery party on the same Default `organization-name` and address components a NIEM person and a FHIR organization compose | saved query 2, the entity graph |
| 3. The answer, line by line | Each response joined to its order on the Order ID, the same component in both models; accepted, cut, rejected or substituted, line by line on the record's table pane | saved query 3, the console |
| 4. The rule that changed | Each despatch joined to its order, the pack specification version its pallets were packed to beside the day it was sent; the retailer's version changed on 1 July, and a later despatch packed to the January version is the notice of the story | saved query 4 |
| 5. The identifier that expired | Each despatch with its pallet identifiers and the earliest day one stops being valid; where that is the day the advice was sent, the notice went out inside the period and the goods arrive outside it | saved query 5, the record's table pane |

The console's question, on either stack: where did every record come from, and what does it hold? The retailer's records name its order system as the PROV agent; the supplier's name the document each was read from and the translator that read it. The store answers from the bound components.

## What comes with the next documents

6. The verdict, examinable: the deduction as the OrderProblem transition, settled with a receipt that verifies offline.
7. Two profiles: the same order under two retailers' models; what each requires, and which the receipt names.

## How it was built

1. The Order, Order Response and Despatch Advice models: 243 components authored from the UBL 2.3 common library and GS1's identifiers on the Default and ProvGov libraries by identifier slot, published in the SDCStudio project Business Documents, the ProvGov `order` workflow bound. The applications SDCStudio generated for them are in `app/sdc4/order/`, `app/sdc4/order_response/` and `app/sdc4/despatch_advice/`, verbatim; the packages and the app zips as downloaded are in `sdcstudio_downloads/`.
2. The exchange: `ubl/order.py`, `ubl/order_response.py` and `ubl/despatch_advice.py` write a conformant UBL 2.3 document from a record and read one into a record; `datagen/` generates the retailer's orders, the supplier's responses and the supplier's despatch advices on the template engine, writes each as a document, validates it against the OASIS schema of its type, and reads it back on the other side. `datagen/tests/` holds the three round trips. Where UBL has no element for what the despatch record names, the module says where it went: the pallet as transport equipment with its identifier's validity period as the equipment's document reference, the pack specification version as the unit's document reference.
3. The stack: the CordovaOS 4.4.2 skeleton (settings, compose, batch loader, console, demo pages, entity graph) run twice from one compose file, `env/halvorsen.env` and `env/retailer.env` giving each its project name, ports and data directory.

## Repository structure

- `app/sdc4/`: the Django project; `order/`, `order_response/` and `despatch_advice/` the generated applications; `mediafiles/dmlib/` the three packages; `console/`, `demo/` the skeleton's pages, adapted; `docs/` the two guides.
- `datagen/`: the engine, the schema reader, the order, response and despatch generators and the exchange driver; `datagen/records/` the five library token records the writer maps codes with.
- `ubl/`: the Order, OrderResponse and DespatchAdvice writers and readers, and the instance reader. `data/ubl-2.3/`: the three OASIS document schemas with their import closure, and the OASIS examples.
- `sparql/`: the saved queries of the walk-through. `env/`: the two stacks' settings. `sdcstudio_downloads/`: the model package and the app, as SDCStudio produced them.

## Related

- [CordovaOS](https://github.com/Axius-SDC/CordovaOS): the skeleton, and a fictional nation's ten government domains on it.
- [FAIR Data Demo](https://github.com/SemanticDataCharter/FAIR_Data_Demo): three federal health studies on one component library, on the same skeleton.

## License

Apache-2.0. Halvorsen Foods and Kestrel Mercantile are fictitious; every identifier is GS1-shaped under a prefix GS1 does not issue.
