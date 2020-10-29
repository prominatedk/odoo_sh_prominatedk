{
    "name": "Prominate Webshop Integration",
    "summary": "Stock Syncronization",
    "description": "This module syncronizes the stock quantities between Odoo and the webshop",
    "version": "1.0.0",
    "category": "E-Commerce",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        'sale',
        'stock',
        'sale_stock'
    ],
    "data": [
        'views/stock_picking_view.xml',
        'views/product_view.xml',
        'views/res_config_view.xml',
        'views/sale_order_view.xml',
        'data/ir_cron.xml',
    ],
    "installable": True,
    "license": "OPL-1"
}