# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OdooEdiEndpoint(models.Model):
    _name = 'odoo_edi.endpoint'
    _description = 'Odoo EDI Endpoint Definition'

    name = fields.Char(string="Endpoint Id")
    description = fields.Char(string="Endpoint name")
    edi_provider = fields.Selection(string='EDI Network Provider', selection=[
        ('nemhandel', 'NemHandel'),
        ('vans', 'VANS')
    ])
