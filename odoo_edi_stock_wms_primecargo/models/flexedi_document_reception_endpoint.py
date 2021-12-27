from odoo import models, fields, api, _
import json
import logging
_logger = logging.getLogger(__name__)

class FlexediDocumentReceptionEndpoint(models.Model):
    _inherit = 'flexedi.document.reception.endpoint'

    def _recieve_primecargo_wms_sales_order_export_document(self, company, document):
        return self._recieve_primecargo_wms_picking_confirmation(company, document)

    def _recieve_primecargo_wms_purchase_order_export_document(self, company, document):
        return self._recieve_primecargo_wms_picking_confirmation(company, document)

    def _recieve_primecargo_wms_picking_confirmation(self, company, document):
        if document['order_result_message'] == 'OK':
            source_edi_document = self.env['flexedi.document.wms.picking'].search([('edi_uuid', '=', document['order_uuid'])], limit=1)
            if not source_edi_document.exists():
                _logger.error('Unable to process document as no document exists in the system with UUID %s' % (document['order_uuid'],))
                return False
            if not source_edi_document.picking_id:
                _logger.error('The UUID %s refers to a document with no picking assigned. This should not happen unless someone has made breaking modifications of odoo_edi_stock_wms' % (document['order_uuid'],))
                return False
            picking = source_edi_document.picking_id
            # Create an entry to represent to recieved document so that we have it for future reference on the returned data
            confirmation_edi_document = self.env['flexedi.document.wms.picking'].create({
                'edi_id': document['pk'],
                'edi_uuid': document['uuid'],
                'state': 'recieved', # It is important to explicitly set the state as it might otherwise be handled as something that we should send
                'company_id': company.id,
                'partner_id': picking.partner_id.id,
                'picking_id': picking.id,
                'response_data': json.dumps(document, sort_keys=True, indent=4)
            })
            if picking.state in ['done', 'cancel']:
                _logger.error('Picking %s is marked completed, so we cannot update it. Marking document as failed during processing')
                if confirmation_edi_document._update_document({
                    'status': 'failed_internal',
                    'status_message': 'Unable to update an already completed order',
                }):
                    confirmation_edi_document.write({
                        'state': 'failed_internal',
                        'error': _('<p>Unable to update an already completed order</p>'),
                        'blocking_level': 'error'
                    })
            for line in document['purchaseorderexportline_set']:
                # TODO: Verify if the below actually works on 13.0, as it just copied over from 14.0 version of stock-workflow/odoo_edi_primecargo_wms
                move = picking.move_ids_without_package.filtered(lambda l: l.product_id.barcode == line['barcode_no'] or l.product_id.default_code == line['part_number'])
                if not move.exists():
                    _logger.error('No stock.move found for product barcode {} or internal reference {} for order {}'.format(line['barcode_no'], line['part_number'], picking.name))
                    confirmation_edi_document.write({
                        'error': confirmation_edi_document.error + '<p>No stock.move found for product barcode %s or internal reference %s</p>' % (line['barcode_no'], line['part_number']),
                        'blocking_level': 'warning' if not confirmation_edi_document.blocking_level == 'error' else 'error'
                    })
                    continue
                # We want to only work with one move for a product, so we will register move lines for the first move only. Odoo will handle multiple moves during validation
                if len(move) > 1:
                    move = move[0]
                if move.product_id.tracking in ['lot', 'serial']:
                    # If we are using lots or serial numbers, we did already send to PrimeCargo which ones to use
                    # So we will loop over the reserved move lines and see if we can find it
                    line_found = False
                    for ml in move.move_line_nosuggest_ids:
                        if ml.lot_id.name == line['batch_number']:
                            # We have found the line
                            ml.write({
                                'qty_done': line['quantity']
                            })
                    if not line_found:
                        # We went through all move lines and could not find one for the lot/serial returned from PrimeCargo
                        # We will now register the move line
                        move.write({
                            'move_line_nosuggest_ids': [(0,0, {
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'qty_done': line['quantity'],
                                'lot_id': (0,0, {
                                    'name': line['batch_number']
                                }),
                                'location_id': move.picking_id.location_id.id,
                                'location_dest_id': move.picking_id.location_dest_id.id,
                                'picking_id': picking.id
                            })]
                        })
            if company.flexedi_wms_autovalidate_done:
                picking_done = picking.button_validate()
                if 'type' in picking_done:
                    # We have been given an action, which means that one or more moves are not finished
                    _logger.warn('One or more moves are not finished and therefore we cannot validate the picking {}'.format(picking.name))
            # Mark document processed
            confirmation_edi_document.update_document_state('processed')
            return confirmation_edi_document
        else:
            return False

    def _recieve_primecargo_wms_stock_correction_document(self, company, document):
        product = self.env['product.product'].search(['|',('barcode', '=', document['barcode']),('default_code', '=', document['part_number'])], limit=1)
        if not product.exists():
            return False
        confirmation_edi_document = self.env['flexedi.document.wms.stock.adjustment'].create({
            'edi_id': document['pk'],
            'edi_uuid': document['uuid'],
            'state': 'recieved', # It is important to explicitly set the state as it might otherwise be handled as something that we should send
            'company_id': company.id,
            'product_id': product.id,
            'response_data': json.dumps(document, sort_keys=True, indent=4)
        })
        adjustment = self.env['inventory.adjustment'].create({
            'name': fields.Date.to_string(fields.Date.today()),
            'state': 'draft',
            'line_ids': [(0, 0, {
                'product_id': product.id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'product_uom_id': product.uom_id.id,
                'product_qty': product.qty_available + document['quantity_change']
            })]
        })
        # Start inventory adjustment process
        adjustment.action_start()
        # If that works, we immediately validate it
        adjustment.action_validate()
        # Respond to FlexEDI with information about having processed the document
        confirmation_edi_document.update_document_state('processed')
        return confirmation_edi_document