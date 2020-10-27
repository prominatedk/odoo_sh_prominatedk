from odoo import models, fields, api, _

class ProductPrimecargoShipping(models.Model):
    _name = 'product.primecargo.shipping'
    _description = 'PrimeCargo Shipping Codes/Products'

    active = fields.Boolean()
    name = fields.Char(required=True, help='Name of the shipping code. This is what you see in Odoo')
    code = fields.Char(required=True, help='The shipping code used when communicating with PrimeCargo. This value is given by PrimeCargo')

    @api.multi
    def name_get(self):
        return [(record.id, '[%s]%s' % (record.code, record.name)) for record in self]