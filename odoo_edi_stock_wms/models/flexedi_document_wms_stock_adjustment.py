from odoo import models, fields, api, _

class FlexediDocumentWmsStockAdjustment(models.Model):
    _inherit = 'flexedi.document'
    _name = 'flexedi.document.wms.stock.adjustment'
    _description = 'Inventory Adjustment (FlexEDI)'

    product_id = fields.Many2one('product.product')
