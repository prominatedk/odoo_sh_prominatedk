import logging
import requests

_logger = logging.getLogger(__name__)

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    webshop_price = fields.Float(string="Pricing per unit (Webshop)", compute="_compute_webshop_price")
    webshop_weight = fields.Float(string="Packaging weight per unit (Webshop)", compute="_compute_webshop_weight")
    webshop_shipping_code = fields.Char(string="Shipping Code (Webshop)")
    
    virtual_available_quotation = fields.Float(string="Stock in units (Webshop)", compute="_get_virtual_available_quotation")

    @api.depends('list_price')
    def _compute_webshop_price(self):
        for p in self:
            item = p.item_ids.filtered(lambda i: i.pricelist_id.currency_id.name == 'EUR' and (i.date_end == False or i.date_end >= fields.Date.today())) if p.item_ids else False
            p.webshop_price = item[0].fixed_price * p.primecargo_inner_pack_qty if item else p.list_price * p.primecargo_inner_pack_qty

    @api.depends('weight')
    def _compute_webshop_weight(self):
        for p in self:
            p.webshop_weight = p.weight * p.primecargo_inner_pack_qty

    @api.depends('virtual_available')
    def _get_virtual_available_quotation(self):
        for product in self:
            variant_id = product.product_variant_ids[0].id if product.product_variant_ids else product.id
            lines = self.env['sale.order.line'].search([('product_id', '=', variant_id),('state', '=', 'draft')])
            qty = product.qty_available - product.outgoing_qty
            if lines:
                qty -= sum(lines.mapped('product_uom_qty'))
            product.virtual_available_quotation = product._convert_to_primecargo_pack(qty)

    def _convert_to_primecargo_pack(self, qty):
        if not self.primecargo_inner_pack_qty:
            return qty
        return qty / self.primecargo_inner_pack_qty


class ProductProduct(models.Model):
    _inherit = 'product.product'

    api_warehouse_id = fields.Many2one('stock.warehouse', help="This is the Odoo warehouse that corresponds to the warehouse used in the webshop")

            
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

        parameters = "/warehouses/{0}/products/{1}/inventory".format(self.api_warehouse_id.webshop_code, self.default_code)
        intake_date, intake_amount = self._get_next_stock_intake()
        data = {'amount': int(self.virtual_available_quotation)}
        if intake_date and intake_amount:
            data.update({
                'next_intake_date': intake_date,
                'next_intake_amount': self._convert_to_primecargo_pack(intake_amount)
            })
        _logger.info('PUT %s (%s)', url + parameters, data)
        response = requests.put(url + parameters, json=data, headers=headers)
        _logger.info('API response: %s', response.json())

    def action_update_webshop_stock_all(self):
        products = self.env['product.product'].search([('api_warehouse_id', '!=', False)])
        for p in products:
            p.action_update_webshop_stock()

    def _get_next_stock_intake(self):
        receipt_operations = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '!=', False)])
        pickings = self.env['stock.picking'].search([('state', 'not in', ['done', 'cancel']), ('picking_type_id', 'in', receipt_operations.ids)])
        if not pickings:
            return False, False
        moves = self.env['stock.move'].search([('product_id', '=', self.id), ('picking_id', 'in', pickings.ids)])

        if moves:
            move = moves.sorted(key=lambda m: m.date_expected)[0]
            return move.date_expected.strftime("%Y-%m-%d"), int(move.product_uom_qty)
        return False, False
