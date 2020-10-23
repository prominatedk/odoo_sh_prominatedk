import logging
import requests
import traceback

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.odoo_edi.models.edi_document import LIVE_API_ROOT, TEST_API_ROOT
from math import ceil


OUTGOING_API_ENDPOINT = 'primecargo/sales-orders/'
QUEUE_OUTGOING_API = 'primecargo/sales-order-exports/queue/'

class EdiStockPickingOutgoing(models.TransientModel):
    _name = 'odoo_edi.primecargo.stock.picking.outgoing'
    _inherit = 'odoo_edi.document'


    def create_edi(self, document):
        self._validate_move_lines(document.move_ids_without_package)
        doc = self.prepare_document(document)
        _logger.info('SEND DOC: %s', doc)
        self.send_document(doc, document, OUTGOING_API_ENDPOINT)

    def prepare_document(self, document):
        return {'edi_provider': "primecargo_wms",
                'order_id': document.name,
                'shipping_date': document.scheduled_date.strftime("%Y-%m-%d"),
                'owner_code': document.company_id.primecargo_ownercode,
                'order_template_code': document.company_id.primecargo_template_code,
                'recipient_name': document.partner_id.display_name,
                'recipient_address1': document.partner_id.street,
                'recipient_address2': document.partner_id.street2 or "",
                'recipient_zipcode': document.partner_id.zip,
                'recipient_city': document.partner_id.city,
                'recipient_country': document.partner_id.country_id.code,
                'recipient_email': document.partner_id.email,
                'recipient_phone': document.partner_id.phone or document.partner_id.mobile,
                'shipping_product_code': document.primecargo_shipping_product_code or document.company_id.primecargo_shipping_code,
                'customer_number': document.partner_id.ref or document.partner_id.id,
                'salesorderline_set': [self.prepare_document_lines(line) for line in document.move_ids_without_package]}
    
    def prepare_document_lines(self, line):
        prep_line = {'barcode_no': line.product_id.barcode,
                    'part_number': line.product_id.default_code,
                    'quantity': line.product_uom_qty, # or quantity_done?
                    'description': line.product_id.display_name,
                    'use_fifo': line.product_id.categ_id.property_cost_method == 'fifo',
                    'property_currency_code': line.sale_line_id.order_id.currency_id.name,
                    'saleorderlinecustomsinformation_set': [
                        {
                            'customs_uom_code': line.product_id.uom_id.edi_product_uom_id.name,
                            'customs_origin_country': line.product_id.company_id.country_id.iso_code,
                            'net_weight': ceil(line.weight),
                            'gross_weight': ceil(line.weight),
                        }
                    ],}
        if line.product_id.tracking == 'lot':
            prep_line['batch_number'] = line.move_line_ids[0].lot_name
        return prep_line

    def _validate_move_lines(self, lines):
        masterdata = self.env['product.primecargo.wms.masterdata'].search([]) # ('edi_document_status', '=', 'processed')
        masterdata_products = [x.product_ids for x in masterdata]
        masterdata_products = set([y for x in masterdata_products for y in x])
        if not all([line.product_id in masterdata_products for line in lines]):
            raise ValidationError(_('Error! The following products have not been created in PrimeCargo:\n{0}'.format([line.product_id.display_name for line in lines if line.product_id.id not in masterdata_products])))
        
        lot_lines = lines.filtered(lambda l: l.product_id.tracking == 'lot')
        if lot_lines and not all([l.move_line_ids[0].lot_name for l in lot_lines]):
            raise ValidationError(_('Error! Missing lot number for moves'))

    def recieve_document(self):
        for company in self.env['res.company'].search([]):
            company = self.env.user.company_id
            headers = {'Content-Type': 'application/json; charset=utf8',
                        'Authorization': 'Token {0}'.format(company.odoo_edi_token)}
            self._update_queue(company, headers)

    def _update_queue(self, company, headers):
        queue = requests.get((LIVE_API_ROOT if company.edi_mode == 'production' else TEST_API_ROOT) + QUEUE_OUTGOING_API, headers=headers)
        _logger.info(queue.text)
        if len(queue.json()) > 0:
            for data in queue.json():
                if data['order_result_message'] == "OK":
                    picking = self.env['stock.picking'].search([('edi_document_guid', '=', data['order_uuid'])])
                    picking.edi_document_id = data['order_id']
                    picking.edi_document_status = data['status']
                    picking.edi_document_status_message = data['status_message']
                    carrier_tracking_refs = []
                    for line in data['salesorderexportline_set']:
                        move = picking.move_ids_without_package.filtered(lambda l: l.product_id.barcode == line['barcode_no'] or l.product_id.default_code == line['part_number'])
                        if not move:
                            _logger.error('No stock.move found for product barcode {} or internal reference {} for order {}'.format(line['barcode_no'], line['part_number'], picking.name))
                            continue
                        if line['tracking_no']:
                            if not line['tracking_no'] in carrier_tracking_refs:
                                carrier_tracking_refs.append(line['tracking_no'])
                        line_found = False
                        if not move.product_id.tracking in ['lot', 'serial']:
                            move.write({
                                'move_line_ids': [(0,0, {
                                    'product_id': move.product_id.id,
                                    'qty_done': line['quantity_done'],
                                    'product_uom_id': move.product_uom.id,
                                    'location_id': move.picking_id.location_id.id,
                                    'location_dest_id': move.picking_id.location_dest_id.id
                                })]
                            })
                        else:
                            for ml in move.move_line_ids:
                                if ml.lot_id.name == line['batch_number']:
                                    ml.qty_done = line['quantity_done']
                                    line_found = True
                            if not line_found:
                                move.write({
                                    'move_line_ids': [(0,0, {
                                        'product_id': move.product_id.id,
                                        'product_uom_id': move.product_uom.id,
                                        'qty_done': line['quantity_done'],
                                        'lot_id': (0,0, {
                                            'name': line['batch_number']
                                        }),
                                        'location_id': move.picking_id.location_id.id,
                                        'location_dest_id': move.picking_id.location_dest_id.id
                                    })]
                                })
                    if picking.company_id.primecargo_autovalidate_done:
                        try:
                            picking_done = picking.button_validate()
                            if 'type' in picking_done:
                                # We have been given an action, which means that one or more moves are not finished
                                _logger.warn('One or more moves are not finished and therefore we cannot validate the picking {}'.format(picking.name))
                                continue
                        except UserError as e:
                            tb = traceback.format_exc()
                            _logger.error('Error validating picking {}: {}'.format(picking.name, e))
                            _logger.error(tb)
                    if carrier_tracking_refs:
                        picking.carrier_tracking_ref = ", ".join(carrier_tracking_refs)
                headers = {
                    'Content-Type': 'application/json; charset=utf8',
                    'Authorization': 'Token {0}'.format(company.odoo_edi_token)
                }
                response_update = requests.patch(data['url'], json={'status':'processed'}, headers=headers)
                if not response_update.status_code == 200:
                    _logger.warn('Response returned status code {}'.format(response_update.status_code))
        else:
            _logger.warn('There are no confirmed deliveries from PrimeCargo')