from odoo import models, fields

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    tax_country_id = fields.Many2one('res.country')