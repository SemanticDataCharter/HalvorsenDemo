# HalvorsenDemo for the people who sign

Halvorsen Foods is fictitious. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This demonstration is built so the verdict survives a question. This release runs the first two of its six beats, on the purchase order alone; the other four arrive with the order response and the despatch advice.

## What you are looking at

Two stacks on one machine. The retailer, Kestrel Mercantile, also fictitious, generates a year of purchase orders as records of a published model. On the way out of its stack each record is written as a standard document, a UBL 2.3 Order, the format the retailer's trading partners already accept. On the way in to the supplier's stack, Halvorsen Foods, each document is read back into a record of the same model.

Open the same order on both sides. The values are the same. What differs is the provenance each record carries: the retailer's says its order system generated it; the supplier's names the document it was read from, the translator that read it, and when. Neither side mapped anything. The model is the agreement.

## The two points this release makes

1. **The document is a projection of the record.** The retailer's system of record is the governed record, not the file. The file is written from it, checked against the standard's own schema, and read back into an identical record. If the standard changes, the projection changes; the record does not.

2. **The party is one component.** Buyer, seller and delivery party are the same organization name and address components the published Default library provides, the ones a government's person record and a hospital's organization record compose in the other two demonstrations. No table says a buyer and a seller are both organizations. The component does.

## What comes next

The rule that changed, the identifier that expired, the verdict that verifies offline, and the same order under two retailers' profile models. Each is a beat of the walk-through, listed on the page, and each arrives with the document that carries it.

## What this is not

Nothing here comes from any proprietary standard. The concepts are the OASIS Universal Business Language's, the identifiers are GS1's, and both companies are invented.
