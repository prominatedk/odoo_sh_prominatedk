from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    template_in_primecargo_wms = fields.Boolean(compute='_variants_in_primecargo')
    primecargo_customs_description = fields.Char(size=25)

    def action_use_in_primecargo_wms(self):
        for record in self:
            if not record.template_in_primecargo_wms:
                for product in record.product_variant_ids.filtered(lambda p: p.in_primecargo_wms == False):
                    product.action_use_in_primecargo_wms()
            else:
                for product in record.product_variant_ids:
                    product.action_use_in_primecargo_wms()

    def _variants_in_primecargo(self):
        for record in self:
            if all([x.in_primecargo_wms == True for x in record.product_variant_ids]):
                record.template_in_primecargo_wms = True
            else:
                record.template_in_primecargo_wms = False