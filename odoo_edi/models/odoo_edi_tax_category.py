from odoo import models, fields

class OdooEdiTaxCategory(models.Model):
    _name = 'odoo_edi.tax.category'
    _description = 'OIOUBL Tax Category for EDI'
    _rec_name = 'name'

    code = fields.Char(required=True)
    name = fields.Char(required=True)