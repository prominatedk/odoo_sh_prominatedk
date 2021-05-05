import requests
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    api_order = fields.Boolean(related="sale_id.api_order")

    def action_done(self):
        super(StockPicking, self).action_done()
        if self.api_order and self.sale_id.integration_code:
            self._send_order_shipped()

    
    def _send_order_shipped(self):
        ids = self.sale_id.integration_code.split(",")
        for f_id in ids:
            url = self.company_id.integration_api_url + "/order-fulfillments/{0}/messages".format(f_id)
            auth = self.company_id.integration_auth_token

            data = self.get_fulfillment_data()

            headers = {
                'Authorization': 'Bearer {0}'.format(auth),
                'Content-Type': 'application/json'
            }
            _logger.info('POST: %s', url)
            _logger.info('HEADERS: %s', headers)
            _logger.info('DATA: %s', data)
            response = requests.post(url, json=data, headers=headers)
            _logger.info('API RESPONSE: %s', response)
            _logger.info('API JSON: %s', response.json())


    def get_fulfillment_data(self):
        self.ensure_one()
        return {
            'origin': 'delivery',
            'type': 'success',
            'attributes': {
                'tracking_code': self.carrier_tracking_ref
            }
        }