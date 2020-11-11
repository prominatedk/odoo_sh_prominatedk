from odoo import models, fields, api, _

class ProductPrimecargoShipping(models.Model):
    _inherit = 'product.primecargo.shipping'

    webshop_carrier_code = fields.Char(string='Webshop Carrier Code', help='The code passed to the external webshop for informing which shipping provider was used')

