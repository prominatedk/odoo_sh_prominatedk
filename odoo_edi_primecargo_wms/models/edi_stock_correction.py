import requests
import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.addons.odoo_edi.models.edi_document import LIVE_API_ROOT, TEST_API_ROOT

CORRECTION_API_ENDPOINT = 'primecargo/stock-corrections/queue/'

class EdiStockCorrection(models.TransientModel):
    _name = 'edi.stock.correction'

    def check_primecargo_stock_corrections(self):
        company = self.env.user.company_id
        headers = {'Content-Type': 'application/json; charset=utf8',
                    'Authorization': 'Token {0}'.format(company.odoo_edi_token)}
        server = (LIVE_API_ROOT if company.edi_mode == "production" else TEST_API_ROOT) + CORRECTION_API_ENDPOINT

        result = requests.get(server, headers=headers)
        if self._create_inventory(result.json()):
            for entry in result.json():
                requests.patch(entry['url'], headers=headers, json={'status':'processed'})

    def _create_inventory(self, lines):
        new_lines = dict()
        for line in lines:
            if line['part_number'] in new_lines:
                new_lines[line['part_number']]['quantity_change'] += line['quantity_change']
            else:
                new_lines[line['part_number']] = {
                    'part_number': line['part_number'],
                    'barcode': line['barcode'],
                    'quantity_change': line['quantity_change']
                }

        return self.env['stock.inventory'].create({
            'filter': 'partial',
            'name': fields.Date.to_string(fields.Date.today()),
            'state': 'confirm',
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'line_ids': [(0, 0, self._create_inventory_line(line)) for index, line in new_lines.items()]
        })

    def _create_inventory_line(self, line):
        product = self.env['product.product'].search(['|',('barcode', '=', line['barcode']),('default_code', '=', line['part_number'])], limit=1)

        return {
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'product_uom_id': product.uom_id.id,
            'product_qty': product.qty_available + line['quantity_change']
        }

