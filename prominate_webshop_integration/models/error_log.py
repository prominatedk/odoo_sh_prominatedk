from odoo import models, fields, api, _


class IntegrationErrorLog(models.Model):
    _name = 'integration.error.log'
    _description = 'Error Log'
    _rec_name = 'error_date'
    _order = 'error_date'

    from_email = fields.Char()
    error_date = fields.Datetime(default=fields.Datetime.now)
    msg = fields.Text()
    action = fields.Selection([('odoo_support', 'Contact Odoo Support'),
                               ('link_support', 'Contact LINK Support'),
                               ('check_product', 'Check Product Data')])
