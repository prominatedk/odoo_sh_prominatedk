from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    in_primecargo_wms = fields.Boolean()

    def action_use_in_primecargo_wms(self):
        if self.in_primecargo_wms:
            self.in_primecargo_wms = False
        else:
            self._validate_edi_fields()
            wms_masterdata_document = self.env['product.primecargo.wms.masterdata'].search(
                [('edi_document_status', '=', False), ('company_id', '=', self.company_id.id)])

            if wms_masterdata_document and wms_masterdata_document.product_ids and any([x.barcode == self.barcode and x.default_code == self.default_code for x in wms_masterdata_document.product_ids]):
                raise ValidationError(
                    _('This product is already pending in Primecargo WMS'))
            if wms_masterdata_document:
                wms_masterdata_document.write(
                    {'product_ids': [(4, self.id, 0)]})
            if not wms_masterdata_document:
                self.env['product.primecargo.wms.masterdata'].create(
                    {'company_id': self.company_id.id, 'product_ids': [(4, self.id, 0)]})
            self.in_primecargo_wms = True

    def _validate_edi_fields(self):
        if not self.barcode or not self.default_code:
            raise ValidationError(
                _('You must fill out barcode and default code fields to use this product with Primecargo WMS'))
