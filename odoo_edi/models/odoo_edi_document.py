# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging, json, requests, uuid
_logger = logging.getLogger(__name__)

API_ROOT = "https://api.b2bbackbone.com/api/"
LIVE_API_ROOT = "https://manage.flexedi.dk/api/"
TEST_API_ROOT = "https://manage.test.flexedi.dk/api/"

class EdiDocument(models.TransientModel):
    _name = 'odoo_edi.document'
    _description = 'Odoo EDI Document'

    def send_document(self, document, document_res, endpoint):
        self.validate_settings(document_res)
        settings = document_res.company_id if document_res.company_id.id else self.env.user.company_id
        server_address = "{}".format(LIVE_API_ROOT if settings.edi_mode == 'production' else TEST_API_ROOT) + endpoint
        token = settings.odoo_edi_token
        if not settings.edi_mode == 'development':
            headers = {
                'Content-Type': 'application/json; charset=utf8',
                'Authorization': 'Token {0}'.format(token)
            }
            result = requests.post(server_address, headers=headers, json=document)
            _logger.info(result.text)
            if not result.status_code in [200, 201]:
                document_res.write({
                    'edi_document_status': 'failed_internal',
                    'edi_document_status_message': result.json()
                })
            elif result.status_code in [200, 201]:
                document_res.write({
                    'edi_document_status': 'pending',
                    'edi_document_status_message': '',
                    'edi_document_guid': result.json()['uuid'],
                    'edi_document_id': result.json()['pk']
                })
        else:
            f = open('/tmp/' + document_res.name.replace('/','_') + '.json', 'w')
            f.write(json.dumps(document, ensure_ascii=False))
            f.close()
            document_res.write({
                'edi_document_status': 'pending',
                'edi_document_guid': str(uuid.uuid4()),
                'edi_document_id': document_res.id
            })
            _logger.info('odoo_edi is running in DEVELOPMENT mode and therefore nothing has been submitted to the servers. You can find your file in the /tmp directory')

    def recieve_document(self):
        raise UserError(_("The odoo_edi.document.recieve_document method is not implemented for this document type"))

    def create_edi(self, document):
        raise UserError(_("The odoo_edi.document.create_edi method is not implemented for this document type"))

    def validate_settings(self, document_res):
        company = document_res.company_id if document_res.company_id.id else self.env.user.company_id
        if not company.company_registry:
            raise UserError(_('The current company, %s, does not have a company registration number or GLN identification/number, which is required for EDI invoicing') % company.name)
        if not company.country_id:
            raise UserError(_('The current company, %s, does not have a country set. This is required for EDI') % company.name)
        if company.odoo_edi_token == "" or not company.odoo_edi_token:
            raise UserError(_('Please define the FlexEDI API Key before sending'))

    def cron_document_status(self):
        pass

