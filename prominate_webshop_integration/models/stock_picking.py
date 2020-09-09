import requests
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    api_order = fields.Boolean(related="sale_id.api_order")
    integration_tracking_code = fields.Char()

    def action_done(self):
        super(StockPicking, self).action_done()
        if self.api_order and self.sale_id.integration_code and self.sale_id.client_order_ref:
            self._send_order_shipped()

    
    def _send_order_shipped(self):
        fulfillment = self.sale_id.integration_code + '-' + self.sale_id.client_order_ref if self.sale_id.integration_code else self.sale_id.client_order_ref
        url = self.company_id.integration_api_url + "/order-fulfillments/{0}/messages".format(fulfillment)
        auth = self.company_id.integration_auth_token

        data = {
            'origin': 'delivery',
            'type': 'success',
            'attributes': {
                'tracking_code': self.integration_tracking_code
            }
        }
        headers = {
            'Authorization': 'Bearer {0}'.format(auth),
            'Content-Type': 'application/json'
        }
        _logger.info('POST %s (%s)', url, data)
        response = requests.post(url, json=data, headers=headers)
        if response.get('code') and int(response.get('code')) != 200:
            _logger.error('API Error! %s', response.json())