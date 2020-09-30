import requests

from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    primecargo_valid = fields.Boolean(compute="check_move_products_primecargo")
    picking_type_code = fields.Selection(related="picking_type_id.code")
    edi_document_id = fields.Char(string='FlexEDI Platform Document ID', readonly=True)
    edi_document_guid = fields.Char(string='Provider Document ID', readonly=True)
    edi_document_status = fields.Selection(readonly=True, selection=[
        ('pending', 'Waiting to be sent'),
        ('sent', 'Sent'),
        ('validated', 'Validated'),
        ('recieved', 'Recieved'),
        ('processed', 'Processing confirmed by client'),
        ('failed_internal', 'Document failed internally'),
        ('failed_vans', 'Document failed at provider')
    ], string='EDI Status', track_visibility='onchange')
    edi_document_status_message = fields.Text(
        readonly=True, string='EDI Status Details', track_visibility='onchange')
    primecargo_shipping_product_code = fields.Char(string="PrimeCargo Shipping Product", help="Holds the PrimeCargo Shipping Product Code as per agreement with PrimeCargo for this delivery")


    def action_send_primecargo(self):
        for picking in self:
            if picking.picking_type_code == 'incoming':
                self.env['odoo_edi.primecargo.stock.picking.incoming'].create_edi(picking)
            if picking.picking_type_code == 'outgoing':
                self.env['odoo_edi.primecargo.stock.picking.outgoing'].create_edi(picking)

    def check_move_products_primecargo(self):
        for picking in self:
            if picking.picking_type_code in ['incoming', 'outgoing']:
                picking.primecargo_valid = all([x.product_id.in_primecargo_wms for x in picking.move_ids_without_package])
            else:
                picking.primecargo_valid = False


