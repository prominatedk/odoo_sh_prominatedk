# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OdooEdiProductUom(models.Model):
    _name = 'odoo_edi.product.uom'
    _description = 'EDI standard Unit of measure name'

    name = fields.Char(string="EDI unit name")
    description = fields.Char(string="EDI unit description")
