{
    "name": "Prominate Webshop Information",
    "summary": "Adds relevant fields for data to/from external webshop",
    "description": "This module handles information to be shared between Odoo and the webshop",
    "version": "1.1.0",
    "category": "E-Commerce",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        'product',
        'sale',
        'stock',
        'sale_stock',
    ],
    "data": [
        'views/product_template_views.xml',
    ],
    "installable": True,
    "license": "OPL-1"
}