import json
from odoo import models, fields, api, _
from psycopg2 import OperationalError
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
import requests
import logging
import uuid
_logger = logging.getLogger(__name__)

LIVE_API_ROOT = "https://manage.flexedi.dk/api/"
TEST_API_ROOT = "https://manage.test.flexedi.dk/api/"

class FlexediDocument(models.AbstractModel):
    _name = 'flexedi.document'
    _description = 'FlexEDI Document'
    _order = 'create_date desc'

    def _get_document_states(self):
        return [
            ('pending', 'Waiting to be sent to VANS'),
            ('sent', 'Sent to VANS'),
            ('validated', 'Validated by VANS'),
            ('recieved', 'Recieved from VANS'),
            ('processed', 'Processing confirmed by client'),
            ('failed_internal', 'Document failed internally'),
            ('failed_vans', 'Document failed at VANS')
        ]

    def _get_endpoint_for_sending(self):
        return False

    def _get_document_endpoint(self):
        """
        Implemented by each inherited model
        Should return the direct endpoint for the currect document instance
        Fx: invoices/123/ where 123 is self.edi_id
        """
        return False

    @api.model
    def _get_absolute_endpoint(self, endpoint, mode='production'):
        """
        :param endpoint: Endpoint relative to the API root. fx invoices/ or invoices/pending/
        :param mode: Operational mode for EDI. Is either test or production
        :return str: String with absolute/full URL
        """
        return "{root}{endpoint}".format(
            root=LIVE_API_ROOT if mode == 'production' else TEST_API_ROOT,
            endpoint=endpoint
        )
    
    @api.model
    def _get_api_headers(self, token, **kwargs):
        """
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token {token}'.format(token=token)
        }
        for key in kwargs.keys():
            # Loop over any extra headers that we might need to give here
            headers[key] = kwargs[key]

        return headers

    state = fields.Selection(selection=_get_document_states, required=True, index=True, default='pending', ondelete='cascade')
    error = fields.Html(string='Document Error', help='The last error message that was returned from FlexEDI')
    blocking_level = fields.Selection(
        selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        help="Blocks the document current operation depending on the error severity :\n"
        "  * Info: Everything is fine, but there might be some relevant information for the user.\n"
        "  * Warning : The document has technically been processed, but there were some issues that the system has worked around.\n"
        "  * Error : The document was not properly processed due to some error.")
    document_format_id = fields.Many2one('flexedi.document.format', string='Document Format')
    company_id = fields.Many2one('res.company')
    partner_id = fields.Many2one('res.partner')
    edi_id = fields.Char(string="FlexEDI Document ID") # Technically this is an integer value, but since an integer field is always having a value, it will be 0 for False and 1 or more for True. By setting it as a Char, we can have a False value
    edi_uuid = fields.Char(string="Document Exchange ID")
    origin_document_edi_id = fields.Integer()
    request_data = fields.Text()
    response_data = fields.Text()

    def document_is_valid(self):
        self.ensure_one()
        return self.document_format_id.is_valid(self)

    @api.model
    def _cron_process_flexedi_documents(self, job_count=None):
        documents_to_send = self.search([('state', '=', 'pending'), ('edi_id', '=', False)])
        documents_processed = documents_to_send._process_flexedi_documents(job_count=job_count)
        documents_remaining = len(documents_to_send) - documents_processed

        if documents_remaining > 0:
            _logger.warning('Not all documents have been processed in one batch. Remaining {} documents will be processed in next batch'.format(documents_remaining))

    def _process_flexedi_documents(self, job_count=None, with_commit=True):
        documents = self[0:job_count or len(self)]
        if len(documents) == 0:
            _logger.warning('There are no documents to send')
            return False
        processed = []
        try:
            with self.env.cr.savepoint():
                self._cr.execute('SELECT * FROM {table} WHERE id IN %s FOR UPDATE NOWAIT'.format(table=self._table), [tuple(documents.ids)])
                for document in documents:
                    validation_result = document.document_is_valid()
                    rendered_error = False
                    if 'messages' in validation_result:
                        if len(validation_result['messages']):
                            error_lines = ''
                            for message in validation_result['messages']:
                                error_lines += '<li>{}</li>'.format(message)
                            rendered_error = '<ul>{}</ul>'.format(error_lines)
                    document.write({
                        'blocking_level': validation_result['error_state'],
                        'error': rendered_error or False
                    })
                    if not validation_result['error_state'] == 'error':
                        document.send_document()
                        processed.append(document.id)
                    else:
                        document.write({
                            'state': 'failed_internal',
                            'blocking_level': 'error'
                        })
        except OperationalError as e:
            if e.pgcode == '55P03':
                _logger.error('Another transaction is already having a lock on these documents. Cannot continue')
            else:
                raise e
        else:
            if with_commit and len(documents) > 1:
                self.env.cr.commit()
        
        if not len(documents) == len(processed):
            _logger.warning('One or more documents could not be processed. A total of {} documents were queued, but {} did complete'.format(len(documents), len(processed)))

        return len(processed)

    def send_document(self):
        # TODO: Describe how to implement send_document()
        if not self._get_endpoint_for_sending():
            raise ValidationError(_('Document does not support being sent'))
        self._send_document(self._get_endpoint_for_sending())

    def _send_document(self, endpoint):
        for record in self:
            company = record.company_id
            server_address = record._get_absolute_endpoint(endpoint=endpoint, mode=company.edi_mode)
            token = company.odoo_edi_token
            headers = record._get_api_headers(token)
            document = record.generate_document()
            record.write({
                'request_data': json.dumps(document, sort_keys=True, indent=4)
            })
            if company.edi_mode == 'development':
                # If runinng in development mode, we simply update the object and continue to the next document
                record.write({
                    'state': 'sent',
                    'error': '<p><strong>' + _('The system is running in DEVELOPMENT mode. This document has not actually been sent') + '</strong></p>',
                    'blocking_level': 'warning'
                })
                _logger.warning('Please note that documents are processed in DEVELOPMENT mode and data is therefore not sent to any server')
                continue
            else:
                # Send document to the specified server address
                result = requests.post(server_address, headers=headers, json=document)
                _logger.error(result.text)
                data = result.json()
                if result.status_code in [200, 201]:
                    record.write({
                        'response_data': json.dumps(data, sort_keys=True, indent=4),
                        'state': data['status'],
                        'edi_id': data['pk'],
                        'edi_uuid': data['uuid']
                    })
                elif result.status_code == 400:
                    # We have a Bad Request, which most likely is missing values or invalid values
                    # Errors come back as a dict
                    # {
                    #    'FIELD_NAME': [
                    #        'ERROR MESSAGE 1',
                    #        'ERROR MESSAGE 2',
                    #        'ERROR MESSAGE 3',
                    #        ...
                    #    ],
                    #    ...
                    # }
                    _logger.error(result.text)
                    errors = []
                    # NOTE: This could have been done as a double inline loop, but would have made the code to complex to understand
                    for field in result.json():
                        # TODO: Translate the field names from the API to field labels in Odoo to let the user understand what is wrong
                        errors.append(
                            "{key}:<br/>\n<ul>{messages}</ul>".format(
                                key=field,
                                messages="</li><li>".join([
                                    message for message in errors[field]
                                ])
                            )
                        )
                    record.write({
                        'response_data': json.dumps(data, sort_keys=True, indent=4),
                        'state': 'failed_internal',
                        'error': record.error + "<br/>\n".join(errors)
                    })
                else:
                    record.write({
                        'response_data': json.dumps(data, sort_keys=True, indent=4),
                        'state': 'failed_internal'
                    })

    def update_document_state(self, state):
        self.ensure_one()
        valid_states = {}
        for option in self._get_document_states():
            valid_states[option[0]] = option[1]

        if not state in valid_states:
            raise ValidationError(
                _('You are trying to the state to an invalid option of %s' % (state,))
            )
        
        if self._update_document(self._get_document_endpoint(), { 'status': state }):
            self.write({
                'state': state
            })

    def _update_document(self, endpoint, data):
        self.ensure_one()
        if not endpoint:
            return False
        company = self.company_id or self.env.user.company_id
        server_address = self._get_absolute_endpoint(endpoint=endpoint, mode=company.edi_mode)
        headers = self._get_api_headers(company.odoo_edi_token)
        response = requests.patch(server_address, headers=headers, json=data)
        if response.status_code == 200:
            return True
        else:
            return False

    def _requeue_document(self):
        self.ensure_one()
        endpoint = self._get_document_endpoint()
        if not endpoint:
            return False
        company = self.company_id or self.env.user.company_id
        server_address = self._get_absolute_endpoint(endpoint=endpoint + 'requeue/', mode=company.edi_mode)
        headers = self._get_api_headers(company.odoo_edi_token)
        response = requests.post(server_address, headers=headers)
        if response.status_code in [200, 202]:
            return True
        else:
            return False

    @api.model
    def _cron_get_status_update(self, job_count=None):
        for endpoint in self.env['flexedi.document.status.endpoint'].search([]):
            if not endpoint.model in self.env:
                _logger.error("Model %s does not exist in registry. Skipping endpoint %s" % (endpoint.model, endpoint.name))
                continue
            for company in self.env['res.company'].search([('odoo_edi_token', '!=', False)]):
                documents = self.env[endpoint.model].search([('state', 'in', ['pending', 'sent']), ('company_id', '=', company.id)], limit=job_count).mapped('edi_uuid')
                if len(documents) == 0:
                    _logger.warning('No documents require status updates for model %s in %s' % (endpoint.model, company.display_name))
                    continue
                server_address = self._get_absolute_endpoint(endpoint=endpoint.endpoint, mode=company.edi_mode)
                token = company.odoo_edi_token
                headers = self._get_api_headers(token)

                response = requests.get(server_address, headers=headers, json={
                    'document_ids': documents
                })
                if response.status_code == 200:
                    for document in response.json():
                        record = self.env[endpoint.model].search([('edi_uuid', '=', document['uuid'])], limit=1)
                        if record.state == document['status']:
                            # No changes since last update
                            # TODO: Sometimes a document does not get a state change for some time. We need to add a method to postpone next check
                            continue
                        record.write({
                            'state': document['status'],
                            'error': document['status_message'],
                            'blocking_level': 'error' if document['state'] in ['failed_internal' , 'failed_vans'] else record.blocking_level
                        })
                    self.env.cr.commit()
                elif response.status_code == 404:
                    _logger.error('The requested endpoint "{}" was not found'.format(server_address))
                elif response.status_code == 401:
                    _logger.error('The remote server responded with error code 401, which means that the credentials are not valid')
                else:
                    _logger.error('The remote server returned error code {} for endpoint "{}"'.format(response.status_code, server_address))
                    _logger.error(response.text)

    @api.model
    def _cron_receive_flexedi_documents(self, job_count=None):
        """
        This methods requests the given endpoint for each company. An ir.cron record must exist for each endpoint that should be checked
        """
        for endpoint in self.env['flexedi.document.reception.endpoint'].search([]):
            for company in self.env['res.company'].search([]):
                server_address = self._get_absolute_endpoint(endpoint=endpoint.endpoint, mode=company.edi_mode)
                token = company.odoo_edi_token
                headers = self._get_api_headers(token)
                response = requests.get(server_address, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    endpoint.process_documents_to_recieve(company, result)
                else:
                    _logger.error(response.text)
                



    @api.model_create_multi
    def create(self, vals_list):
        if type(vals_list) == list:
            for index, vals in enumerate(vals_list):
                if not 'company_id' in vals:
                    vals_list[index]['company_id'] = self.env.user.company_id.id
                if not 'edi_uuid' in vals:
                    vals_list[index]['edi_uuid'] = str(uuid.uuid4())
                
        elif type(vals_list) == dict:
            if not 'company_id' in vals_list:
                vals_list['company_id'] = self.env.user.company_id.id
            if not 'edi_uuid' in vals_list:
                vals_list['edi_uuid'] = str(uuid.uuid4())

        return super().create(vals_list)

    @api.model
    def format_monetary(self, amount: float, currency):
        # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
        # See https://github.com/odoo/odoo/blob/14.0/addons/account_edi_ubl/models/account_move.py
        return float_repr(amount, currency.decimal_places)

    def action_retry(self):
        for record in self:
            record.copy({
                'edi_uuid': str(uuid.uuid4()),
                'edi_id': False,
                'state': 'pending',
                'blocking_level': False,
                'error': False
            })

    def _document_post_reception_hook(self, document):
        pass