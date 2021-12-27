from odoo import models, fields, api, _

class OdooEdiPrimeCargoMasterdata(models.TransientModel):
    _inherit = 'odoo_edi.primecargo.masterdata'

    def prepare_product_document(self, product):
        doc = super(OdooEdiPrimeCargoMasterdata, self).prepare_product_document(product)
        doc['variant_area2'] = product.product_tmpl_id.primecargo_outer_pack_qty
        doc['variant_area1'] = product.product_tmpl_id.primecargo_inner_pack_qty
        doc['can_be_returned'] = True
        doc['use_fifo'] = False
        return doc
