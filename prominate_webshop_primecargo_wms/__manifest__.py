{
    "name": "Customization of PrimeCargo WMS for Prominate webshop",
    "summary": "Customization of data flowing from the PrimeCargo WMS integration into Odoo in order for certain data to flow to the webshop",
    "description": "Customization of data flowing from the PrimeCargo WMS integration into Odoo in order for certain data to flow to the webshop",
    "version": "1.0.0",
    "category": "Customization",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        "odoo_edi_primecargo_wms",
        "prominate_webshop_integration"
    ],
    "data": [
        'views/product_primecargo_shipping_views.xml'
    ],
    "installable": True,
    "license": "LGPL-3"
}
