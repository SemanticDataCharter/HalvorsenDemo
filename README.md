# HalvorsenDemo

Halvorsen Foods is a fictitious food manufacturer. It shipped a mixed pallet to a large retailer and took a three percent deduction for a non-compliant advance ship notice. Eleven days of reconstruction found no mistake: the retailer's rule had changed on a date the notice did not carry, and the pallet identifier had stopped being valid on a date the notice also did not carry. Two correct systems, one working integration, a verdict nobody could examine.

This is the demonstration in which the verdict survives a question. Two stacks on one machine, the supplier and the retailer, exchange a year of purchase orders, acknowledgments, ship notices and invoices as governed records composed from the published component libraries and the [X12 library](https://github.com/Axius-SDC/X12Library), with the X12 file written on the way out of one stack and read on the way in to the other. Every record carries its provenance and the model that governs it; every change of an order's state settles against the model's workflow with a receipt that can be verified offline. The file is a projection of the record.

**Scheduled for the first quarter of 2027.** Built on the CordovaOS 4.4.1 skeleton, the way the FAIR Data Demo was. Private until the X12 library's licensing posture is settled.
