# HalvorsenDemo for the people who run it

Two stacks from one compose file, the CordovaOS skeleton each: PostgreSQL, GraphDB, SirixDB, Keycloak, Redis, the Django web app and a Celery worker. `make demo` starts both, generates the year of orders, responses, dispatch advices, receipt advices and invoices on the host, and loads each side in its own web container.

## Getting it running

```
git clone https://github.com/SemanticDataCharter/HalvorsenDemo.git
cd HalvorsenDemo
make demo
```

Two stacks need about 14 GB of RAM. One stack alone (`docker compose -p retailer --env-file env/retailer.env -f app/sdc4/docker-compose.yml up -d`) needs about 7 GB.

| | Retailer (Kestrel Mercantile) | Supplier (Halvorsen Foods) |
|---|---|---|
| Web | http://localhost:18300 | http://localhost:18200 |
| GraphDB | http://localhost:17500 | http://localhost:17400 |
| Keycloak | http://localhost:18083 | http://localhost:18082 |
| PostgreSQL | 15435 | 15434 |
| SirixDB | 19446 | 19445 |
| Redis | 16382 | 16381 |

The project name, the ports and the data directory (`app/sdc4/mediafiles/<stack>/`) come from `env/<stack>.env`; the image, the model library (`app/sdc4/mediafiles/dmlib/`) and the Keycloak realm are shared. Both stacks run the same image, `ghcr.io/semanticdatacharter/halvorsendemo`.

## 1. The application is generated. The model is the source of truth.

`app/sdc4/order/`, `app/sdc4/order_response/`, `app/sdc4/despatch_advice/`, `app/sdc4/receipt_advice/` and `app/sdc4/invoice/` are the standalone applications SDCStudio generated for the published Order (`h8bttbt9afwzf9zs4jhae566`), Order Response (`kuntv2wlkw54h7nxe0kqhvi2`), Despatch Advice (`cacl4njrwanj15g3p3so8t6h`), Receipt Advice (`tog0v0p1zit1xwpxysxwpf3d`) and Invoice (`u19w614300a8ot4a7qnn2o1c`) models, installed verbatim; `sdcstudio_downloads/` holds the zips and the model packages as downloaded. The models compose the UBL 2.3 concepts and GS1's identifiers on the Default and ProvGov libraries by identifier slot, with the ProvGov `order` workflow bound. The skeleton discovers an application by its directory; nothing is registered by hand.

## 2. The exchange in both directions, and where each record says it came from

`datagen/generate_all.py` does three things per order. It generates the retailer's record on the template engine (`datagen/engine.py`: label paths, no element identifiers; the engine fills the model's own instance template). It writes the record as a UBL 2.3 Order (`ubl/order.py`, `write_order`), validated against the OASIS Order schema (`data/ubl-2.3/xsd/`, the published import closure) before it is written to `app/sdc4/import_data/exchange/`. It reads that document back (`read_order`) into the supplier's record: the same order values, with the document as the PROV entity the activity used, the translator as the agent, and the document as the audit's location.

Then the supplier answers. `datagen/halvorsen_responses.py` generates Halvorsen's response to each order as a record of the Order Response model in the supplier's stack (`import_data/halvorsen/order_response/`); `ubl/order_response.py` writes it as a UBL 2.3 OrderResponse, validated against the OASIS OrderResponse schema, into the exchange; the retailer's translator reads it back (`import_data/retailer/order_response/`). The answer to each line travels as the line item's `LineStatusCode` naming the library's line-response list; a document written with UBL's own status list reads back through a small map.

Then the supplier ships. `datagen/halvorsen_dispatch.py` generates the warehouse system's dispatch advice for each answered order as a record of the Despatch Advice model in the supplier's stack (`import_data/halvorsen/despatch_advice/`): the pallets by serial shipping container code, each with the pool operator's pallet identifier and the period it is valid for, the cases on it packed against the retailer's pack specification by version, and the temperature range for chilled goods. `ubl/dispatch_advice.py` writes it as a UBL 2.3 DespatchAdvice, validated against the OASIS DespatchAdvice schema, into the exchange; the retailer's translator reads it back (`import_data/retailer/despatch_advice/`). Where UBL has no element for what the record names, the module docstring says where it went: the pallet is `cac:TransportEquipment` and its identifier's validity period is the equipment's `cac:ShipmentDocumentReference` of type `Pallet identification`; the pack specification version is the unit's `cac:ShipmentDocumentReference` of type `Pack specification`; layers and cases are `cac:ContainedPackage` levels; the loaded height and weight are `cac:MeasurementDimension`s; the temperatures are in UN/ECE code CEL. Every twelfth order the first pallet's identifier lapses on the day of dispatch, and every twelfth after July a unit is packed to the specification version the retailer replaced (`KM-PACK-2026-01`, in force until 1 July 2026; `KM-PACK-2026-02` after).

Then the retailer receives. `datagen/halvorsen_receipts.py` generates the receiving system's receipt advice for each shipment on the day the window opens (`import_data/retailer/receipt_advice/`): every line counted against the dispatch, every handling unit checked on that day against the pallet identifier's validity period and the pack specification in force, with the two yes-or-no answers, the receiver's decision and the exception beside the facts; a failing unit puts the record in the OrderProblem state. `ubl/receipt_advice.py` writes it as a UBL 2.3 ReceiptAdvice (the checks as the unit's `cac:Status` elements naming the library component with an indication, the version in force as a second document reference) into the exchange; the supplier's translator reads it back (`import_data/halvorsen/receipt_advice/`).

The two answers are booleans, and the first run of 4.1.3 found that no boolean reached any generated application's graph: the generator named the value `xdboolean-value` where the reference model writes `true-value` or `false-value` (SDCStudio #714, fixed and deployed the same day). The four applications were regenerated, apps only, the packages untouched, and installed verbatim in 4.1.4; saved query 6 binds the two answers beside the receiving condition and the exception.

Then the supplier bills. `datagen/halvorsen_invoices.py` generates the billing system's invoice for each receipt (`import_data/halvorsen/invoice/`): every line at the received quantity and the confirmed price, the short and rejected cases left off, a deposit deducted every twelfth order, the order, dispatch and receipt lines it settles named in UBL's own line references; the state is OrderPaymentDue. `ubl/invoice.py` writes it as a UBL 2.3 Invoice into the exchange; the retailer's translator reads it back (`import_data/retailer/invoice/`). UBL's Invoice carries no document status, so that one leaf of the header is left out and named (`NOT_PROJECTED_INVOICE`).

Two leaves of the record have no home in a UBL Order (a contact point's method and use); they are named in `ubl/order.py` as `NOT_PROJECTED`. Everything else round-trips, and the supplier's record projects back to the document byte for byte. `datagen/tests/test_round_trip.py` holds that.

## 3. Loading

`load_all_data` in each web container validates every instance under the model's XSD 1.1 schema on the way in, writes PostgreSQL and one named graph per record in GraphDB. Each stack mounts its own `app/sdc4/import_data/<stack>/` as `/app/import_data`, so the retailer loads `retailer/order/`, `retailer/order_response/`, `retailer/despatch_advice/`, `retailer/receipt_advice/` and `retailer/invoice/`, the supplier the same five under `halvorsen/`. Every load clears the previous graphs first: a reload mints fresh instance identifiers, and the stale graphs would otherwise inflate every count.

## 4. The settlement

`settlement/settle.py` (or `make settle`) runs once, on the host, with an issuer token in `SDCRECEIPT_TOKEN` or `settlement/.token`. For every retailer receipt advice in the OrderProblem state it builds the deduction notice from the record and the invoice (three percent of the payable amount, the pallets accepted with an exception and what each failed), asks `POST /api/v1/vsl/settle` to settle OrderProblem to OrderProcessing between `did:web:kestrelmercantile.example` and `did:web:halvorsenfoods.example`, signs a trigger with each party's key and submits it to `/trigger`, and fetches the Receipt from `/receipt/<id>` as it finally stands. The first record is also asked to go to OrderDelivered, which governance refuses; the DENY Receipt is kept. The parties' keys are generated on first use with `sdcreceipt`; the private keys stay in `settlement/keys/` and are gitignored, the key documents are committed, and the issuer's published key document is saved as `settlement/issuer-keys.json`. `settlement/index.json` names, for every Receipt, the record file and the sha256 of its bytes. The generated data carries a pinned version in its agents' identifiers (`LIBRARY_VERSION` in `datagen/shared.py`, separate from the release number), because a Receipt names the record by the hash of its bytes and the first issuance was invalidated by a release bump that changed nothing else; bump the data version only when the data changes, and re-issue.

`make generate` writes the settled records: `settlement/settled.py` checks that the regenerated record's bytes are the bytes the Receipt names (the generator is deterministic, so they are) and writes a second record of the same receipt advice in OrderProcessing whose PROV activity is the settlement, its entity the Receipt (`urn:vsl:receipt:<id>`), its agent the settlement agent. `settlement/verify_all.py` and the Settlements page (`/demo/settlements/`) verify every Receipt with `sdcreceipt.verify` against the saved issuer key document, the parties' key documents, the record's bytes as the stack read them in (`/app/import_data/receipt_advice/`, the loader re-serializes what it stores, so the store is not the wire), and the schema's bytes in `mediafiles/dmlib/`; nothing reaches the issuer. On the supplier's stack the Receipts verify without the payload, because the bytes they name are the retailer's record, and the page says so. The web image carries `sdcreceipt`, and `settlement/` is mounted read-only at `/settlement`.

## 5. The console and the saved questions

`/console/` on either stack: the records, and one question answered by the store, where the records came from (the PROV agent, bound by its component identifier) and the documents that carry a payable amount, the orders, the responses and the invoices, by month and by model with their totals. `/demo/` carries the eight saved queries of the walk-through (`sparql/`), the SPARQL explorer and the entity graph, which joins a record to its counterpart, and a response or a dispatch to its order, on the Order ID component, and a receipt to its dispatch and an invoice to its receipt on the identifiers each names. A reifier in the graph is keyed by component and record, so the ten lines of one response share their reifiers, and so do the six pallets' validity periods and the delivery window of one dispatch, all on the Default library's date range: which answers a response holds, or the earliest day a dispatch's pallet identifiers stop being valid, is the graph's question; which line or which pallet is the record's, on its Table pane.

Every query binds its component: the reifier is addressed by its label and the component read from its IRI. A triple term with the component unbound makes GraphDB scan every reifier in the store, which cost the other demonstrations a six-minute query before it was written down.

## 6. What this release does not show

The two retailer profile models: the same order under two retailers' models, and which one a Receipt names. That is the remaining beat. The receipt advice holds the notice's two facts against the receipt date; the settlement receipt will make the deduction a transition anyone can verify offline.
