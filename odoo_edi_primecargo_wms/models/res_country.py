from odoo import models, fields

class ResCountry(models.Model):
    _inherit = 'res.country'

    iso_code = fields.Char()
    