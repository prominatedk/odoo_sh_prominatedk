import requests
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    api_order = fields.Boolean(related="sale_id.api_order")

    @api.onchange('scheduled_date')
    def _send_intake_update(self):
        if self.state not in ['done', 'cancel']:
            for move in self.move_ids_without_package:
                move.product_id.action_update_webshop_stock()

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
            _logger.info('POST %s (%s)', url, data)
            if not self.company_id.integration_in_production:
                _logger.info('Integration testing mode - Skipping request')
                continue
            response = requests.post(url, json=data, headers=headers)
            _logger.info('API response: %s', response.json())


    def get_fulfillment_data(self):
        self.ensure_one()
        return {
            'origin': 'delivery',
            'type': 'success',
            'attributes': {
                'tracking_code': self.carrier_tracking_ref
            }
        }