from odoo import models, fields, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _convert_to_warehouse_pack(self, qty):
        self.ensure_one()
        return self.product_tmpl_id._convert_to_warehouse_pack(qty)

    def _convert_from_warehouse_pack(self, qty):
        self.ensure_one()
        return self.product_tmpl_id._convert_from_warehouse_pack(qty)