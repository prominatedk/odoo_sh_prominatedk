{
    'name': "Country Vat Number",
    'summary': 'Vat no. per country',
    'version': '1.0.3',
    'author': 'VK Data ApS',
    'category': 'Accounting',
    'description':'This module allows you to set a company vat no. for each country.',
    'website': 'https://vkdata.dk',
    'depends': ['account'],

    'data': [
        'views/account_tax_view.xml',
        'views/external_layout_template.xml',
        'views/report_invoice_template.xml',
        'views/res_country_view.xml',
        ]
}