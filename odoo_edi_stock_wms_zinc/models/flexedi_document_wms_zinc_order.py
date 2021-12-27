from odoo import models, fields, api, _

class FlexediDocumentWmsZincOrder(models.Model):
    _inherit = 'flexedi.document'
    _name = 'flexedi.document.wms.zinc.order'
    _description = 'Zinc WMS Order Request (FlexEDI)'

    sale_order_id = fields.Many2one('sale.order')
    purchase_order_id = fields.Many2one('purchase.order')

    def _get_endpoint_for_sending(self):
        if self.document_format_id.id == self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_order_status').id:
            return 'zinc-wms/order-status/'
        else:
            return 'zinc-wms/orders/'

    def _get_document_endpoint(self):
        return 'zinc-wms/orders/%s/' % (self.edi_id,)

    def generate_document(self):
        if self.document_format_id.id == self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_order_status').id:
            return self._generate_zinc_status_update_document()
        else:
            return super().generate_document()

    def _generate_zinc_status_update_document(self):
        return {
            'edi_provider': 'zinc_wms',
            'status': self.state,
            'origin_identity': self.company_id.zinc_wms_origin_identity,
            'recipient_identity': 'prominate-hub', # TODO: Currently hardcoded, but if cXML spec is to be followed, this identification should be configurable
            'sender_identity': self.company_id.zinc_wms_origin_identity,
            'direction': 'out',
            'document_secret': self.company_id.zinc_wms_document_key,
            'order': self.origin_document_edi_id,
        }