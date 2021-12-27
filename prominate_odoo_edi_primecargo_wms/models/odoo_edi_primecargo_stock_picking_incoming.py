from odoo import models, fields, api, _

class OdooEdiPrimeCargoStockPickingIncoming(models.TransientModel):
    _inherit = 'odoo_edi.primecargo.stock.picking.incoming'

    def prepare_document_lines(self, line):
        prep_line = super(OdooEdiPrimeCargoStockPickingIncoming, self).prepare_document_lines(line)
        prep_line['variant_area2'] = line.product_id.product_tmpl_id.primecargo_outer_pack_qty
        prep_line['variant_area1'] = line.product_id.product_tmpl_id.primecargo_inner_pack_qty
        prep_line['use_fifo'] = False
        return prep_line
