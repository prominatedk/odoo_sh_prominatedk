from odoo import models, fields, api, _
from math import ceil

class FlexediDocumentWmsPicking(models.Model):
    _inherit = 'flexedi.document.wms.picking'

    def _get_endpoint_for_sending(self):
        if len(self) == 0:
            return super()._get_endpoint_for_sending()
        self.ensure_one()

        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        picking_type_id = self.picking_id.picking_type_id

        if picking_type_id.code == 'incoming':
            if picking_type_id.flexedi_document_format_id.id == primecargo_picking_in_format_id.id:
                return 'primecargo/purchase-orders/'
            else:
                return super()._get_endpoint_for_sending()
        elif picking_type_id.code == 'outgoing':
            if picking_type_id.flexedi_document_format_id.id == primecargo_picking_out_format_id.id:
                return 'primecargo/sales-orders/'
            else:
                return super()._get_endpoint_for_sending()
        else:
            return super()._get_endpoint_for_sending()
    
    def _get_document_endpoint(self):
        self.ensure_one()
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        picking_type_id = self.picking_id.picking_type_id

        if picking_type_id.code == 'incoming':
            if picking_type_id.flexedi_document_format_id.id == primecargo_picking_in_format_id.id:
                return 'primecargo/purchase-order-exports/%s/' % (self.edi_id,)
            else:
                return super()._get_document_endpoint()
        elif picking_type_id.code == 'outgoing':
            if picking_type_id.flexedi_document_format_id.id == primecargo_picking_out_format_id.id:
                return 'primecargo/sales-order-exports/%s/' % (self.edi_id,)
            else:
                return super()._get_document_endpoint()
        else:
            return super()._get_document_endpoint()

    def generate_document(self):
        self.ensure_one()
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        picking_type_id = self.picking_id.picking_type_id
        if picking_type_id.flexedi_document_format_id.id in [primecargo_picking_in_format_id.id, primecargo_picking_out_format_id.id]:
            return self._generate_primecargo_document()
        else:
            return super().generate_document()

    def _generate_primecargo_document(self):
        self.ensure_one()
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        doc = {
            'edi_provider': 'primecargo_wms',
            'order_id': self.picking_id.name,
            'owner_code': self.company_id.primecargo_ownercode,
        }

        doc.update(self._generate_primecargo_dates())
        doc.update(self._generate_primecargo_order_details())
        doc.update(self._generate_primecargo_lines())

        return doc

    def _generate_primecargo_dates(self):
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        if self.docment_format_id.id == primecargo_picking_out_format_id.id:
            return {
                'shipping_date': self.picking_id.scheduled_date.strftime("%Y-%m-%d")
            }
        elif self.document_format_id.id == primecargo_picking_in_format_id:
            return {
                'delivery_date': self.picking_id.scheduled_date.strftime("%Y-%m-%d")
            }
        else:
            return {}

    def _generate_primecargo_order_details(self):
        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        if self.docment_format_id.id == primecargo_picking_out_format_id.id:
            res = {
                'order_template_code': self.company_id.primecargo_template_code,
                'order_hold_code': self.picking_id.primecargo_order_hold,
                'recipient_name': self.picking_id.partner_id.display_name if len(self.picking_id.partner_id.display_name) < 35 else self.picking_id.partner_id.commercial_partner_id.name,
                'recipient_address1': self.picking_id.partner_id.street,
                'recipient_address2': self.picking_id.partner_id.street2 or "",
                'recipient_zipcode': self.picking_id.partner_id.zip,
                'recipient_city': self.picking_id.partner_id.city,
                'recipient_country': self.picking_id.partner_id.country_id.code,
                'recipient_email': self.picking_id.partner_id.email,
                'recipient_phone': self.picking_id.partner_id.phone or self.picking_id.partner_id.mobile,
                'recipient_contact_name': self.picking_id.partner_id.name if self.picking_id.partner_id.parent_id.id else '',
                'shipping_product_code': self.picking_id.primecargo_shipping_product_id.code or self.company_id.primecargo_shipping_product_id.code,
                'customer_number': self.picking_id.partner_id.ref or self.picking_id.partner_id.id,
            }
            # If order outside of Europe, then set customs_status = 1
            europe = self.env.ref('base.europe')
            if not self.picking_id.partner_id.country_id.id in europe.country_ids.ids:
                res['customs_status'] = 1
            if self.picking_id.partner_id.state_id:
                res['recipient_state'] = self.picking_id.partner_id.state_id.code
        else:
            return {}

    def _generate_primecargo_lines(self):
        res = {}
        lines = []

        primecargo_picking_out_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_out')
        primecargo_picking_in_format_id = self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_picking_in')
        if self.docment_format_id.id == primecargo_picking_out_format_id.id:
            res.update({
                'salesorderline_set': [self._generate_primecargo_sale_line(line) for line in self.picking_id.move_ids_without_package]
            })
        elif self.document_format_id.id == primecargo_picking_in_format_id:
            res.update({
                'purchaseorderline_set': [self._generate_primecargo_purchase_line(line) for line in self.picking_id.move_ids_without_package]
            })

        return res

    def _generate_primecargo_sale_line(self, line):
        res = {
            'barcode_no': line.product_id.barcode,
            'part_number': line.product_id.default_code,
            'quantity': line.product_uom_qty, # or quantity_done?
            'cost_price': line.sale_line_id.purchase_price,
            'cost_currency_code': self.company_id.currency_id.name,
            'sales_price': line.sale_line_id.price_unit,
            'sales_currency_code': line.sale_line_id.order_id.currency_id.name,
            'description': line.product_id.display_name,
            'use_fifo': line.product_id.categ_id.property_cost_method == 'fifo',
            'property_currency_code': line.sale_line_id.order_id.currency_id.name,
            'saleorderlinecustomsinformation_set': [
                {
                    'customs_uom_code': line.product_id.uom_id.edi_product_uom_id.name,
                    'customs_origin_country': line.product_id.company_id.country_id.iso_code or self.env.user.company_id.country_id.iso_code,
                    'net_weight': ceil(line.weight),
                    'gross_weight': ceil(line.weight),
                }
            ],
        }
        if line.product_id.tracking == 'lot':
            res['batch_number'] = line.move_line_ids[0].lot_name

        return res

    def _generate_primecargo_purchase_line(self, line):
        res = {
            'barcode_no': line.product_id.barcode,
            'part_number': line.product_id.default_code,
            'quantity': line.product_uom_qty, # or quantity_done?
            'description': line.product_id.display_name,
            'use_fifo': line.product_id.categ_id.property_cost_method == 'fifo',
            'property_currency_code': line.purchase_line_id.order_id.currency_id.name or line.picking_id.partner_id.property_product_pricelist.currency_id.name,
            'purchaseorderlinepackagingnote_set': [],
        }
        if line.product_id.tracking == 'lot':
            res['batch_number'] = line.move_line_ids[0].lot_name
        if line.product_id.product_tmpl_id.primecargo_customs_description:
            res['shipping_product_category'] = line.product_id.product_tmpl_id.primecargo_customs_description

        return res