from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    webshop_price = fields.Float(string="Pricing per unit (Webshop)", compute="_compute_webshop_price")
    webshop_weight = fields.Float(string="Packaging weight per unit (Webshop)", compute="_compute_webshop_weight")
    webshop_shipping_code = fields.Char(string="Shipping Code (Webshop)")

    warehouse_outer_pack_qty = fields.Integer(string='Quantity in outside pack (Warehouse)')
    warehouse_inner_pack_qty = fields.Integer(string='Quantity in inside pack (Warehouse)')

    virtual_available_quotation = fields.Float(string="Stock in units (Webshop)", compute="_get_virtual_available_quotation")

    @api.depends('list_price')
    def _compute_webshop_price(self):
        for p in self:
            item_ids = p.env['product.pricelist.item'].search(['|', ('product_tmpl_id', '=', p.id), ('product_id', 'in', p.product_variant_ids.ids)])
            item = item_ids.filtered(lambda i: i.pricelist_id.currency_id.name == 'EUR' and (i.date_end == False or i.date_end >= fields.Date.today())) if item_ids else False
            p.webshop_price = item[0].fixed_price * p.warehouse_inner_pack_qty if item else p.list_price * p.warehouse_inner_pack_qty

    @api.depends('weight')
    def _compute_webshop_weight(self):
        for p in self:
            p.webshop_weight = p.weight * p.warehouse_inner_pack_qty

    @api.depends('virtual_available')
    def _get_virtual_available_quotation(self):
        for product in self:
            variant_id = product.product_variant_ids[0].id if product.product_variant_ids else product.id
            lines = self.env['sale.order.line'].search([('product_id', '=', variant_id),('state', '=', 'draft')])
            qty = product.qty_available - product.outgoing_qty
            if lines:
                qty -= sum(lines.mapped('product_uom_qty'))
            product.virtual_available_quotation = product._convert_to_warehouse_pack(qty)

    def _convert_to_warehouse_pack(self, qty):
        self.ensure_one()
        if not self.warehouse_inner_pack_qty:
            return qty
        return qty / self.warehouse_inner_pack_qty

    def _convert_from_warehouse_pack(self, qty):
        self.ensure_one()
        if not self.warehouse_inner_pack_qty:
            return qty
        return qty * self.warehouse_inner_pack_qty