from odoo import models, fields

class OdooEdiTaxScheme(models.Model):
    _name = 'odoo_edi.tax.scheme'
    _description = 'OIOUBL Tax Scheme for EDI'
    _rec_name = 'name'

    code = fields.Char(required=True)
    name = fields.Char(required=True)
