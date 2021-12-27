from odoo import models, fields, api, _

class FlexediDocumentWmsPicking(models.Model):
    _inherit = 'flexedi.document'
    _name = 'flexedi.document.wms.picking'
    _description = 'Stock Picking (FlexEDI)'

    picking_id = fields.Many2one('stock.picking')

    def _get_status_endpoint(self):
        return 'wms/pickings/pending/'

    def _get_endpoint_for_sending(self):
        return 'wms/pickings/'

    def _get_document_endpoint(self):
        return 'wms/pickings/%s' % (self.edi_id,)

    def generate_document(self):
        pass