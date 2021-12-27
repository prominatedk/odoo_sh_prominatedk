from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    primecargo_username = fields.Char()
    primecargo_password = fields.Char()
    primecargo_ownercode = fields.Char()
    primecargo_template_code = fields.Char()
    primecargo_shipping_product_id = fields.Many2one('product.primecargo.shipping', string="PrimeCargo Shipping Product", help="Contains the PrimeCargo Shipping Product Code as per agreement with PrimeCargo for this delivery")
    primecargo_autovalidate_done = fields.Boolean(string='Automatically validate pickings from PrimeCargo', help='Checking this will automatically validate any pickings recieving data from PrimeCargo,\nif all moves are fully processed.\nIf one or more moves trigger a confirmation dialog or a backorder, nothing is validated')
    