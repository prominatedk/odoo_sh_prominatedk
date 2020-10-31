from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    integration_auth_token = fields.Char()
    integration_api_url = fields.Char()
    integration_analytic_account_id = fields.Many2one("account.analytic.account")
    placeholder_partner_id = fields.Many2one('res.partner')