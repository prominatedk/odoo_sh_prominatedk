import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    template_in_primecargo_wms = fields.Boolean(compute='_variants_in_primecargo')

    def action_use_in_primecargo_wms(self):
        if not self.template_in_primecargo_wms:
            for product in self.product_variant_ids.filtered(lambda p: p.in_primecargo_wms == False):
                product.action_use_in_primecargo_wms()
        else:
            for product in self.product_variant_ids:
                product.action_use_in_primecargo_wms()

    def _variants_in_primecargo(self):
        if all([x.in_primecargo_wms == True for x in self.product_variant_ids]):
            self.template_in_primecargo_wms = True
        else:
            self.template_in_primecargo_wms = False