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
        company = self.env['res.company'].browse(custom_values.get('company_id')) if custom_values and custom_values.get('company_id') else False
        json_file = msg.get('attachments')
        if not json_file:
            self.env['integration.error.log'].create({'msg': _("Error! No JSON file attached to mail"), 'action': 'odoo_support'})
            raise ValidationError(_("Error! No JSON file attached to mail"))
        vals = self._parse_json(json_file[0], company)

        return super(SaleOrder, self).message_new(msg, custom_values=vals)
        

    def _parse_json(self, json_file, company):
        vals = {}
        try:
            data = json.loads(json_file.content.decode('utf-8'))
            self.validate_data(data)
            partners = self._get_partner_data(data)
            currency = self.env['res.currency'].search([('name', '=', data['currency_code'])])
            pricelist = self.env['product.pricelist'].search([('currency_id', '=', currency.id)], limit=1)
            ref = ",".join([x["id"] for x in data["fulfillments"]]) if data.get('fulfillments') else False
            vals['integration_code'] = ref
            vals['client_order_ref'] = data['order_number']
            vals['note'] = data['notes']
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.order')
            vals['partner_id'] = partners['partner_id'].id
            vals['partner_invoice_id'] = partners['partner_invoice_id'].id or company.placeholder_partner_id.id
            vals['partner_shipping_id'] = company.placeholder_partner_id.id
            vals['pricelist_id'] = pricelist.id
            vals['shipping_info'] = self._note_shipping_info(data['shipments'][0]['recipient_address'])
            vals['billing_info'] = self._note_billing_info(data['billing_address'])
            vals['order_line'] = [(0, 0, vals) for vals in self._get_order_items(data, partners['partner_id'], company)]
            vals['currency_id'] = currency.id
            vals['api_order'] = True
            if company.integration_analytic_account_id:
                vals['analytic_account_id'] = company.integration_analytic_account_id.id

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

    # Prominate wants the shipping info logged as a note in the activity log
    # Shipping address is a free text field in the webshop, so it cannot be reliably used to
    # pick the correct shipping address in Odoo
    def _note_shipping_info(self, data):
        return """
        <p>
            Shipping Info:<br/><br/>

            {8}<br/>
            {0} {1}<br/>
            {2}<br/>
            {3}<br/>
            {4} {5}<br/>
            {6}<br/><br/>
            {7}
        </p>
        """.format(data['first_name'], data['last_name'],
                   data['street'], data['street2'],
                   data['postcode'], data['city'], data['country_code'],
                   data['phone_number'], data['organization'])

    def _note_billing_info(self, data):
        return """
        <p>
            Billing Info:<br/><br/>

            {9}<br/>
            {0} {1}<br/>
            {8}<br/><br/>
            {2}<br/>
            {3}<br/>
            {4} {5}<br/>
            {6}<br/><br/>
            {7}
        </p>
        """.format(data['first_name'], data['last_name'],
                   data['street'], data['street2'],
                   data['postcode'], data['city'], data['country_code'],
                   data['phone_number'], data['vatid'], data['organization'])


    def validate_data(self, data):
        if not data.get('order_number'):
            self.env['integration.error.log'].create({'msg': _("Error! No order number in JSON data"), 'action': 'link_support'})
            raise ValidationError(_("Error! No order number in JSON data"))
        cur = self.env['res.currency'].search([('name', '=', data['currency_code'])])
        if not cur:
            self.env['integration.error.log'].create({'msg': _("Error! Could not read currency code in JSON data"), 'action': 'odoo_support'})
            raise ValidationError(_("Error! Could not read currency code in JSON data"))

            
    def _get_partner_data(self, data):
        partners = {}
        info = data['customer']
        shipping = data['shipments'][0]['recipient_address']
        billing = data['billing_address']
        existing_partner = self.env['res.partner'].search([('email', 'ilike', info['email'])], limit=1)
        if existing_partner:
            partners['partner_id'] = existing_partner
        else:
            partner_country = self.env['res.country'].search([('code', 'ilike', shipping['country_code'])])
            partners['partner_id'] = self.env['res.partner'].create({
                'name': info['full_name'],
                'phone': info['phone_number'],
                'ref': info['customer_number'],
                'email': info['email'],
                'country_id': partner_country.id,
                'street': shipping['street'],
                'street2': shipping['street2'],
                'zip:': shipping['postcode'],
                'city': shipping['city']
            })
        partners['partner_invoice_id'] = self._get_invoice_address(billing) or partners['partner_id']
        
        return partners
        
    def _get_invoice_address(self, address):
        existing_address = self.env['res.partner'].search([('vat', '=', address['vatid'])], limit=1)
        return existing_address.commercial_partner_id if existing_address and existing_address.commercial_partner_id.email else False


    def _get_order_items(self, data, partner, company):
        vals = []
        for shipment in data['shipments']:
            for item in shipment['items']:
                product = self.env['product.product'].search([('default_code', '=', item['variant']['code'])])
                if not product:
                    self.env['integration.error.log'].create({'msg': _("Error! Product %s not found!") % item['variant']['code'], 'action': 'check_product'})
                    raise ValidationError(_("Error! Product %s not found!") % item['variant']['code'])
                quantity = item['quantity'] * product.primecargo_inner_pack_qty if product.primecargo_inner_pack_qty else item['quantity']
                vals.append({'product_id': product.id,
                            'product_uom_qty': quantity,
                            'price_unit': (item['unit_price'] / 100.0) / product.primecargo_inner_pack_qty if product.primecargo_inner_pack_qty else (item['unit_price'] / 100.0),
                            'product_uom': product.uom_id.id,
                            'name': product.with_context(lang=partner.lang,
                                                        partner=partner,
                                                        quantity=quantity,
                                                        date=fields.Date.today()).get_product_multiline_description_sale()})
            #Shipping product
            product = self.env['product.product'].search([('webshop_shipping_code', '=', shipment['method']['code'])], limit=1)
            if not product:
                self.env['integration.error.log'].create({'msg': _('Error! Shipping product %s not found!') % shipment['method']['code'], 'action': 'check_product'})
                raise ValidationError(_("Error! Shipping product %s not found!") % shipment['method']['code'])
            else:
                shipping_info = list(filter(lambda x: x.get('type') == 'shipping' and x.get('code') == shipment['method']['code'], shipment['adjustments']))
                amount = shipping_info[0].get('amount', product.list_price) if shipping_info else product.list_price
                vals.append({'product_id': product.id,
                            'product_uom_qty': 1.0,
                            'price_unit': amount / 100,
                            'product_uom': product.uom_id.id,
                            'name': product.with_context(lang=partner.lang,
                                                        partner=partner,
                                                        quantity=1.0,
                                                        date=fields.Date.today()).get_product_multiline_description_sale()})
        return vals

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.api_order:
            res._send_stock_update()
        if vals.get('billing_info'):
            res.message_post(body=vals['billing_info'])
        if vals.get('shipping_info'):
            res.message_post(body=vals['shipping_info'])
        return res


    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        if self.api_order and self.integration_code:
            self._send_order_cancel()
        return res

    def _send_order_cancel(self):
        ids = self.integration_code.split(",")
        for f_id in ids:
            url = self.company_id.integration_api_url + "/order-fulfillments/{0}/messages".format(f_id)
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
            _logger.info('API response: %s', response.text)
            if response.json().get('code') and (response.json()['code'] != '400' or response.json()['code'] != 400):
                self.env['integration.error.log'].create({'msg': _("Error! Response code %s with message:\n\n%s") % (response.json()['code'], response.json()['message']), 'action': 'odoo_support'})
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
            if line.product_id.api_warehouse_id:
                if products.get(line.product_id.default_code):
                    products[line.product_id.default_code] = func(products[line.product_id.default_code], line.product_uom_qty)
                else:
                    products[line.product_id.default_code] = func(line.product_id.virtual_available, line.product_uom_qty)
        for code, amount in products.items():
            parameters = "/warehouses/{0}/products/{1}/inventory".format(self.warehouse_id.webshop_code, code)
            data = {'amount': int(amount)}
            _logger.info('PUT %s (%s)', url + parameters, data)
            response = requests.put(url + parameters, json=data, headers=headers)
            _logger.info('API response: %s', response.text)


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