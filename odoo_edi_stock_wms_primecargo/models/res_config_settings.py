from odoo import models, fields, api

class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    primecargo_username = fields.Char(related="company_id.primecargo_username", readonly=False)
    primecargo_password = fields.Char(related="company_id.primecargo_password", readonly=False)
    primecargo_ownercode = fields.Char(related="company_id.primecargo_ownercode", readonly=False)
    primecargo_template_code = fields.Char(related="company_id.primecargo_template_code", readonly=False)
    primecargo_shipping_product_id = fields.Many2one('product.primecargo.shipping', related="company_id.primecargo_shipping_product_id", readonly=False, string="PrimeCargo Shipping Product", help="Contains the PrimeCargo Shipping Product Code as per agreement with PrimeCargo for this delivery")

    