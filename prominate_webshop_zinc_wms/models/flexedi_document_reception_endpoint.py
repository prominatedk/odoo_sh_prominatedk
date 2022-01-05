import datetime
from odoo import models, fields, api, _
import json
import logging
_logger = logging.getLogger(__name__)

class FlexediDocumentReceptionEndpoint(models.Model):
    _inherit = 'flexedi.document.reception.endpoint'

    def _get_sale_order_line_from_zinc_wms_order_line(self, company, line):
        res = super()._get_sale_order_line_from_zinc_wms_order_line(company, line)

        product = self.env['product.product'].search([('default_code', 'in', [line['buyer_part_number'], line['supplier_part_number']])], limit=1)

        if not product._convert_from_warehouse_pack(res['product_uom_qty']) == res['product_uom_qty']:
            res.update({
                'product_uom_qty': product._convert_from_warehouse_pack(res['product_uom_qty']),
                'price_unit': line['unit_price'] / product.product_tmpl_id.warehouse_inner_pack_qty,
            })
        
        return res