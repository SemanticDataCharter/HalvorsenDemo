# Receipts issued but not held

Two Receipts the issuer signed and charged that name nothing the generator writes. They stay here as the record of the credit spent; `index.json` does not list them, `settled.py` writes nothing for them, and the Settlements page does not show them.

- `zlpz1ndvkks8telfvbi40t7g.json`: the first issuance of 4.1.6 named the parties by `did:web` identifiers on `.example` domains; the issuer resolves a party's key document over HTTPS when a trigger arrives, so no trigger could land. The parties' key documents were then published on the company site and the Receipts re-issued.
- `vbcevxxjgqqeym12c5zmvefk.json` (and its envelope): the first issuance of the Torvale order's release, in 4.1.8, named the supplier's record as generated that day; a translated record's instance identifier was drawn from an unseeded generator, so the next `make generate` could not write the same bytes. The instance identifiers are seeded since (`idrng` in `datagen/generate_all.py`, two runs byte-identical), and the Receipt was re-issued as `c5xx3x87h609sbwp2dn9gart`.
