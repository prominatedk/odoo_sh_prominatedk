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
            'document_format_id': self.env.ref('odoo_edi_stock_wms_zinc.flexedi_document_format_zinc_wms_order').id
        })

        partner_invoice_id_is_placeholder = False
        partner_shipping_id_is_placeholder = True
        shipping_not_found = False

        # Validate the existence of all data
        partner_id = self.env['res.partner'].search([('email', '=', document['contact_email'])], limit=1)
        if not partner_id.exists():
            if company.zinc_wms_auto_create_missing_partner:
                partner_id = self.env['res.partner'].create({
                    'name': document['contact_name'] or document['contact_email'],
                    'email': document['contact_email'] # Might not be entirely correct, but is needed to send invoices or other messages from Odoo
                })
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to locate customer: {}<br/>A new partner has been created and will be assigned to the sales order</p>'.format(document['contact_name']),
                })
            else:
                recieved_edi_document.write({
                    'blocking_level': 'error',
                    'error': recieved_edi_document.error or '' + '<p>Unable to locate customer: {}<br/>Sales order cannot be created</p>'.format(document['contact_name']),
                })
                recieved_edi_document.update_document_state('failed_internal')
                return False
        recieved_edi_document.write({
            'partner_id': partner_id.id
        })

        if 'billing_vat' in document:
            if document['billing_vat']:
                partner_invoice_id = self.env['res.partner'].search([('vat', '=', document['billing_vat'])], limit=1) # As per cXML specification, this should point to the actual company
                if not partner_invoice_id.exists():
                    partner_invoice_id_is_placeholder = True
                    if not company.zinc_wms_order_placeholder_contact.id:
                        partner_invoice_id = partner_id.address_get(['invoice'])['invoice']
                        recieved_edi_document.write({
                            'blocking_level': 'warning',
                            'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for partner to invoice: {}<br/>Sales order will created with ordering partners default invoice contact and recieved partner to invoice will be logged on the order</p>'.format(document['billing_name']),
                        })
                    else:
                        partner_invoice_id = company.zinc_wms_order_placeholder_contact
                        recieved_edi_document.write({
                            'blocking_level': 'warning',
                            'error': recieved_edi_document.error or '' + '<p>Unable to locate partner to invoice: {}<br/>Sales order will created with placeholder contact as invoice address</p>'.format(document['billing_name']),
                        })
            else:
                partner_invoice_id_is_placeholder = True
                if not company.zinc_wms_order_placeholder_contact.id:
                    partner_invoice_id = partner_id.address_get(['invoice'])['invoice']
                    recieved_edi_document.write({
                        'blocking_level': 'warning',
                        'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for partner to invoice: {}<br/>Sales order will created with ordering partners default invoice contact and recieved partner to invoice will be logged on the order</p>'.format(document['billing_name']),
                    })
                else:
                    partner_invoice_id = company.zinc_wms_order_placeholder_contact
                    recieved_edi_document.write({
                        'blocking_level': 'warning',
                        'error': recieved_edi_document.error or '' + '<p>Unable to locate partner to invoice: {}<br/>Sales order will created with placeholder contact as invoice address</p>'.format(document['billing_name']),
                    })
        else:
            partner_invoice_id_is_placeholder = True
            if not company.zinc_wms_order_placeholder_contact.id:
                partner_invoice_id = partner_id.address_get(['invoice'])['invoice']
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for partner to invoice: {}<br/>Sales order will created with ordering partners default invoice contact and recieved partner to invoice will be logged on the order</p>'.format(document['billing_name']),
                })
            else:
                partner_invoice_id = company.zinc_wms_order_placeholder_contact
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to locate partner to invoice: {}<br/>Sales order will created with placeholder contact as invoice address</p>'.format(document['billing_name']),
                })

        if 'delivery_vat' in document:
            if document['delivery_vat']:
                partner_shipping_id = self.env['res.partner'].search([('vat', '=', document['delivery_vat'])], limit=1)
                if not partner_shipping_id.exists():
                    partner_shipping_id_is_placeholder = True
                    if not company.zinc_wms_order_placeholder_contact.id:
                        recieved_edi_document.write({
                            'blocking_level': 'warning',
                            'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for shipping address: {}<br/>Sales order will created with ordering partners default shipping contact and recieved shipping address will be logged on the order</p>'.format(document['billing_name']),
                        })
                    else:
                        partner_shipping_id = company.zinc_wms_order_placeholder_contact
                        recieved_edi_document.write({
                            'blocking_level': 'warning',
                            'error': recieved_edi_document.error or '' + '<p>Unable to locate shipping address: {}<br/>Sales order will created with placeholder contact as shipping address</p>'.format(document['billing_name']),
                        })
            else:
                if not company.zinc_wms_order_placeholder_contact.id:
                    recieved_edi_document.write({
                        'blocking_level': 'warning',
                        'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for shipping address: {}<br/>Sales order will created with ordering partners default shipping contact and recieved shipping address will be logged on the order</p>'.format(document['billing_name']),
                    })
                else:
                    partner_shipping_id = company.zinc_wms_order_placeholder_contact
                    recieved_edi_document.write({
                        'blocking_level': 'warning',
                        'error': recieved_edi_document.error or '' + '<p>Unable to locate shipping address: {}<br/>Sales order will created with placeholder contact as shipping address</p>'.format(document['billing_name']),
                    })
        else:
            if not company.zinc_wms_order_placeholder_contact.id:
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to set placeholder for shipping address: {}<br/>Sales order will created with ordering partners default shipping contact and recieved shipping address will be logged on the order</p>'.format(document['billing_name']),
                })
            else:
                partner_shipping_id = company.zinc_wms_order_placeholder_contact
                recieved_edi_document.write({
                    'blocking_level': 'warning',
                    'error': recieved_edi_document.error or '' + '<p>Unable to locate shipping address: {}<br/>Sales order will created with placeholder contact as shipping address</p>'.format(document['billing_name']),
                })

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
            'partner_invoice_id': partner_invoice_id if type(partner_invoice_id) == int else partner_invoice_id.id,
            'partner_shipping_id': partner_shipping_id if type(partner_shipping_id) == int else partner_shipping_id.id,
            'pricelist_id': pricelist_id.id,
            'payment_term_id': partner_id.property_payment_term_id and partner_id.property_payment_term_id.id or False,
            'company_id': company.id,
            'date_order': datetime.datetime.strptime(document['order_date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None),
            'commitment_date': document['delivery_date'],
            'warehouse_id': company.zinc_wms_default_warehouse_id.id or False,
            'zinc_wms_order_number': document['supplier_order_number'] or False,
            'order_line': [(0, 0, self._get_sale_order_line_from_zinc_wms_order_line(company, line)) for line in document['lines']],
            'note': document['comment'] or ''
        })
        sale_order = self.env['sale.order'].create(sale_order_vals)

        # Set fiscal position and other values based on shipping address
        sale_order.onchange_partner_shipping_id()
        # Since there is a chance that the fiscal position has changed, we also need to recompute line taxes
        sale_order._compute_tax_id()

        sale_order.message_post(body='Sales Order was created automatically using order data recieved from EDI', message_type='notification')

        sale_order.message_post(body="""
        <p>
            Billing Information reported by EDI:<br/><br/>
            Name: {name}<br/>
            Bill To: {bill_to}<br/>
            Address: {street}<br/>
            ZIP: {zip}<br/>
            City: {city}<br/>
            State: {state}<br/>
            Country: {country}<br/>
            VAT ID: {vat_id}
        </p>
        """.format(
            name=document['billing_name'],
            bill_to=document['billing_to'] + ' ' + (document['billing_to2'] or ''),
            street=document['billing_street'],
            zip=document['billing_zip'],
            city=document['billing_city'],
            state=document['billing_state'] or '',
            country=document['billing_country_name'] + ' (' + document['billing_country_code'] + ')',
            vat_id=document['billing_vat']
        ), message_type='notification')

        sale_order.message_post(body="""
        <p>
            Delivery Information reported by EDI:<br/><br/>
            Name: {name}<br/>
            Deliver To: {deliver_to}<br/>
            Address: {street}<br/>
            ZIP: {zip}<br/>
            City: {city}<br/>
            State: {state}<br/>
            Country: {country}<br/>
            VAT ID: {vat_id}
        </p>
        """.format(
            name=document['delivery_name'],
            deliver_to=document['delivery_to'] + ' ' + (document['delivery_to2'] or ''),
            street=document['delivery_street'],
            zip=document['delivery_zip'],
            city=document['delivery_city'],
            state=document['delivery_state'] or '',
            country=document['delivery_country_name'] + ' (' + document['delivery_country_code'] + ')',
            vat_id=document['delivery_vat']
        ), message_type='notification')

        if document['comment']:
            sale_order.message_post(body="""
            <p>
                Order Notes from EDI:
                {note}
            </p>
            """.format(note=document['comment'].replace('\n', '<br/>')), message_type='notification')

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
                # Set all moves to have processed quantities matching the initial demand
                # NOTE: This will cause negative quantities if an order is confirmed from WMS before the relevant purchase is validated
                for move in picking.move_ids:
                    move.write({
                        'move_line_ids': [(0, 0, {
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'qty_done': move.product_uom_qty,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id,
                            'picking_id': picking.id
                        })]
                    })
                picking_done = picking.button_validate()
                if 'type' in picking_done:
                    # We have been given an action, which means that one or more moves are not finished
                    _logger.warning('One or more moves are not finished and therefore we cannot validate the picking {}'.format(picking.name))
                    picking.message_post(body=_('One or more moves are not finished and therefore we cannot validate the picking %s' % (picking.name,)))

        recieved_edi_document.update_document_state('processed')

        return recieved_edi_document
        