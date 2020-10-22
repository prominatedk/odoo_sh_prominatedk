from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    primecargo_username = fields.Char()
    primecargo_password = fields.Char()
    primecargo_ownercode = fields.Char()
    primecargo_template_code = fields.Char()
    primecargo_shipping_code = fields.Char()
    primecargo_autovalidate_done = fields.Boolean(string='Automatically validate pickings from PrimeCargo', help='Checking this will automatically validate any pickings recieving data from PrimeCargo,\nif all moves are fully processed.\nIf one or more moves trigger a confirmation dialog or a backorder, nothing is validated')
    