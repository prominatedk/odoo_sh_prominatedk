{
    "name": "Prominate Webshop Integration",
    "summary": "Stock Syncronization",
    "description": "This module syncronizes the stock quantities between Odoo and the webshop",
    "version": "1.7.7",
    "category": "E-Commerce",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        'sale',
        'stock',
        'sale_stock',
        'prominate_odoo_edi_primecargo_wms'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/stock_warehouse_view.xml',
        'views/product_view.xml',
        'views/res_config_view.xml',
        'views/sale_order_view.xml',
        'views/error_log_view.xml',
        'data/ir_cron.xml',
    ],
    "installable": True,
    "license": "LGPL-3"
}