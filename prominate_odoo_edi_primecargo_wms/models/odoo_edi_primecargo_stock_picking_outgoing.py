from odoo import models, fields, api, _

class OdooEdiPrimeCargoStockPickingOutgoing(models.TransientModel):
    _inherit = 'odoo_edi.primecargo.stock.picking.outgoing'

    def prepare_document_lines(self, line):
        prep_line = super(OdooEdiPrimeCargoStockPickingOutgoing, self).prepare_document_lines(line)
        prep_line['variant_area2'] = line.product_id.product_tmpl_id.primecargo_outer_pack_qty
        prep_line['variant_area1'] = line.product_id.product_tmpl_id.primecargo_inner_pack_qty
        return prep_line