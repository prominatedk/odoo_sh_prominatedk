import datetime
from odoo import models, fields, api, _
import json
import logging
_logger = logging.getLogger(__name__)

class FlexediDocumentReceptionEndpoint(models.Model):
    _inherit = 'flexedi.document.reception.endpoint'

    def _recieve_zinc_wms_warehouse_orders_document(self, company, document):
        # Recieve a given cXML OrderRequest from Zinc Germany WMS
        recieved_edi_document = self.env['flexedi.document.wms.zinc.order'].create({
            'edi_id': document['pk'],
            'edi_uuid': document['uuid'],
            'state': 'recieved', # It is important to explicitly set the state as it might otherwise be handled as something that we should send
            'company_id': company.id,
            'response_data': json.dumps(document, sort_keys=True, indent=4),
            'document_format_id': self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_picking_out').id
        })

        # Validate the existence of all data
        partner_id = self.env['res.partner'].search([('name', '=', document['contact_email'])], limit=1)
        if not partner_id.exists():
            partner_id = self.env['res.partner'].search([('name', '=', document['delivery_name'])], limit=1) # As per cXML specification, this should point to the actual company
            if not partner_id.exists():
                # If the partner does not exist, we will try to search again using a different field
                partner_id = self.env['res.partner'].search([('name', '=', document['delivery_to'])], limit=1)
                if partner_id.exists():
                    # We found something. Now we need to check the second line to see if we can somehow identify a specific contact
                    contact_id = self.env['res.partner'].search([('commercial_partner_id', '=', partner_id.id), ('name', '=', document['delivery_to2'])], limit=1)
                    if contact_id.exists():
                        partner_id = contact_id
                elif company.zinc_wms_auto_create_missing_partner:
                    partner_id = self.env['res.partner'].create({
                        'name': document['delivery_name'],
                        'street': document['delivery_street'],
                        'zip': document['delivery_zip'],
                        'city': document['delivery_city'],
                        'country_id': self.env['res.country'].search([('code', '=', document['delivery_country_code'])], limit=1).id,
                        'email': document['contact_email'] # Might not be entirely correct, but is needed to send invoices or other messages from Odoo
                    })
                    recieved_edi_document.write({
                        'blocking_level': 'warning',
                        'error': recieved_edi_document.error or '' + '<p>Unable to locate customer: {}<br/>A new partner has been created and will be assigned to the sales order</p>'.format(document['delivery_name']),
                    })
                else:
                    recieved_edi_document.write({
                        'blocking_level': 'error',
                        'error': recieved_edi_document.error or '' + '<p>Unable to locate customer: {}<br/>Sales order cannot be created</p>'.format(document['delivery_name']),
                    })
                    recieved_edi_document.update_document_state('failed_internal')
                    return False
        recieved_edi_document.write({
            'partner_id': partner_id.id
        })

        partner_invoice_id = self.env['res.partner'].search([('name', '=', document['billing_name'])], limit=1) # As per cXML specification, this should point to the actual company
        if not partner_invoice_id.exists():
            # If the partner does not exist, we will try to search again using a different field
            partner_invoice_id = self.env['res.partner'].search([('name', '=', document['billing_to'])], limit=1)
            if partner_invoice_id.exists():
                # We found something. Now we need to check the second line to see if we can somehow identify a specific contact
                contact_id = self.env['res.partner'].search([('commercial_partner_id', '=', partner_invoice_id.id), ('name', '=', document['billing_to2'])], limit=1)
                if contact_id.exists():
                    partner_invoice_id = contact_id
            else:
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to locate partner to invoice: {}<br/>Sales order will created with default invoice address of the ordering partner</p>'.format(document['billing_name']),
                })
                partner_invoice_id = partner_id.address_get(['invoice'])['invoice']

        line_errors = []
        for line in document['lines']:
            product_id = self.env['product.product'].search([('default_code', '=', line['buyer_part_number'])], limit=1)
            if not product_id.exists():
                product_id = self.env['product.product'].search([('default_code', '=', line['supplier_part_number'])], limit=1)
                if not product_id.exists():
                    line_errors.append(line['buyer_part_number'] or line['supplier_part_number'])
        if line_errors:
            message = ''
            for line in line_errors:
                message += '<li>A product with internal reference {} does not exist</li>'.format(line)
            message = '<ul>' + message + '</ul>'
            recieved_edi_document.write({
                'blocking_level': 'error',
                'error': recieved_edi_document.error or '' + message
            })
            recieved_edi_document.update_document_state('failed_internal')
            return False

        currency_id = self.env['res.currency'].search([('name', '=', document['order_currency'])], limit=1)
        if not currency_id.exists():
            recieved_edi_document.write({
                'blocking_level': 'error',
                'error': recieved_edi_document.error or '' + '<p>The order cannot be created as the currency {} does not exist</p>'.format(document['order_currency']),
            })
            recieved_edi_document.update_document_state('failed_internal')
            return False
        pricelist_id = self.env['product.pricelist'].search([('currency_id', '=', currency_id.id)], limit=1) if not partner_id.property_product_pricelist.currency_id.id == currency_id.id else partner_id.property_product_pricelist
        if not pricelist_id.exists():
            recieved_edi_document.write({
                'blocking_level': 'error',
                'error': recieved_edi_document.error or '' + '<p>The order cannot be created as the currency {} is not assigned to any pricelist in Odoo</p>'.format(document['order_currency']),
            })
            recieved_edi_document.update_document_state('failed_internal')
            return False

        # Create a new sale.order record
        sale_order_vals = self.env['sale.order'].default_get([])
        sale_order_vals.update({
            'partner_id': partner_id.id,
            'partner_invoice_id': partner_invoice_id.id,
            'pricelist_id': pricelist_id.id,
            'company_id': company.id,
            'date_order': datetime.datetime.strptime(document['order_date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None),
            'commitment_date': document['delivery_date'],
            'order_line': [(0, 0, self._get_sale_order_line_from_zinc_wms_order_line(company, line)) for line in document['lines']]
        })
        sale_order = self.env['sale.order'].create(sale_order_vals)

        # Confirm the sale order
        sale_order.action_confirm()

        # Update EDI document status
        recieved_edi_document.write({
            'sale_order_id': sale_order.id,
        })
        recieved_edi_document._update_document(recieved_edi_document._get_document_endpoint(), {
            'state': 'processed',
            'buyer_order_number': sale_order.name
        })

        # Create new StatusUpdateRequest
        status_update = self.env['flexedi.document.wms.zinc.order'].create({
            'company_id': company.id,
            'partner_id': partner_id.id,
            'state': 'sent',
            'sale_order_id': sale_order.id,
            'origin_document_edi_id': recieved_edi_document.edi_id,
            'document_format_id': self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_order_status').id
        })

        # Queue StatusUpdateRequest for sending
        status_update.send_document()
        # Manual requeue of the document as status updates are not automatically sent
        if status_update.edi_id:
            status_update._requeue_document()

        recieved_edi_document.update_document_state('processed')

        return recieved_edi_document


    def _get_sale_order_line_from_zinc_wms_order_line(self, company, line):
        res = self.env['sale.order.line'].default_get([])

        product = self.env['product.product'].search([('default_code', 'in', [line['buyer_part_number'], line['supplier_part_number']])], limit=1)

        res.update({
            'product_id': product.id,
            'product_uom_qty': line['quantity'],
            'product_uom': company.get_uom_from_edi_unit(line['unit_code'], product.uom_id.category_id.id).id,
            'price_unit': line['unit_price'],
        })
        return res

    def _recieve_zinc_wms_shipment_notice_document(self, company, document):
        recieved_edi_document = self.env['flexedi.document.wms.picking'].create({
            'edi_id': document['pk'],
            'edi_uuid': document['uuid'],
            'state': 'recieved', # It is important to explicitly set the state as it might otherwise be handled as something that we should send
            'company_id': company.id,
            'response_data': json.dumps(document, sort_keys=True, indent=4),
            'origin_document_edi_id': document['order'],
            'document_format_id': self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_shipment_notice').id
        })

        edi_sale_order = self.env['flexedi.document.wms.zinc.order'].search([('edi_id', '=', recieved_edi_document.origin_document_edi_id)], limit=1)
        if not edi_sale_order.exists():
            recieved_edi_document.write({
                'blocking_level': 'error',
                'error': recieved_edi_document.error or '' + '<p>Unable to locate origin sale order in Odoo</p>'
            })
            recieved_edi_document.update_document_state('failed_internal')
            return False
        sale_order = edi_sale_order.sale_order_id

        ready_states = ['confirmed', 'assigned']
        allowed_states = ready_states + ['waiting']
        
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id), ('state', 'in', allowed_states)], limit=1)
        if not picking.exists():
            recieved_edi_document.write({
                'blocking_level': 'error',
                'error': recieved_edi_document.error or '' + '<p>Unable to locate an active picking operation for sales order {}</p>'.format(sale_order.name)
            })
            recieved_edi_document.update_document_state('failed_internal')
            return False
        recieved_edi_document.write({
            'picking_id': picking.id,
            'partner_id': picking.partner_id.id
        })
        picking.message_post(type='notification', body=_('Order has been confirmed shipped with %s and tracking reference %s' % (document['shipper_name'] or document['shipper_scac_id'], document['shipment_number'])))
        picking.write({
            'carrier_tracking_ref': document['shipment_number']
        })

        if company.flexedi_wms_autovalidate_done:
            if picking.state == 'waiting':
                _logger.error('Picking is waiting')
                picking.message_post(type='notification', body=_('This picking cannot be automatically validated, since it is a waiting state, possibly due to mismatched inventory between Odoo and the WMS system'))
            elif picking.state in ready_states:
                picking_done = picking.button_validate()
                if 'type' in picking_done:
                    if 'res_model' in picking_done:
                        if picking_done['res_model'] == 'stock.immediate.transfer':
                            _logger.error(picking_done)
                    # We have been given an action, which means that one or more moves are not finished
                    _logger.warning('One or more moves are not finished and therefore we cannot validate the picking {}'.format(picking.name))
                    picking.message_post(body=_('One or more moves are not finished and therefore we cannot validate the picking %s' % (picking.name,)))

        recieved_edi_document.update_document_state('processed')

        return recieved_edi_document
        