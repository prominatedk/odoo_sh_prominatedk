# -*- encoding: utf-8 -*-
{
    'name': 'EDI - Electronic Document Interchange Odoo 12',
    'category': 'Accounting & Finance',
    'version': '1.5',
    'depends': ['base','sale_management','stock','purchase'],
    'description': """EDI Module with support for EDIFACT, X12, TRADACOM and other EDI formats.
    EDI Conversion is done by easyEDI as a hosted service. Connection to all VANs.
    Added EDI fields list(2.0)).
    """,
    'data': [
            'security/ir.model.access.csv',
            'data/cronjobs.xml',
            'views/edi.xml',
            'views/partner.xml',
            'views/saleorder.xml',
            'views/picking.xml',
            'views/invoice.xml',
            'views/purchaseorder.xml'
    ],
    'demo': [
    ],
    'external_dependencies' : {
        # 'python' : ['suds-jurko'],
    },

    'installable': True,
    'auto_install': True,
}
