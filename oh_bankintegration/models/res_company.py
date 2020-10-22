# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    # TODO check all the options/fields are in the views (settings + company
    # form view)
    payment_journal = fields.Many2one(
        'account.journal', string='Payment journal', domain="[('type', '=', 'bank')]")
