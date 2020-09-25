import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api
from math import ceil

MASTERDATA_API_ENDPOINT = 'primecargo/masterdata/'

class EdiMasterdata(models.TransientModel):
    _name = 'odoo_edi.primecargo.masterdata'
    _inherit = 'odoo_edi.document'

    def create_edi(self, masterdata):
        doc = self.prepare_document(masterdata)
        self.send_document(doc, masterdata, MASTERDATA_API_ENDPOINT)


    def prepare_document(self, document):
        doc = {'edi_provider': "primecargo_wms",
                'owner_code': document.company_id.primecargo_ownercode,
                'masterdataproduct_set': [self.prepare_product_document(x) for x in document.product_ids]}
        return doc

    def prepare_product_document(self, product):
        doc = {'primary_item_id': product.barcode if product.barcode else "",
                'description': product.name,
                'part_number': product.default_code if product.default_code else "",
                'use_fifo': product.categ_id.property_cost_method == 'fifo',
                'use_batchnumbers': product.tracking == 'lot',
                'use_serialnumber': product.tracking == 'serial',
                'net_weight': int(ceil(product.weight)),
                'volume': int(ceil(product.volume)),
                'masterdataproductmatrix_set': [],
                'masterdatasecondaryunit_set': []}
        return doc
