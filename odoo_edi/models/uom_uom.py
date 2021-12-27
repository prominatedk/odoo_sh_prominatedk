# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductUom(models.Model):
    _inherit = 'uom.uom'
    edi_product_uom_id = fields.Many2one('odoo_edi.product.uom', string="EDI Unit", help="The generic EDI unit used for correctly handling EDI invoicing", oldname='edi_name')

