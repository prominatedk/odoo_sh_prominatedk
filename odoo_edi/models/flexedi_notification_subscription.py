from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FlexediNotificationSubscription(models.Model):
    _name = 'flexedi.notification.subscription'

    company_id = fields.Many2one('res.company', required=True)
    user_id = fields.Many2one('res.users', required=True)
    # The model_id field allows custom noticiation settings, so that a user is only notified for the given mode
    # If no model is set, then the user is notified for all FlexEDI documents as per the selected subscription type
    model_id = fields.Many2one('ir.model', domain=[('model', 'ilike', 'flexedi.document.%')])
    subscription_type = fields.Selection(selection=[
        ('none', 'Nothing'),
        ('all', 'Everything'),
        ('error', 'Errors'),
        ('warning', 'Warnings'),
        ('info', 'Informational messages only')
    ], default='error', required=True)