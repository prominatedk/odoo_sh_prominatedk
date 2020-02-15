# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from datetime import datetime


class ConversionList(models.Model):
    _name = 'bankintegration.conversion_list'
    _model = "oh_bankintegration.conversion_list"
    _description = "Bank Integration Conversion List"

    active = fields.Boolean(string='Active')
    from_text = fields.Char(string='From', required=True)
    to_text = fields.Char(string='To', required=True)
    origin = fields.Char(string='Origin')
