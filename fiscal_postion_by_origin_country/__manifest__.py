{
    "name": "Fiscal Position using origin country",
    "summary": "Allows to get fiscal position based on country of origin",
    "description": "This module implements the necessary internal logic to allow Odoo to compute the fiscal position using a country of origin as an additional condition. This makes it possible to build functionality to have a company in Denmark and ship orders from a warehouse in another country such as Germany, France, Norway, China etc.",
    "version": "1.0.0",
    "category": "Accounting",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        'account'
    ],
    "data": [
        'views/account_fidcal_position_views.xml',
    ],
    "installable": True,
    "license": "OPL-1"
}