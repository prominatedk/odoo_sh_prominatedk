{
    "name": "Zinc WMS via FlexEDI",
    "summary": "Integrates Zinc WMS (Warehouse Management System) with Odoo inventory",
    "description": "Integrates Zinc Germany WMS (Warehouse Management System) with Odoo inventory. Integration is based on cXML specification version 1.2.050",
    "version": "2.1.1",
    "category": "Warehouse",
    "author": "VK Data ApS",
    "website": "https://vkdata.dk",
    "depends": [
        "sale",
        "purchase",
        "stock",
        "sale_stock",
        "delivery",
        "odoo_edi",
        "odoo_edi_stock_wms"
    ],
    "data": [
        'data/flexedi_document_format_data.xml',
        'data/flexedi_document_reception_endpoint_data.xml',
        'data/flexedi_document_status_endpoint_data.xml',
        'data/flexedi_document_document_wms_zinc_order_views.xml',
        'views/sale_order_views.xml',
        'views/res_company_views.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "license": "OPL-1"
}
