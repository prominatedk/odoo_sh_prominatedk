from odoo import models, fields, api

class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    primecargo_username = fields.Char(related="company_id.primecargo_username", readonly=False)
    primecargo_password = fields.Char(related="company_id.primecargo_password", readonly=False)
    primecargo_ownercode = fields.Char(related="company_id.primecargo_ownercode", readonly=False)
    primecargo_template_code = fields.Char(related="company_id.primecargo_template_code", readonly=False)
    primecargo_shipping_code = fields.Char(related="company_id.primecargo_shipping_code", readonly=False)
    