from odoo import models, fields

class ResCountry(models.Model):
    _inherit = 'res.country'
    
    vat_number = fields.Char()