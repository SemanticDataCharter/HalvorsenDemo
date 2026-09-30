# HalvorsenDemo: two stacks on one machine, the supplier (Halvorsen Foods) and the retailer (Kestrel Mercantile),
# exchanging orders as governed records with the UBL 2.3 document written on the way out and read on the way in.
#
# Requirements: Docker (or Podman) with the compose plugin, ~14GB free RAM for both stacks (~7GB for one),
# Python 3.12 on the host for data generation (lxml, xmlschema, pyyaml).
#
# Typical first run:
#   make demo        # both stacks up, the year of orders generated, both sides loaded
# then open http://localhost:18300/console/ (the retailer) and http://localhost:18200/console/ (the supplier)
COMPOSE_FILE := app/sdc4/docker-compose.yml
HALVORSEN := docker compose -p halvorsen --env-file env/halvorsen.env -f $(COMPOSE_FILE)
RETAILER  := docker compose -p retailer  --env-file env/retailer.env  -f $(COMPOSE_FILE)
HALVORSEN_URL := http://localhost:18200
RETAILER_URL  := http://localhost:18300
.PHONY: help up down demo generate load load-halvorsen load-retailer wait test clean version release-check pull build settle verify-settlements

help:
	@echo "HalvorsenDemo quickstart:"
	@echo "  make demo            Start both stacks, generate the year of orders, load both sides."
	@echo "  make up / make down  Start or stop both stacks."
	@echo "  make generate        Generate the records and the UBL documents on the host (writes app/sdc4/import_data/)."
	@echo "  make load            Load the retailer's records, then the supplier's."
	@echo "  make test            Run the datagen and round-trip tests on the host."
	@echo "  make settle          Settle the deductions live against the issuer (needs SDCRECEIPT_TOKEN or settlement/.token; one credit a Receipt)."
	@echo "  make verify-settlements  Verify the Receipts held in settlement/ offline, against the record and schema bytes here."
	@echo ""
	@echo "  $(RETAILER_URL)/console/    the retailer's records (Kestrel Mercantile)"
	@echo "  $(HALVORSEN_URL)/console/   the supplier's records (Halvorsen Foods), each read from a document"

up:
	$(RETAILER) up -d
	$(HALVORSEN) up -d

down:
	$(HALVORSEN) down
	$(RETAILER) down

wait:
	@echo "Waiting for both web apps (first run can take 1-2 min)..."
	@until curl -sf $(RETAILER_URL)/ >/dev/null 2>&1; do sleep 3; done
	@until curl -sf $(HALVORSEN_URL)/ >/dev/null 2>&1; do sleep 3; done
	@echo "Both web apps are up."

# Generation runs on the host: the retailer's orders as records, each written as a UBL 2.3 Order into
# app/sdc4/import_data/exchange/, and each document read back into a supplier record.
generate:
	@python3 -m pip install -q -r datagen/requirements.txt
	cd datagen && python3 generate_all.py

# Loading runs in each web container (validates every instance under XSD 1.1, writes Postgres + GraphDB).
load-retailer: wait
	$(RETAILER) exec -T web python manage.py load_all_data --clear --batch 200

load-halvorsen: wait
	$(HALVORSEN) exec -T web python manage.py load_all_data --clear --batch 200

load: load-retailer load-halvorsen

demo: up generate load
	@echo ""
	@echo "Demo ready."
	@echo "  $(RETAILER_URL)/console/    the retailer's records"
	@echo "  $(HALVORSEN_URL)/console/   the supplier's records, each read from the retailer's document"

test:
	python3 -m pytest datagen/tests -q

clean: down
	rm -rf app/sdc4/import_data/halvorsen app/sdc4/import_data/retailer app/sdc4/import_data/exchange

version:            ## Print the version (app/sdc4/VERSION is the single source)
	@cat app/sdc4/VERSION

release-check:      ## What the release workflow checks: VERSION is tagged, tag is on main
	@v=$$(cat app/sdc4/VERSION); git rev-parse -q --verify "refs/tags/v$$v" >/dev/null && echo "tag v$$v exists" || echo "tag v$$v missing"

pull:               ## Pull the published web image for this version instead of building it (private package: docker login ghcr.io first)
	IMAGE_TAG=$$(cat app/sdc4/VERSION) $(RETAILER) pull web

build:               ## Build the web image locally (after a change to app/sdc4/requirements.txt)
	$(RETAILER) build web

# The settlement is issued live, once, by whoever holds an issuer token; what it writes under settlement/ is committed and
# verified offline at every run. make generate writes the settled records from the Receipts held.
settle:
	@python3 -m pip install -q -r datagen/requirements.txt
	python3 settlement/settle.py
	cd datagen && python3 generate_all.py

verify-settlements:
	python3 settlement/verify_all.py
