# -*- coding: utf-8 -*-
{
    'name': "Monthly Sales Report",
    'summary': """This provide functionality to add monthly sales report""",
    'description': """This provide functionality to add monthly sales report""",
    'author': "Nisus Solutions (Pvt) Ltd",
    'website': "http://www.nisus.lk",
    'category': 'Sales',
    'version': '1.0.8',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/monthly_sales_report_view.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [],
}
