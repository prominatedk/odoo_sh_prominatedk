{
    "name": "Primecargo WMS via FlexEDI",
    "summary": "Integrates PrimeCargo WMS (Warehouse Management System) with Odoo inventory",
    "description": "Integrates PrimeCargo WMS (Warehouse Management System) with Odoo inventory. Integration is based on PrimeCargo XML format version 1.6.8",
    "version": "2.0.0",
    "category": "Warehouse",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        "sale",
        "purchase",
        "stock",
        "delivery",
        "odoo_edi",
        "odoo_edi_stock_wms"
    ],
    "data": [
        'data/flexedi_document_format_data.xml',
        'data/flexedi_document_reception_endpoint_data.xml',
        'data/flexedi_document_status_endpoint_data.xml',
        'views/res_country_views.xml',
        'views/res_company_views.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "license": "OPL-1"
}
