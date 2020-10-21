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
        json_file = msg.get('attachments')
        if not json_file:
            self.env['integration.error.log'].create({'msg': _("Error! No JSON file attached to mail"), 'action': 'odoo_support'})
            raise ValidationError(_("Error! No JSON file attached to mail"))
        vals = self._parse_json(json_file[0])
        vals['api_order'] = True
        if company and company.integration_analytic_account_id:
            vals['analytic_account_id'] = company.integration_analytic_account_id.id

        return super(SaleOrder, self).message_new(msg, custom_values=vals)
        

    def _parse_json(self, json_file):
        vals = {}
        try:
            partner = self._get_partner_data(data)
            data = json.loads(json_file.content.decode('utf-8'))
            self.validate_data(data)
            vals['integration_code'] = data['channel']['code']
            vals['client_order_ref'] = data['order_number']
            vals['note'] = data['notes']
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.order')
            vals['partner_id'] = partner.id
            vals['order_line'] = [(0, 0, vals) for vals in self._get_order_items(data, partner)]
            vals['currency_id'] = self.env['res.currency'].search([('name', '=', data['currency_code'])])

            return vals
        except KeyError as err:
            self.env['integration.error.log'].create({'msg': _("Error! JSON file did not include expected data\n\n%s") % err, 'action': 'odoo_support'})
            raise
        except TypeError as err:
            self.env['integration.error.log'].create({'msg': _("Error! Could not parse data in JSON file\n\n%s") % err, 'action': 'odoo_support'})
            raise
        except json.JSONDecodeError as err:
            self.env['integration.error.log'].create({'msg': _("Error! Could not decode JSON file\n\n%s") % err, 'action': 'odoo_support'})
            raise
        except ValidationError as err: # ValidationErrors should be handled for each case
            raise
        except Exception as err:
            self.env['integration.error.log'].create({'msg': _("Error! Undefined error!\n\n%s") % err, 'action': 'odoo_support'})
            raise


    def validate_data(self, data):
        if not data.get('order_number'):
            self.env['integration.error.log'].create({'msg': _("Error! No order number in JSON data"), 'action': 'link_support'})
            raise ValidationError(_("Error! No order number in JSON data"))
        cur = self.env['res.currency'].search([('name', '=', data['currency_code'])])
        if not cur:
            self.env['integration.error.log'].create({'msg': _("Error! Could not read currency code in JSON data"), 'action': 'odoo_support'})
            raise ValidationError(_("Error! Could not read currency code in JSON data"))

            

    def _get_partner_data(self, data):
        info = data['customer']
        address = data['shipments'][0]['recipient_address']
        existing_partner = self.env['res.partner'].search([('email', 'ilike', info['email'])], limit=1)
        if existing_partner:
            return existing_partner
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
            })

    def _get_order_items(self, data, partner):
        vals = []
        OrderLine = self.env['sale.order.line']
        for val in data['items']:
            product = self.env['product.product'].search([('default_code', '=', val['variant']['code'])])
            if not product:
                self.env['integration.error.log'].create({'msg': _("Error! Product %s not found!") % val['code'], 'action': 'check_product'})
                raise ValidationError(_("Error! Product %s not found!") % val['variant']['code'])
            quantity = val['quantity'] * product.primecargo_inner_pack_qty if product.primecargo_inner_pack_qty else val['quantity']
            vals.append({'product_id': product.id,
                        'product_uom_qty': quantity,
                        'price_unit': (val['unit_price'] / 100.0) / product.primecargo_inner_pack_qty if product.primecargo_inner_pack_qty else (val['unit_price'] / 100.0),
                        'product_uom': product.uom_id.id,
                        'name': OrderLine.get_sale_order_line_multiline_description_sale(product.with_context(lang=partner.lang,
                                                                                                              partner=partner,
                                                                                                              quantity=quantity,
                                                                                                              date=fields.Date.today()))})
        for val in data['adjustments']:
            if val['type'] == 'shipping':
                company = self.env['res.company'].browse(self._context.get('company_id'))
                product = company.webshop_shipping_product_id
                vals.append({'product_id': product.id,
                             'product_uom_qty': 1.0,
                             'price_unit': product.list_price,
                             'product_uom': product.uom_id.id,
                             'name': OrderLine.get_sale_order_line_multiline_description_sale(product.with_context(lang=partner.lang,
                                                                                                                    partner=partner,
                                                                                                                    quantity=1.0,
                                                                                                                    date=fields.Date.today()))})
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