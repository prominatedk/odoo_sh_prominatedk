from odoo import models, fields, api, _
from math import ceil

class FlexediDocumentWmsProduct(models.Model):
    _inherit = 'flexedi.document.wms.product'

    def _get_endpoint_for_sending(self):
        if len(self) == 0:
            return super()._get_endpoint_for_sending()
        if self.document_format_id.id == self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_product').id:
            return 'primecargo/masterdata/'
        else:
            return super()._get_endpoint_for_sending()
    
    def generate_document(self):
        self.ensure_one()
        if self.document_format_id.id == self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_product').id:
            return self._generate_primecargo_document()
        else:
            return super().generate_document()

    def _generate_primecargo_document(self):
        res = {
            'edi_provider': 'primecargo_wms',
            'description': self.product_id.name,
            'part_number': self.product_id.default or '',
            'use_fifo': self.product_id.categ_id.property_cost_method == 'fifo',
            'use_batchnumbers': self.product_id.tracking == 'lot',
            'use_serialnumbers': self.product_id.tracking == 'serial',
            'net_weight': int(ceil(self.product_id.weight)),
            'volume': int(ceil(self.product_id.volume)),
            'masterdataproductmatrix_set': [],
            'masterdatasecondaryunit_set': [],
        }

        if self.product_id.product_tmpl_id.primecargo_customs_description:
            res['shipping_product_category'] = self.product_id.product_tmpl_id.primecargo_customs_description

        return res