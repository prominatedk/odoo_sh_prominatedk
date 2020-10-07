# -*- coding: utf-8 -*-
{
    'name': 'Odoo Bankintegration',
    'version': '2.5.1',
    'category': 'Accounting',
    'description': """
Odoo Bankintegration.
=======================================
This module uses the bankintegration.dk API to import bank statements into Odoo and also allow payment of vendor bills.
""",
    'author': 'Odoo House, VK DATA ApS',
    'website': 'http://odoodanmark.dk',
    'summary': 'Odoo Bankintegration',
    'sequence': 20,
    'depends': ['base', 'base_vat', 'base_iban', 'account', 'account_bank_statement_import'],
    'data': [
        'views/account_bank_statement_line_views.xml',
        'views/account_invoice_views.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_journal_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_bank_views.xml',
        'views/res_company_views.xml',
        'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
