from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class FlexediDocumentWmsPicking(models.Model):
    _inherit = 'flexedi.document.wms.picking'

    def _get_endpoint_for_sending(self):
        self.ensure_one()

        zinc_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_out')
        zinc_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_in')
        picking_type_id = self.picking_id.picking_type_id

        if picking_type_id.flexedi_document_format_id.id in [zinc_picking_in_format_id.id, zinc_picking_out_format_id.id]:
            return 'zinc/orders/'
        else:
            return super()._get_endpoint_for_sending()
    
    def _get_document_endpoint(self):
        zinc_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_out')
        zinc_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_in')
        zinc_picking_status_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_status_out')
        zinc_shipment_notice = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_shipment_notice')
        picking_type_id = self.picking_id.picking_type_id

        if picking_type_id.flexedi_document_format_id.id in [zinc_picking_in_format_id.id, zinc_picking_out_format_id.id]:
            return 'zinc/orders/%s/' % (self.edi_id,)
        elif self.document_format_id.id == zinc_picking_status_format_id.id:
            return 'zinc/order-status/%s/' % (self.edi_id,)
        elif self.document_format_id.id == zinc_shipment_notice.id:
            return 'zinc-wms/shipments/%s/' % (self.edi_id,)
        else:
            return super()._get_document_endpoint()

    def generate_document(self):
        self.ensure_one()
        zinc_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_out')
        zinc_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_in')
        picking_type_id = self.picking_id.picking_type_id
        if picking_type_id.flexedi_document_format_id.id in [zinc_picking_in_format_id.id, zinc_picking_out_format_id.id]:
            return self._generate_zinc_document()
        elif self.document_format_id.id == self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_status_out').id:
            return self._generate_zinc_status_update_document()
        else:
            return super().generate_document()

    def _generate_zinc_document(self):
        self.ensure_one()
        doc = {
            'edi_provider': 'zinc_wms',
            'status': 'pending',
            'origin_identity': self.company_id.zinc_wms_origin_identity,
            'recipient_identity': 'prominate-hub', # TODO: Currently hardcoded, but if cXML spec is to be followed, this identification should be configurable
            'sender_identity': self.company_id.zinc_wms_origin_identity,
            'direction': 'out',
            'document_secret': self.company_id.zinc_wms_document_key,
            'order_total': None, # TODO: Get order total from origin document, such as PO or SO
            'order_currency': None, # TODO: Get order currency from origin document, such as PO or SO
            'order_date': None, # TODO: Get order date from origin document, such as PO or SO
            'delivery_date': self.picking_id.scheduled_date,
            'buyer_order_number': self.picking_id.origin,
            'delivery_name': self.partner_id.display_name,
            'delivery_to': self.partner_id.name if not self.partner_id.parent_id else self.partner_id.commercial_partner_id.name,
            'delivery_to2': self.partner_id.name if self.partner_id.parent_id else '',
            'delivery_street': self.partner_id.street,
            'delivery_city': self.partner_id.city,
            'delivery_state': self.partner_id.state_id.name if self.partner_id.state_id else '',
            'delivery_zip': self.partner_id.zip,
            'delivery_country_code': self.partner_id.country_id.code,
            'delivery_conutry_name': self.partner_id.country_id.name,
            'lines': [
                {
                    'name': line.name,
                    'supplier_part_number': line.product_id.default_code,
                    'buyer_part_number': line.product_id.default_code,
                    'unit_price': line.product_id.lst_price, # NOTE: Technically not the correct price, but it requires a bit more work to get the actual unit price from the origin document
                    'quantity': line.product_uom_qty,
                    'unit_code': line.product_uom.edi_product_uom_id.name
                } for line in self.picking_id.move_ids
            ]
        }

        doc.update(self._generate_zinc_billing_contact())

        return doc

    def _generate_zinc_billing_contact(self):
        origin = self.env['sale.order'].search([('name', '=', self.picking_id.origin)], limit=1)
        # TODO: Implement logic to properly handle cases where the origin is PO and not an SO. This still needs to be supported on the WMS side, which it is not as of december 2021
        if not origin.exists():
            return {}
        res = {
            'billing_name': origin.partner_invoice_id.display_name,
            'billing_to': origin.partner_invoice_id.name if not origin.partner_invoice_id.parent_id else origin.partner_invoice_id.commercial_partner_id.name,
            'billing_to2': origin.partner_invoice_id.name if origin.partner_invoice_id.parent_id else '',
            'billing_street': origin.partner_invoice_id.street,
            'billing_city': origin.partner_invoice_id.city,
            'billing_state': origin.partner_invoice_id.state_id.name if origin.partner_invoice_id.state_id else '',
            'billing_zip': origin.partner_invoice_id.zip,
            'billing_country_code': origin.partner_invoice_id.country_id.code,
            'billing_conutry_name': origin.partner_invoice_id.country_id.name,
        }

        return res

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