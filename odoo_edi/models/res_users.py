from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    flexedi_notification_subscription_ids = fields.One2many('flexedi.notification.subscription', 'user_id')