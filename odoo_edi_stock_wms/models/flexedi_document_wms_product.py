from odoo import models, fields, api, _

class FlexediDocumentWmsProduct(models.Model):
    _inherit = 'flexedi.document'
    _name = 'flexedi.document.wms.product'
    _description = 'Product (FlexEDI)'

    product_id = fields.Many2one('product.product')

    def _get_status_endpoint(self):
        return 'wms/products/pending/'

    def _get_endpoint_for_sending(self):
        return 'wms/products/'

    def source_document_object(self):
        self.ensure_one()
        return self.product_id

    def generate_document(self):
        pass