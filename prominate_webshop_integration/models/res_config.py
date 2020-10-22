from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    integration_auth_token = fields.Char(string="Authorization", related="company_id.integration_auth_token", readonly=False)
    integration_api_url = fields.Char(string="URL", related="company_id.integration_api_url", readonly=False)
    integration_analytic_account_id = fields.Many2one("account.analytic.account", related="company_id.integration_analytic_account_id", readonly=False)
    webshop_shipping_product_id = fields.Many2one('product.product', related="company_id.webshop_shipping_product_id", readonly=False)
