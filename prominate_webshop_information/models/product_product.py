from odoo import models, fields, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    webshop_shipping_code = fields.Char(string="Shipping Code (Webshop)", related='product_tmpl_id.webshop_shipping_code', store=True)

    def _convert_to_warehouse_pack(self, qty):
        self.ensure_one()
        return self.product_tmpl_id._convert_to_warehouse_pack(qty)

    def _convert_from_warehouse_pack(self, qty):
        self.ensure_one()
        return self.product_tmpl_id._convert_from_warehouse_pack(qty)