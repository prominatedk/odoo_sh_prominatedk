from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    in_primecargo_wms = fields.Boolean()

    def action_use_in_primecargo_wms(self):
        for record in self:
            record._validate_edi_fields()
            document = record.env['flexedi.document.wms.product'].create({
                'product_id': record.id,
                'document_format_id': self.env.ref('odoo_edi_stock_wms_primecargo.flexedi_document_format_primecargo_wms_product').id,
                'state': 'pending',
            })
            document.send_document()
            record.in_primecargo_wms = document.blocking_level != 'error'

    def _validate_edi_fields(self):
        self.ensure_one()
        if not self.barcode or not self.default_code:
            raise ValidationError(
                _('You must fill out barcode and default code fields to use this product with Primecargo WMS'))
