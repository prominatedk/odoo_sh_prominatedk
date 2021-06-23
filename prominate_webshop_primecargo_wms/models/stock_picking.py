from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_fulfillment_data(self):
        self.ensure_one()
        vals = super(StockPicking, self).get_fulfillment_data()
        if self.primecargo_shipping_product_id.id:
            vals['attributes']['carrier'] = self.primecargo_shipping_product_id.webshop_carrier_code

        return vals