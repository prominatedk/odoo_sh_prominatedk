{
    "name": "Primecargo WMS via FlexEDI",
    "summary": "Integrates PrimeCargo WMS (Warehouse Management System) with Odoo inventory",
    "description": "Integrates PrimeCargo WMS (Warehouse Management System) with Odoo inventory. Integration is based on PrimeCargo XML format version 1.6.8",
    "version": "1.5.3",
    "category": "Customization",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        "sale",
        "sale_margin",
        "purchase",
        "stock",
        "delivery",
        "odoo_edi"
    ],
    "data": [
        "security/ir.model.access.csv",
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/res_country_views.xml',
        'views/product_primecargo_shipping_views.xml',
        'data/ir_cron.xml'
    ],
    "installable": True,
    "license": "OPL-1"
}
