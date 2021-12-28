from odoo import models, fields, api
import requests
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    primecargo_username = fields.Char()
    primecargo_password = fields.Char()
    primecargo_ownercode = fields.Char()
    primecargo_template_code = fields.Char()
    primecargo_shipping_product_id = fields.Many2one('product.primecargo.shipping', string="PrimeCargo Shipping Product", help="Contains the PrimeCargo Shipping Product Code as per agreement with PrimeCargo for this delivery")

    @api.model
    def _cron_update_primecargo_credentials(self):
        FlexEdiDocument = self.env['flexedi.document']
        for company in self.env['res.company'].search([('odoo_edi_token', '!=', False)]):
            current = False
            server_address = FlexEdiDocument._get_absolute_endpoint(endpoint='primecargo/agreements/', mode=company.edi_mode)
            token = company.odoo_edi_token
            headers = FlexEdiDocument._get_api_headers(token)

            response = requests.get(server_address, headers=headers)

            if response.status_code == 200:
                current = response.json()[0]
            if not current:
                # Create new
                current = {
                    'ftp_username': company.primecargo_username,
                    'ftp_password': company.primecargo_password
                }
                response = requests.post(server_address, headers=headers, json={
                    'ftp_username': current['ftp_username'],
                    'ftp_password': current['ftp_password'],
                })
                if not response.status_code in [200, 201]:
                    _logger.error('Unable to create PrimeCargo account credentials. Request returned status code {}'.format(response.status_code))
                    _logger.error(response.text)
            else:
                # Patch
                run_update = False
                if not current['ftp_username'] == company.primecargo_username:
                    current['ftp_username'] = company.primecargo_username
                    run_update = True
                if not current['ftp_password'] == company.primecargo_password:
                    current['ftp_password'] = company.primecargo_password
                    run_update = True
                if run_update:
                    server_address = FlexEdiDocument._get_absolute_endpoint(endpoint='primecargo/agreements/{}/'.format(current['id']), mode=company.edi_mode)
                    response = requests.patch(server_address, headers=headers, json={
                        'ftp_username': current['ftp_username'],
                        'ftp_password': current['ftp_password'],
                    })
                    if not response.status_code in [200, 201]:
                        _logger.error('Unable to update PrimeCargo account credentials. Request returned status code {}'.format(response.status_code))
                        _logger.error(response.text)
    