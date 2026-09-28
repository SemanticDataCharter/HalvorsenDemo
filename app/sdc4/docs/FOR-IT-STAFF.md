# HalvorsenDemo for the people who run it

Two stacks from one compose file, the CordovaOS skeleton each: PostgreSQL, GraphDB, SirixDB, Keycloak, Redis, the Django web app and a Celery worker. `make demo` starts both, generates the year of orders on the host, and loads each side in its own web container.

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

`app/sdc4/order/` is the standalone application SDCStudio generated for the published Order model (`h8bttbt9afwzf9zs4jhae566`), installed verbatim; `sdcstudio_downloads/` holds the zip and the model package as downloaded. The model composes 45 UBL 2.3 concepts on the Default and ProvGov libraries by identifier slot, with the ProvGov `order` workflow bound (schema.org OrderStatus). The skeleton discovers the application by its directory; nothing is registered by hand.

## 2. The exchange, and where each record says it came from

`datagen/generate_all.py` does three things per order. It generates the retailer's record on the template engine (`datagen/engine.py`: label paths, no element identifiers; the engine fills the model's own instance template). It writes the record as a UBL 2.3 Order (`ubl/order.py`, `write_order`), validated against the OASIS Order schema (`data/ubl-2.3/xsd/`, the published import closure) before it is written to `app/sdc4/import_data/exchange/`. It reads that document back (`read_order`) into the supplier's record: the same order values, with the document as the PROV entity the activity used, the translator as the agent, and the document as the audit's location.

Two leaves of the record have no home in a UBL Order (a contact point's method and use); they are named in `ubl/order.py` as `NOT_PROJECTED`. Everything else round-trips, and the supplier's record projects back to the document byte for byte. `datagen/tests/test_round_trip.py` holds that.

## 3. Loading

`load_all_data` in each web container validates every instance under the model's XSD 1.1 schema on the way in, writes PostgreSQL and one named graph per record in GraphDB. Each stack mounts its own `app/sdc4/import_data/<stack>/` as `/app/import_data`, so the retailer loads `retailer/order/` and the supplier `halvorsen/order/`. Every load clears the previous graphs first: a reload mints fresh instance identifiers, and the stale graphs would otherwise inflate every count.

## 4. The console and the saved questions

`/console/` on either stack: the records, and one question answered by the store, where the records came from (the PROV agent, bound by its component identifier) and the orders by month with their payable totals. `/demo/` carries the two saved queries of the walk-through (`sparql/`), the SPARQL explorer and the entity graph, which joins a record to its counterpart on the Order ID component.

Every query binds its component: the reifier is addressed by its label and the component read from its IRI. A triple term with the component unbound makes GraphDB scan every reifier in the store, which cost the other demonstrations a six-minute query before it was written down.

## 5. What this release does not show

The order response, the despatch advice and the invoice; the two retailer profile models; the settlement receipt on the OrderProblem transition. They are the remaining four beats and arrive with those documents.
