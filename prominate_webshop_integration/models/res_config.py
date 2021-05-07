from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    integration_auth_token = fields.Char(string="Authorization", related="company_id.integration_auth_token", readonly=False)
    integration_api_url = fields.Char(string="URL", related="company_id.integration_api_url", readonly=False)
    integration_analytic_account_id = fields.Many2one("account.analytic.account", related="company_id.integration_analytic_account_id", readonly=False)
    placeholder_partner_id = fields.Many2one('res.partner', related="company_id.placeholder_partner_id", readonly=False)
    integration_in_production = fields.Boolean(related="company_id.integration_in_production", readonly=False)