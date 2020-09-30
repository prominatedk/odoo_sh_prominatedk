from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    primecargo_username = fields.Char()
    primecargo_password = fields.Char()
    primecargo_ownercode = fields.Char()
    primecargo_template_code = fields.Char()
    primecargo_shipping_code = fields.Char()
    