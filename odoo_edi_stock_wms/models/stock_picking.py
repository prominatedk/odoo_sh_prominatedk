from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    flexedi_wms_picking_ids = fields.One2many('flexedi.document.wms.picking', 'picking_id')

    flexedi_wms_picking_status = fields.Selection(selection=[
        ('pending', 'Waiting to be sent to VANS'),
        ('sent', 'Sent to VANS'),
        ('validated', 'Validated by VANS'),
        ('recieved', 'Recieved from VANS'),
        ('processed', 'Processing confirmed by client'),
        ('failed_internal', 'Document failed internally'),
        ('failed_vans', 'Document failed at VANS')
    ], compute='_compute_flexedi_wms_picking_status', string="FlexEDI Status", store=True, help='Shows the status of the last time the document was sent to FlexEDI')

    flexedi_can_send_wms_document = fields.Boolean(compute='_compute_flexedi_can_send_wms_document', string="Sendable using FlexEDI", help='Determines if the document can be sent using FlexEDI')

    is_using_flexedi_wms = fields.Boolean(compute='_compute_is_using_flexedi_wms', string="Document is using FlexEDI")

    @api.depends('flexedi_wms_picking_ids.state')
    def _compute_flexedi_wms_picking_status(self):
        for record in self:
            record.flexedi_wms_picking_status = record.flexedi_wms_picking_ids[0].state if len(record.flexedi_wms_picking_ids) else False

    @api.depends('partner_id', 'partner_id.flexedi_document_format_mapping_ids')
    def _compute_flexedi_can_send_wms_document(self):
        for record in self:
            record.flexedi_can_send_wms_document = True if record.picking_type_id.flexedi_document_format_id else False

    @api.depends('flexedi_wms_picking_ids')
    def _compute_is_using_flexedi_wms(self):
        for record in self:
            record.is_using_flexedi_wms = len(record.flexedi_wms_picking_ids) > 0

    def action_flexedi_send_to_wms(self):
        for record in self:
            if not record.flexedi_can_send_wms_document:
                raise UserError(_('The picking %s cannot be sent to the warehouse using EDI, as the picking operation type is not properly configured' % (record.name,)))
            record._queue_for_flexedi_wms()

    def _queue_for_flexedi_wms(self):
        # Any valiation logic required to run at this point should override this method, perform their validation and the execute the super() method to get the docment queued for sending
        self.ensure_one()
        self.env['flexedi.document.wms.picking'].create({
            'picking_id': self.id,
            'company_id': self.company_id.id or self.env.user.company_id.id,
            'partner_id': self.partner_id.id,
            'document_format_id': self.picking_type_id.flexedi_document_format_id.id
        })