import requests
import logging

_logger = logging.getLogger(__name__)

from odoo.addons.odoo_edi.models.edi_document import LIVE_API_ROOT, TEST_API_ROOT
from odoo import models, fields, api

AGREEMENT_ENDPOINT = "primecargo/agreements/"

class PrimecargoAgreement(models.TransientModel):
    _name = 'primecargo.agreement'
    _description = 'PrimeCargo WMS Agreement'

    def cron_check_credentials(self):
        company = self.env.user.company_id
        data = self._get_credentials(company)
        data = data[0] if len(data) > 0 else data
        if not data:  # data['ftp_username'] and not data['ftp_password']:
            self._post_credentials(company)
        elif data.get('ftp_username') != company.primecargo_username or data.get('ftp_password') != company.primecargo_password:
            self._patch_credentials(company, data['pk'])

    def _get_credentials(self, company):
        result = requests.get(self._server_address(company), headers=self._http_headers(company))
        if result.status_code == 200:
            return result.json()
        else:
            _logger.error('GET Request to FlexEDI ({0}) failed with status code {1}'.format(self._server_address(company), result.status_code))

    def _post_credentials(self, company):
        result = requests.post(self._server_address(company),
                               headers=self._http_headers(company),
                               json={'ftp_username': company.primecargo_username,
                                     'ftp_password': company.primecargo_password})
        if not result.status_code in [200, 201]:
            _logger.error('POST Request to FlexEDI ({0}) failed with status code {1}'.format(self._server_address(company), result.status_code))

    def _patch_credentials(self, company, patch_key):
        result = requests.patch(self._server_address(company) + str(patch_key) + '/',
                               headers=self._http_headers(company),
                               json={'ftp_username': company.primecargo_username,
                                     'ftp_password': company.primecargo_password})
        if not result.status_code in [200, 201]:
            _logger.error('PATCH Request to FlexEDI ({0}) failed with status code {1}'.format(self._server_address(company), result.status_code))

    def _http_headers(self, company):
        return {'Content-Type': 'application/json; charset=utf8',
                    'Authorization': 'Token {0}'.format(company.odoo_edi_token)}

    def _server_address(self, company):
        return (LIVE_API_ROOT if company.edi_mode == 'production' else TEST_API_ROOT) + AGREEMENT_ENDPOINT