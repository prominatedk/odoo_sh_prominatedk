from odoo import models, fields, api, _

class FlexediDocumentWmsZincOrder(models.Model):
    _inherit = 'flexedi.document.wms.zinc.order'

    def _document_post_reception_hook(self, document):
        super()._document_post_reception_hook(document)
        if 'shipping_cost' in document:
            if not 'shipping_carrier_sku' in document and document['shipping_carrier_sku']:
                shipping_note = 'Shipping services cannot be added to the order as there is no defintion of what shipping provider was used. Below is the information that was recieved through EDI:<br/><br/>'
                if 'shipping_carrier_scac' in document:
                    shipping_note += 'SCAC Code: {}<br/>'.format(document['shipping_carrier_scac'])
                if 'shipping_carrier_method' in document:
                    shipping_note += 'Carrier Shipment Method: {}<br/>'.format(document['shipping_carrier_method'])
                if 'shipping_cost' in document:
                    shipping_note += 'Shipping Cost: {}<br/>'.format(document['shipping_cost'])
                if 'shipping_method_name' in document:
                    shipping_note += 'Shipment Method Name: {}<br/>'.format(document['shipping_method_name'])
                self.sale_order_id.message_post(message_type='notification', body=shipping_note)
            else:
                shipping_product = self.env['product.product'].search([('webshop_shipping_code', '=', document['shipping_carrier_sku'])], limit=1)
                if not shipping_product.exists():
                    shipping_note = 'Shipping services cannot be added to the order as no product exists in Odoo that matches the provided shipping code. Below is the information that was recieved through EDI:<br/><br/>'
                    if 'shipping_carrier_scac' in document:
                        shipping_note += 'SCAC Code: {}<br/>'.format(document['shipping_carrier_scac'])
                    if 'shipping_carrier_method' in document:
                        shipping_note += 'Carrier Shipment Method: {}<br/>'.format(document['shipping_carrier_method'])
                    if 'shipping_cost' in document:
                        shipping_note += 'Shipping Cost: {}<br/>'.format(document['shipping_cost'])
                    if 'shipping_method_name' in document:
                        shipping_note += 'Shipment Method Name: {}<br/>'.format(document['shipping_method_name'])
                    if 'shipping_carrier_sku' in document:
                        shipping_note += 'Shipping SKU: {}<br/>'.format(document['shipping_carrier_sku'])
                    self.sale_order_id.message_post(message_type='notification', body=shipping_note)
                else:
                    line = self.env['sale.order.line'].default_get([])
                    line.update({
                        'product_id': shipping_product.id,
                        'product_uom_qty': 1,
                        'product_uom': shipping_product.uom_id.id,
                        'price_unit': document['shipping_cost']
                    })
                    self.sale_order_id.write({
                        'order_line': [(0, 0, line)]
                    })