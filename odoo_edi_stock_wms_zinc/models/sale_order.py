from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    flexedi_zinc_wms_order_ids = fields.One2many('flexedi.document.wms.zinc.order', 'sale_order_id')