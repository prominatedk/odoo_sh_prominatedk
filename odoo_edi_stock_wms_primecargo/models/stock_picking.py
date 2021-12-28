from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    primecargo_shipping_product_id = fields.Many2one('product.primecargo.shipping', string="PrimeCargo Shipping Product", help="Contains the PrimeCargo Shipping Product Code as per agreement with PrimeCargo for this delivery")
    primecargo_order_hold = fields.Boolean(string='Hold Order at PrimeCargo', help='Check this if the order should not be shipped immediately, but requires manual handling at PrimeCargo')

    def _queue_for_flexedi_wms(self):
        self.ensure_one()
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        if self.picking_type_id.flexedi_document_format_id.id in [primecargo_picking_in_format_id.id, primecargo_picking_out_format_id.id]:
            if self.flexedi_wms_picking_status in ['pending', 'sent', 'validated']:
                raise UserError(_('The picking %s has already been sent to PrimeCargo and can therefore not be sent again as it would create an additional order and ship the order twice' % (self.display_name,)))
        super()._queue_for_flexedi_wms()
        