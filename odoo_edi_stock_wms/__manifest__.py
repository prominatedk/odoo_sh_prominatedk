# -*- coding: utf-8 -*-
{
    'name': "FlexEDI Warehouse Management (WMS)",

    'summary': """
        Implements support for using EDI as a communication method for warehouse management operations""",

    'description': """
        This module implements the necessary data structures and concepts that are required for handling
        EDI communication of warehouse management operations between Odoo and WMS providers.
        This module does not contain any of the logic required to communicate with a specific provider.
        Such logic is built as extensions on top
    """,

    'author': "VK Data ApS",
    'website': "https://vkdata.dk",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Warehouse',
    'version': '2.0.0',

    # any module necessary for this one to work correctly
    'depends': ['odoo_edi', 'stock'],

    'license': 'OPL-1',

    # always loaded
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/flexedi_document_wms_picking_views.xml',
        'views/res_company_views.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
    ],
}
