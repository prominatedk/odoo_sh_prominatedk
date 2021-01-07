# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    audited = fields.Boolean(string='Audited (Yes/No)')
