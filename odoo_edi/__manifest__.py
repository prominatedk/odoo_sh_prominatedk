# -*- coding: utf-8 -*-
{
    'name': "FlexEDI Framework",

    'summary': """
        This module serves as a base framework for EDI integration with Odoo""",

    'description': """
        This module serves as a framework for integrating EDI communication with Odoo Enterprise.

        The purpose of this module is to serve as a base implementation and contains the basic views, data models, python classes and other base code required.
    """,

    'author': "VK Data ApS",
    'website': "https://vkdata.dk",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Specific Industry Applications',
    'version': '4.0.0',
    'license': 'OPL-1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/odoo_edi_menus.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/uom_uom_views.xml',
        'views/res_partner_views.xml',
        'views/flexedi_document_reception_endpoint_views.xml',
        'views/flexedi_document_status_endpoint_views.xml',
        'views/flexedi_document_format_views.xml',
        'data/odoo_edi_product_uom_data.xml',
        'data/odoo_edi_tax_scheme_data.xml',
        'data/odoo_edi_tax_category_data.xml',
        'data/ir_cron_data.xml',
    ],

    'post_init_hook': '_post_install_hook_map_uom'
}
