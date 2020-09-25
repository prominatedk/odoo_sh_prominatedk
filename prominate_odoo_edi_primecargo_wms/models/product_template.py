from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    primecargo_outer_pack_qty = fields.Integer(string='Quantity in outside pack (PrimeCargo)')
    primecargo_inner_pack_qty = fields.Integer(string='Quantity in inside pack (PrimeCargo)')