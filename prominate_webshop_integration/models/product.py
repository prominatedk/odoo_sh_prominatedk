import logging
import requests

_logger = logging.getLogger(__name__)

from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    virtual_available_quotation = fields.Float(compute="_get_virtual_available_quotation")
    api_warehouse_id = fields.Many2one('stock.warehouse', help="This is the Odoo warehouse that corresponds to the warehouse used in the webshop")

    @api.depends('virtual_available')
    def _get_virtual_available_quotation(self):
        for product in self:
            lines = self.env['sale.order.line'].search([('product_id', '=', product.id),('state', '=', 'draft')])
            qty = product.virtual_available
            if lines:
                qty -= sum(lines.mapped('product_uom_qty'))
            product.virtual_available_quotation = qty
            
    def action_open_quotations(self):
        # TODO: Open all quotations with this specific product
        return {
            
        }

    def action_update_webshop_stock(self):
        if not self.api_warehouse_id:
            return
        url = self.company_id.integration_api_url
        auth = self.company_id.integration_auth_token
        headers = {
            'Authorization': 'Bearer {0}'.format(auth),
            'Content-Type': 'application/json'
        }

        parameters = "/warehouses/{0}/products/{1}/inventory".format(self.api_warehouse_id.display_name, self.default_code)
        data = {'amount': int(self.virtual_available_quotation)}
        _logger.info('PUT %s (%s)', url + parameters, data)
        response = requests.put(url + parameters, json=data, headers=headers)
        if response.get('code') and int(response.get('code')) != 200:
            _logger.error('API Error! %s', response.json())

    def action_update_webshop_stock_all(self):
        products = self.env['product.product'].search([])
        for p in products:
            p.action_update_webshop_stock()