from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_shipping_id', 'partner_id', 'company_id')
    def onchange_partner_shipping_id(self):
        result = super().onchange_partner_shipping_id()

        if self.warehouse_id:
            # We have a warehouse configured, so that we can actually check which country it belongs to
            if self.warehouse_id.partner_id:
                # We have a partner selected on the warehouse, so that we can check the country
                company = self.company_id or self.env.user.company_id
                warehouse = self.warehouse_id
                if company.country_id and warehouse.partner_id.country_id:
                    if not company.country_id.id == warehouse.partner_id.country_id.id:
                        # The company and the warehouse do not belong to the same country. Execute fiscal positon selection with foreign country
                        self.fiscal_position_id = self.env['account.fiscal.position'].with_company(self.company_id).get_fiscal_position_by_origin_country(warehouse.partner_id.country_id.id, self.partner_id.id, self.partner_shipping_id.id)

        return result

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if self.warehouse_id:
            # We have a warehouse configured, so that we can actually check which country it belongs to
            if self.warehouse_id.partner_id:
                # We have a partner selected on the warehouse, so that we can check the country
                company = self.company_id or self.env.user.company_id
                warehouse = self.warehouse_id
                if company.country_id and warehouse.partner_id.country_id:
                    if not company.country_id.id == warehouse.partner_id.country_id.id:
                        # The company and the warehouse do not belong to the same country. Execute fiscal positon selection with foreign country
                        self.fiscal_position_id = self.env['account.fiscal.position'].with_company(self.company_id).get_fiscal_position_by_origin_country(warehouse.partner_id.country_id.id, self.partner_id.id, self.partner_shipping_id.id)
        return {}