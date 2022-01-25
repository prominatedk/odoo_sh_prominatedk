{
    'name': "Country Vat Number",
    'summary': 'Vat no. per country',
    'version': '1.0.0',
    'author': 'VK Data ApS',
    'category': 'Accounting',
    'description':'This module allows you to set a company vat no. for each country.',
    'website': 'https://vkdata.dk',
    'depends': ['account'],

    'data': [
        'account_tax_view.xml',
        'external_layout_template.xml',
        'report_invoice_template.xml',
        'res_country_view.xml',
        ]
}