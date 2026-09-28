# HalvorsenDemo

Halvorsen Foods is a fictitious food manufacturer. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This is the demonstration in which the verdict survives a question. Two stacks on one machine, the supplier and the retailer, exchange business documents as governed records composed from the published component libraries and the business documents library built from the OASIS Universal Business Language and GS1 identifiers, with the document written on the way out of one stack and read on the way in to the other. Every record carries its provenance and the model that governs it. The document is a projection of the record.

**Scheduled for the first quarter of 2027. Private until it ships.** This is release 4.1.0: the Order, the exchange, and the first two of the six beats. Built on the CordovaOS 4.4.2 skeleton, the way the FAIR Data Demo was.

## Two guides, depending on why you are here

- [For the people who sign](app/sdc4/docs/FOR-DECISION-MAKERS.md): what the two stacks show, in plain terms.
- [For the people who run it](app/sdc4/docs/FOR-IT-STAFF.md): the stacks, the exchange, the loader, the queries.

## Run it locally

```bash
git clone https://github.com/SemanticDataCharter/HalvorsenDemo.git
cd HalvorsenDemo
make demo
```

`make demo` starts both stacks, generates a year of purchase orders on the host (about five seconds), and loads each side. Then open:

- http://localhost:18300/console/ the retailer, Kestrel Mercantile: 52 orders its order system generated.
- http://localhost:18200/console/ the supplier, Halvorsen Foods: the same 52 orders, each read from the UBL 2.3 document the retailer sent, and saying so.

Measured on the first run: 52 records and 52 named graphs on each side, none invalid, loaded in six seconds each; the saved queries answer in half a second and a fiftieth of a second (`sparql/README.md`).

`make down` stops both. Two stacks need about 14 GB of RAM; `HALVORSEN_ORDERS=260 make demo` generates five years.

## What runs in this release

| Beat | What it shows | Where |
|---|---|---|
| 1. The order as a record | One order as table, document and graph; beside it the UBL Order it was written to, byte for byte the same when read back | the console, either stack; saved query 1 |
| 2. The party is one component | Buyer, seller and delivery party on the same Default `organization-name` and address components a NIEM person and a FHIR organization compose | saved query 2, the entity graph |

The console's question, on either stack: where did every record come from, and what does it hold? The retailer's records name its order system as the PROV agent; the supplier's name the document each was read from and the translator that read it. The store answers from the bound components.

## What comes with the next documents

3. The rule that changed: the despatch advice against two versions of the retailer's pack specification, both in the store with dates.
4. The identifier that expired: the pallet identifier with its validity range; the notice sent inside it and received outside it.
5. The verdict, examinable: the deduction as the OrderProblem transition, settled with a receipt that verifies offline.
6. Two profiles: the same order under two retailers' models; what each requires, and which the receipt names.

## How it was built

1. The Order model: 147 components authored from the UBL 2.3 common library on the Default and ProvGov libraries by identifier slot, published in the SDCStudio project Business Documents, the ProvGov `order` workflow bound. The application SDCStudio generated for it is in `app/sdc4/order/`, verbatim; the package and the app zip as downloaded are in `sdcstudio_downloads/`.
2. The exchange: `ubl/order.py` writes a conformant UBL 2.3 Order from a record and reads one into a record; `datagen/` generates the retailer's orders on the template engine, writes each as a document, validates it against the OASIS schema, and reads it back as the supplier's record. `datagen/tests/` holds the round trip.
3. The stack: the CordovaOS 4.4.2 skeleton (settings, compose, batch loader, console, demo pages, entity graph) run twice from one compose file, `env/halvorsen.env` and `env/retailer.env` giving each its project name, ports and data directory.

## Repository structure

- `app/sdc4/`: the Django project; `order/` the generated application; `mediafiles/dmlib/` the Order package; `console/`, `demo/` the skeleton's pages, adapted; `docs/` the two guides.
- `datagen/`: the engine, the schema reader, the Halvorsen generator and the exchange driver; `datagen/records/` the four library token records the writer maps codes with.
- `ubl/`: the Order writer, reader and instance reader. `data/ubl-2.3/`: the OASIS Order schema with its import closure, and the OASIS example.
- `sparql/`: the saved queries of the walk-through. `env/`: the two stacks' settings. `sdcstudio_downloads/`: the model package and the app, as SDCStudio produced them.

## Related

- [CordovaOS](https://github.com/Axius-SDC/CordovaOS): the skeleton, and a fictional nation's ten government domains on it.
- [FAIR Data Demo](https://github.com/SemanticDataCharter/FAIR_Data_Demo): three federal health studies on one component library, on the same skeleton.

## License

Apache-2.0. Halvorsen Foods and Kestrel Mercantile are fictitious; every identifier is GS1-shaped under a prefix GS1 does not issue.
