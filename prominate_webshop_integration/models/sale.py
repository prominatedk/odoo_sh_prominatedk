import json
import requests
import operator
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    integration_code = fields.Char()
    api_order = fields.Boolean()


    @api.model
    def message_new(self, msg, custom_values=None):
        company = self.env['res.company'].browse(self._context.get('company_id'))
        vals = self._parse_json(msg.get('attachments'))
        vals['api_order'] = True
        if company and company.integration_analytic_account_id:
            vals['analytic_account_id'] = company.integration_analytic_account_id.id

        return super(SaleOrder, self).message_new(msg, custom_values=vals)
        

    def _parse_json(self, json_file):
        vals = {}
        data = json.loads(json_file[0].content.decode('utf-8'))
        vals['integration_code'] = data['channel']['code']
        vals['client_order_ref'] = data['order_number']
        vals['note'] = data['notes']
        vals['name'] = self.env['ir.sequence'].next_by_code('sale.order')
        vals['partner_id'] = self._get_partner_data(data)
        vals['order_line'] = [(0, 0, vals) for vals in self._get_order_items(data)]
        vals['currency_id'] = self.env['res.currency'].search([('name', '=', data['currency_code'])])

        return vals

    def _get_partner_data(self, data):
        info = data['customer']
        address = data['shipments'][0]['recipient_address']
        existing_partner = self.env['res.partner'].search([('email', 'ilike', info['email'])], limit=1)
        if existing_partner:
            return existing_partner.id
        else:
            partner_country = self.env['res.country'].search([('code', 'ilike', address['country_code'])])
            return self.env['res.partner'].create({
                'name': info['full_name'],
                'phone': info['phone_number'],
                'ref': info['customer_number'],
                'email': info['email'],
                'country_id': partner_country.id,
                'street': address['street'],
                'street2': address['street2'],
                'zip:': address['postcode'],
                'city': address['city']
            }).id

    def _get_order_items(self, data):
        vals = []
        for val in data['items']:
            product = self.env['product.product'].search([('default_code', '=', val['variant']['code'])])
            if not product:
                raise ValidationError(_("Error! Product %s not found!") % val['variant']['code'])
            vals.append({'product_id': product.id,
                        'product_uom_qty': val['quantity'],
                        'price_unit': val['unit_price']})
        for val in data['adjustments']:
            if val['type'] == 'shipping':
                product = self.env['product.product'].search([('default_code', '=', val['code'])])
                if not product:
                    raise ValidationError(_("Error! Product %s not found!") % val['code'])
                vals.append({'product_id': product.id,
                             'product_uom_qty': 1,
                             'price_unit': val['amount']})
        return vals

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.api_order:
            res._send_stock_update()
        return res


    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        if self.api_order and self.integration_code and self.client_order_ref:
            self._send_order_cancel()
        return res

    def _send_order_cancel(self):
        fulfillment = self.integration_code + '-' + self.client_order_ref if self.integration_code else self.client_order_ref
        url = self.company_id.integration_api_url + "/order-fulfillments/{0}/messages".format(fulfillment)
        auth = self.company_id.integration_auth_token

        data = {
            'origin': 'delivery',
            'type': 'failed'
        }
        headers = {
            'Authorization': 'Bearer {0}'.format(auth),
            'Content-Type': 'application/json'
        }
        _logger.info('POST %s (%s)', url, data)
        response = requests.post(url, json=data, headers=headers)
        _logger.info('API response: %s', response.json())
        self._send_stock_update(cancel=True)


    def _send_stock_update(self, cancel=False):
        url = self.company_id.integration_api_url
        auth = self.company_id.integration_auth_token
        headers = {
            'Authorization': 'Bearer {0}'.format(auth),
            'Content-Type': 'application/json'
        }
        
        func = operator.add if cancel else operator.sub # Add values to webshop stock if order is cancelled
        products = {}

        for line in self.order_line:
            if products.get(line.product_id.default_code):
                products[line.product_id.default_code] = func(products[line.product_id.default_code], line.product_uom_qty)
            else:
                products[line.product_id.default_code] = func(line.product_id.virtual_available, line.product_uom_qty)
        for code, amount in products.items():
            parameters = "/warehouses/{0}/products/{1}/inventory".format(self.warehouse_id.display_name, code)
            data = {'amount': int(amount)}
            _logger.info('PUT %s (%s)', url + parameters, data)
            response = requests.put(url + parameters, json=data, headers=headers)
            _logger.info('API response: %s', response.json())


class SaleOrderMail(models.Model):
    _name = 'sale.order.mail'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char(required=True, related="alias_name", readonly=False)
    alias_name = fields.Char()


    def get_alias_model_name(self, vals):
        return vals.get('alias_model', 'sale.order')

    def get_alias_values(self):
        vals = super(SaleOrderMail, self).get_alias_values()
        return vals