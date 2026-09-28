"""
The walk-through: the order as a governed record, the document as its projection.

Two of the six beats of the demonstration run in this release, on the Order alone. The other four
need the order response and the despatch advice (the rule that changed, the identifier that expired,
the verdict) and the two retailer profile models (two profiles), and are listed here as what comes.
"""

BEATS = [
    {
        'number': 1,
        'title': 'The order as a record',
        'query_number': 1,
        'icon': 'bi-file-earmark-text',
        'color': 'primary',
        'narrative': (
            'The retailer generated this order as a record of the published Order model: forty-five '
            'UBL concepts composed on the Default and ProvGov libraries, with the order workflow bound. '
            'On the way out of the retailer\'s stack it was written as a UBL 2.3 Order document, checked '
            'against the OASIS schema; on the way in to the supplier\'s it was read back into a record of '
            'the same model. The query lists every value the record carries, on whichever stack you are '
            'looking at; open the record and the Document tab shows the XML instance, byte for byte the '
            'thing the store answers from. The document is a projection of the record, not the other way '
            'round.'
        ),
        'query_label': 'Show the order',
    },
    {
        'number': 2,
        'title': 'The party is one component',
        'query_number': 2,
        'icon': 'bi-people',
        'color': 'success',
        'narrative': (
            'Buyer, seller and delivery party are the same Organization Name and address components '
            'the Default library publishes, the ones a NIEM person\'s organization and a FHIR '
            'organization compose in the other demonstrations. The query groups every party this stack\'s '
            'records name by that one component and counts the orders each appears on. No mapping table '
            'says that a buyer and a seller are both organizations; the component does.'
        ),
        'query_label': 'Show the parties',
    },
]

#: The beats the next releases add, in the order the documents arrive.
COMING = [
    ('The rule that changed', 'the despatch advice against two versions of the retailer\'s pack specification, both in the store with dates'),
    ('The identifier that expired', 'the pallet identifier with its validity range; the notice sent inside it and received outside it'),
    ('The verdict, examinable', 'the deduction as the OrderProblem transition, settled with a receipt that verifies offline'),
    ('Two profiles', 'the same order under two retailers\' models; what each requires, and which the receipt names'),
]
