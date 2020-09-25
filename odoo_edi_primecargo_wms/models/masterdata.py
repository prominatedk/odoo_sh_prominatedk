import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api


class ProductPrimecargoWmsMasterdata(models.Model):
    _name = 'product.primecargo.wms.masterdata'
    _description = 'Primecargo Masterdata'


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

    company_id = fields.Many2one('res.company')
    product_ids = fields.Many2many('product.product')

    def cron_send_masterdata(self):
        send_data = self.env['product.primecargo.wms.masterdata'].search([('edi_document_status', 'in', [False, 'failed_internal'])])
        for data in send_data:
            self.env['odoo_edi.primecargo.masterdata'].create_edi(data)