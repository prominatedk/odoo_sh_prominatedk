{
    "name": "Primecargo WMS",
    "summary": "Please create a short summary for your new module",
    "description": "Please create an in depth description of your new module",
    "version": "1.3.11",
    "category": "Customization",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        "sale",
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
