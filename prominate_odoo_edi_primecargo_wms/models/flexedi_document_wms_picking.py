from odoo import models, fields, api, _
from math import ceil

class FlexediDocumentWmsPicking(models.Model):
    _inherit = 'flexedi.document.wms.picking'

    def _generate_primecargo_sale_line(self, line):
        res = super()._generate_primecargo_sale_line(line)

        res['variant_area2'] = line.product_id.product_tmpl_id.primecargo_outer_pack_qty
        res['variant_area1'] = line.product_id.product_tmpl_id.primecargo_inner_pack_qty
        res['use_fifo'] = False

        return res

    def _generate_primecargo_purchase_line(self, line):
        res = super()._generate_primecargo_purchase_line(line)

        res['variant_area2'] = line.product_id.product_tmpl_id.primecargo_outer_pack_qty
        res['variant_area1'] = line.product_id.product_tmpl_id.primecargo_inner_pack_qty
        res['use_fifo'] = False

        return res