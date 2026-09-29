# HalvorsenDemo for the people who sign

Halvorsen Foods is fictitious. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This demonstration is built so the verdict survives a question. This release runs six beats, on the purchase order, the supplier's response, the dispatch advice and the receipt; the other two arrive with the settlement and the second retailer's model.

## What you are looking at

Two stacks on one machine. The retailer, Kestrel Mercantile, also fictitious, generates a year of purchase orders as records of a published model. On the way out of its stack each record is written as a standard document, a UBL 2.3 Order, the format the retailer's trading partners already accept. On the way in to the supplier's stack, Halvorsen Foods, each document is read back into a record of the same model.

Open the same order on both sides. The values are the same. What differs is the provenance each record carries: the retailer's says its order system generated it; the supplier's names the document it was read from, the translator that read it, and when. Neither side mapped anything. The model is the agreement.

## The six points this release makes

1. **The document is a projection of the record.** The retailer's system of record is the governed record, not the file. The file is written from it, checked against the standard's own schema, and read back into an identical record. If the standard changes, the projection changes; the record does not.

2. **The party is one component.** Buyer, seller and delivery party are the same organization name and address components the published Default library provides, the ones a government's person record and a hospital's organization record compose in the other two demonstrations. No table says a buyer and a seller are both organizations. The component does.

3. **The answer, line by line.** The supplier answers every order within a day, as a record: accepted, one line cut to what is in stock, one line rejected, or one line substituted. The response goes back the same way the order came, a standard document out of one stack and read into the other, and on the retailer's side it says which document it came from. Open the order and its response side by side: the same order identifier, the same component, no lookup table between them.

4. **The rule that changed.** The supplier ships the day before each delivery window, and the advice names, for every pallet, the version of the retailer's pack specification it was packed to. The retailer replaced that specification on the first of July. Ask the store for the dispatches after July packed to the January version and it names them, from the record, with no reconstruction. That is the fact the story's notice did not carry.

5. **The identifier that expired.** Every pallet is an asset with an identifier from the pool operator and the period that identifier is valid for. The record carries the period; the standard document written from it carries the period; the retailer's copy, read from that document, carries the period. Ask the store for the dispatches whose pallet identifier stops being valid on the day the advice was sent and it names them.

6. **The verdict, in the record.** The retailer receives each shipment the day after it was sent and checks every pallet on that day against both rules. The receipt advice holds the answers beside the facts they were judged on: the identifier and its period, the day received, the version packed to and the version in force. A failing pallet is accepted with an exception that says what was found and against which rule, and the record moves to the problem state. It goes back to the supplier as a standard document and reads into the same record there. Two shipments in the year left on the last day of June packed to the rule in force that day and arrived on the first of July, when it was not. That is the story's notice, and this time both sides can read why.

## What comes next

The verdict settled with a receipt that verifies offline, and the same order under two retailers' profile models. Each is a beat of the walk-through, listed on the page, and each arrives with the document that carries it.

## What this is not

Nothing here comes from any proprietary standard. The concepts are the OASIS Universal Business Language's, the identifiers are GS1's, and both companies are invented.
