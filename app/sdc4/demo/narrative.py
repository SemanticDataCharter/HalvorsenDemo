"""
The walk-through: the order as a governed record, the document as its projection.

Six beats run in this release, on the Order, the Order Response, the Despatch Advice and the
Receipt Advice. The other two need the settlement receipt (the verdict settled) and the two
retailer profile models (two profiles), and are listed here as what comes.
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
    {
        'number': 3,
        'title': 'The answer, line by line',
        'query_number': 3,
        'icon': 'bi-reply',
        'color': 'info',
        'narrative': (
            'The supplier answers every order within a day, as a record of the published Order Response '
            'model: accepted as ordered, one line cut to what is in stock, one line rejected, or one line '
            'substituted by the next product of the family. The response was written out of the supplier\'s '
            'stack as a UBL 2.3 OrderResponse and read into the retailer\'s. The query joins each response '
            'to the order it answers on the Order ID, the same component in both models, and lists the '
            'answer to every line. On the retailer\'s stack the orders are generated and the responses read; '
            'on the supplier\'s it is the other way round, and the store says so.'
        ),
        'query_label': 'Show the answers',
    },
    {
        'number': 4,
        'title': 'The rule that changed',
        'query_number': 4,
        'icon': 'bi-box-seam',
        'color': 'warning',
        'narrative': (
            'The supplier ships every answered order the day before the delivery window opens, as a record of '
            'the published Despatch Advice model: the pallets by serial shipping container code, the cases on '
            'each, and the version of the retailer\'s pack specification each pallet was packed to. The '
            'retailer replaced that specification on the first of July. The query joins each dispatch to its '
            'order on the Order ID and lists the version its pallets name beside the day it was sent; a dispatch '
            'after July packed to the January version is the non-compliant notice of the story, and the store '
            'says so from the record, with no table of versions and no reconstruction.'
        ),
        'query_label': 'Show the versions',
    },
    {
        'number': 5,
        'title': 'The identifier that expired',
        'query_number': 5,
        'icon': 'bi-upc-scan',
        'color': 'danger',
        'narrative': (
            'Each pallet is an asset with an identifier from the pool operator and the period that identifier '
            'is valid for. The record carries the period; so does the UBL 2.3 DespatchAdvice written from it, '
            'as the equipment\'s validity period, and the retailer\'s translator reads it back. The query lists '
            'every dispatch with its pallet identifiers, the earliest day one of them stops being valid, and the '
            'day the advice was sent. Where the two are the same day, the notice was sent inside the period and '
            'the goods arrive outside it. The receipt advice, in the next release, holds that against the day '
            'they were received.'
        ),
        'query_label': 'Show the identifiers',
    },
    {
        'number': 6,
        'title': 'The verdict, in the record',
        'query_number': 6,
        'icon': 'bi-clipboard-check',
        'color': 'dark',
        'narrative': (
            'The retailer receives each shipment the day after it was sent and checks every pallet on that day '
            'against both rules: was the identifier within its period, was the unit packed to the version in '
            'force. The receipt advice holds the answers beside the facts they were judged on, the identifier, its '
            'period, the received date, the version packed to and the version in force, and a failing pallet '
            'puts the record in the OrderProblem state. Written as a UBL 2.3 ReceiptAdvice and read into the '
            'supplier\'s stack, the same record on both sides. The query lists every receipt with its dispatch, '
            'the day received and the two yes-or-no answers its pallets carry. Nobody reconstructs anything; the '
            'deduction, when it comes, has a record to be examined against.'
        ),
        'query_label': 'Show the verdicts',
    },
]

#: The beats the next releases add, in the order the documents arrive.
COMING = [
    ('The verdict, settled', 'the deduction as the OrderProblem transition, settled with a receipt that verifies offline'),
    ('Two profiles', 'the same order under two retailers\' models; what each requires, and which the receipt names'),
]
