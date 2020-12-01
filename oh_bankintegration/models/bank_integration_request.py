# -*- coding: utf-8 -*-
import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from odoo.addons.oh_bankintegration.models.account_invoice import PAYMENT_STATUS_CODE
from collections import OrderedDict
from hashlib import sha256
import uuid
import array
import hmac
import base64
import json
import traceback
import requests
import logging
_logger = logging.getLogger(__name__)
BANKINTEGRATION_API_BASE_URL = 'https://api.bankintegration.dk'
ACCOUNT_STATEMENT_API_URL = BANKINTEGRATION_API_BASE_URL + '/report/account?requestId='
PAYMENT_API_URL = BANKINTEGRATION_API_BASE_URL + '/payment'
PAYMENT_STATUS_API_URL = BANKINTEGRATION_API_BASE_URL + '/status'


class BankIntegrationRequest(models.Model):
    _name = "bank.integration.request"
    _description = "Bank Integration Request"

    def _default_request_date(self):
        return datetime.datetime.now()

    request_id = fields.Char(string="Request Id")
    request_status = fields.Selection([
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('success', 'Success'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
        ('not_found', 'Not Found'),
        ('warning', 'Warning'),
        ('canceling', 'Canceling'),
        ('invalid_signature', 'Invalid Signature'),
    ], string='Request status', index=True, readonly=True, default='created')
    request_date = fields.Datetime(string='Request datetime', index=True, help="API Request date", default=_default_request_date, oldname='request_datetime')
    # invoice_id = fields.Many2one(
    #     'account.invoice', string='Payment Invoice', domain=[('type', '=', 'in_invoice')])
    invoice_ids = fields.Many2many('account.invoice', string='Invoices', domain=[('type', '=', 'in_invoice')])
    journal_id = fields.Many2one('account.journal', string='Journal')
    company_id = fields.Many2one('res.company', required=True)
    vendor_account = fields.Many2one(
        'res.partner.bank', string="Vendor Bank Account", ondelete='restrict', copy=False)
    bank_account = fields.Many2one(
        'res.partner.bank', string="Bank Account", ondelete='restrict', copy=False)
    fik_number = fields.Char(string="FIK Number", readonly=True)
    response_text = fields.Text(string="Response text")
    request_text = fields.Text(string="Request text")
    payment_id = fields.Char(string="Payment Id", default='')

    def set_request_id(self):
        for record in self:
            request_id = 'REQ_{company_id}_{timestamp}'.format(company_id=record.company_id.id, timestamp=datetime.datetime.now().timestamp())
            record.write({'request_id': request_id})

    def get_vendorbill_payment_token(self, payment_vals):
        self.ensure_one()
        try:
            # Get value to use as account number from journal
            acc_number = self.journal_id.get_bankintegration_acc_number()
            # Get integration code for the specific bank account
            customer_code = self.journal_id.customer_code

            if not acc_number:
                _logger.error('The account number could not be found')
                return False
            if not customer_code:
                _logger.error('The integration code for the journal on the bills could not be found')
                return False

            auth_dict = OrderedDict([
                ("serviceProvider", self.company_id.erp_provider),
                ("account", acc_number),
                ("time", self.request_date.strftime("%Y-%m-%dT%H:%M:%S")),
                ("requestId", self.request_id),
            ])
            hash_list = []

            for payment in payment_vals:
                auth_vals = OrderedDict([
                    ('token', sha256(str(customer_code).encode('utf-8')).hexdigest()),
                    ('custacc', acc_number),
                    ('currency', payment['currency']),
                    ('reqid', self.request_id),
                    ('paydate', payment.pop('paydate', '')),
                    ('amount', payment['amount']),
                    ('credacc', payment['account']),
                    ('erp', self.company_id.erp_provider),
                    ('payid', payment['paymentId']),
                    ('now', self.request_date.strftime("%Y%m%d%H%M%S")),
                ])
                auth_key = self.generate_auth_key(auth_vals)
                if auth_key:
                    hashed = OrderedDict([
                        ('id', payment['paymentId']),
                        ('hash', auth_key)
                    ])
                    hash_list.append(hashed)
                else:
                    _logger.error('Authentication key for bankintegration.dk could not be generated for {company}'.format(company=self.company_id.display_name))
                    return False
            auth_dict['hash'] = hash_list
            auth_obj = json.dumps(auth_dict)
            auth_obj = auth_obj.replace(" ", "")
            auth_header = base64.b64encode(auth_obj.encode('ascii')).decode()
            return auth_header
        except Exception:
            tb = traceback.format_exc()
            _logger.error('There was an error generating the Authentication token for bankintegration.dk for company {company}: {error}'.format(company=self.company_id.display_name, error=tb))

    def pay_invoice(self, vals, auth_header):
        self.ensure_one()
        _logger.info(vals)
        payment = OrderedDict([
            ('requestId', self.request_id),
            ('transactions', vals),
        ])
        payment['options'] = {
            'waitForBankResponse': self.company_id.check_payment_status,
            'checkPaymentStatus': self.company_id.check_payment_status,
            'moveToNextBankDate': True,
            'useIban': False,
            'skipDuplicateCheck': False
        }
        headers = {
            'Authorization': str('Basic ' + auth_header),
            'Content-type': 'application/json'
        }
        self.request_text = json.dumps(payment, sort_keys=True, indent=4)
        response = requests.post(
            PAYMENT_API_URL,
            verify=False,
            json=payment,
            headers=headers
        )
        self.response_text = response.text
        if response.status_code in [200, 201, 202, 204]:
            self.request_status = 'pending'
            for payment_data in vals:
                payment_id = payment_data['paymentId'].split('_')
                invoice = self.env['account.invoice'].search([('id', '=', payment_id[3])], limit=1, order='id desc')
                if invoice.id:
                    invoice.write({'payment_status': 'pending'})
            if self.company_id.check_payment_status:
                response_data = response.json()
                if 'answers' in response_data:
                    entries = response_data['answers']
                    for entry in entries:
                        self._update_invoice_payment_status(entry)
                else:
                    _logger.warn('There were no status updates in the response although it was specified that these should be delivered')
        else:
            _logger.error(response.text)
            self.request_status = 'failed'
            for invoice in self.invoice_ids:
                invoice.write({
                    'payment_status': 'failed',
                    'payment_error': 'There was an error processing the payment. Please check that the payment details are filled correctly'
                })

        return True

    
    def get_bank_statement_token(self):
        self.ensure_one()
        try:
            # Get value to use as account number from journal
            acc_number = self.journal_id.get_bankintegration_acc_number()
            # Get integration code for the specific bank account
            customer_code = self.journal_id.customer_code
            
            auth_vals = OrderedDict([
                ('token', sha256(str(customer_code).encode('utf-8')).hexdigest()),
                ('custacc', acc_number),
                ('currency', ''),
                ('reqid', self.request_id),
                ('paydate', ''),
                ('amount', ''),
                ('credacc', ''),
                ('erp', self.company_id.erp_provider),
                ('payid', self.payment_id or self.request_id),
                ('now', self.request_date.strftime("%Y%m%d%H%M%S")),
            ])
            auth_key = self.generate_auth_key(auth_vals)
            if auth_key:
                auth_dict = OrderedDict([
                    ("serviceProvider", self.company_id.erp_provider),
                    ("account", acc_number),
                    ("time", self.request_date.strftime("%Y-%m-%dT%H:%M:%S")),
                    ("requestId", self.request_id),
                    ("hash", [
                        OrderedDict([
                            ("id", self.payment_id or self.request_id),
                            ("hash", auth_key)
                        ])
                    ]),
                ])
                auth_obj = json.dumps(auth_dict)
                auth_obj = auth_obj.replace(" ", "")
                auth_header = base64.b64encode(auth_obj.encode('ascii')).decode()
                return auth_header
            else:
                _logger.error('Authentication key for bankintegration.dk could not be generated for {company}'.format(company=self.company_id.display_name))
                return False
        except Exception:
            tb = traceback.format_exc()
            _logger.error('There was an error generating the Authentication token for bankintegration.dk for company {company}: {error}'.format(company=self.company_id.display_name, error=tb))

    def generate_auth_key(self, auth_vals_dict):
        try:
            erp_key = self.company_id.bi_api_key
            payload_raw = "#".join(str(v) for v in auth_vals_dict.values())
            erp_uuid = uuid.UUID(hex=erp_key)
            map_arr = array.array('B', erp_uuid.bytes_le)
            payload = bytes(payload_raw, 'utf-8')
            dig = hmac.new(map_arr.tobytes(), payload, sha256).digest()
            encodedSignature = base64.b64encode(dig).decode()
            return encodedSignature
        except Exception as e:
            _logger.error('Auth Key Generation Error: %s', str(e))
        return False

    def get_bank_statements(self, auth_header, last_bank_statement, is_scheduler=False):
        errors = []
        bank_statement = {
            'from_date': last_bank_statement.date,
            'to_date': (datetime.datetime.today() - datetime.timedelta(days=1)).date()
        }
        transactions = []
        # Store the current balance as per the last transaction, as we need to set this on the statement in the end
        current_balance_amount = round(last_bank_statement.balance_end_real, 2)
        # Store a balance, which starts the same as the current_balance_amount, but here all transaction amounts are
        # added together so that we can check in the end if one or more transactions have been missed
        running_balance = current_balance_amount
        data, errors = self.get_bank_statement_data_from_bankintegration_api(auth_header, last_bank_statement.date, last_bank_statement.balance_end_real)
        if errors:
            if is_scheduler:
                return bank_statement, errors
            else:
                raise ValidationError("\n".join(errors))
        if data:
            # Assign a variable to control the loop
            balance_matches = False
            retry_attempts = 0
            while(not balance_matches):
                # Check if retry attemps are above 5
                if retry_attempts > 5:
                    _logger.error('Max retries exceeded for automation to try and get any missing transactions. User/Administrator has to handle the issue manually')
                    break
                # Assign the current_balance_amount to a different variable so that we can modify it and keep track of the balance
                last_statement_balance_amount = current_balance_amount
                if 'entries' in data:
                    lines = data['entries']
                    if len(lines) > 0:
                        transaction = lines[0]
                        current_running_balance = round(transaction['balance'], 2)
                        running_balance = current_balance_amount
                        if round(last_statement_balance_amount + transaction['amount'], 2) == current_running_balance:
                            # If the balances match, then we can continue
                            balance_matches = True
                            _logger.info('Balances are matching. Now importing')
                        else:
                            retry_attempts += 1
                            _logger.warn('There is a difference between the reported ending balance and the balance computed. Reported ending balance as of last transaction: {ending}. Computed balance as of last transaction: {last}'.format(ending=round(last_statement_balance_amount + transaction['amount'], 2), last=current_running_balance))
                            self.set_request_id()
                            self.request_date = datetime.datetime.now()
                            auth_header = self.get_bank_statement_token()
                            last_bank_statement = self.env['account.bank.statement'].search([('journal_id', '=', self.journal_id.id), ('date', '<', last_bank_statement.date)], limit=1, order='date desc')
                            if not last_bank_statement.id:
                                _logger.error('No previous bank statements could be found')
                                break
                            # Store the current balance as per the last transaction, as we need to set this on the statement in the end
                            current_balance_amount = round(last_bank_statement.balance_end_real, 2)
                            bank_statement = {
                                'from_date': last_bank_statement.date,
                                'to_date': (datetime.datetime.today() - datetime.timedelta(days=1)).date()
                            }
                            data, errors = self.get_bank_statement_data_from_bankintegration_api(auth_header, last_bank_statement.date, last_bank_statement.balance_end_real)
                    else:
                        break
                else:
                    # If no entries are there, then we break the loop and let the exception handling run
                    break
            if data['requestId'] == str(self.request_id):
                if data['currency'] and data['entries']:
                    # TODO: Validate if we are missing any entries
                    from_date = datetime.datetime.strptime(data['from'], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')
                    to_date = datetime.datetime.strptime(data['to'], '%Y-%m-%dT%H:%M:%S').strftime('%d-%m-%Y')
                    bank_statement = {
                        'account': data['account'],
                        'currency': data['currency'],
                        'from_date': from_date,
                        'to_date': to_date,
                        'statement': []
                    }
                    use_last_entry_date_as_statement_date = self.company_id.use_last_entry_date_as_statement_date
                    bankintegration_transaction_accounting_date = self.company_id.bankintegration_transaction_accounting_date
                    statement = {
                        'name': _('Bank statement from ' + from_date + ' to ' + to_date),
                        'balance_start': current_balance_amount,
                        'balance_end_real': 0,
                        'date': datetime.datetime.strptime(data['to'].split('T')[0], '%Y-%m-%d') if use_last_entry_date_as_statement_date else datetime.datetime.strptime(data['created'].split('T')[0], '%Y-%m-%d'), # Only the date from the timestamp
                        'transactions': [],
                    }
                    if 'entries' in data:
                        lines = data['entries']
                        for transaction in lines:
                            vals = {
                                'unique_import_id': "{account}_{id}".format(id=transaction['id'], account=data['account']),
                                'name': transaction['advis'][0] if self.company_id.use_note_msg else transaction['text'],
                                'date': datetime.datetime.strptime(transaction['date'][bankintegration_transaction_accounting_date], '%Y-%m-%dT%H:%M:%S'),
                                'amount': transaction['amount'],
                                'note': "\n".join(transaction['advis']) if 'advis' in transaction else '',
                                'json_log': json.dumps(transaction, sort_keys=True, indent=4)
                            }
                            # Validate if starting and ending balance matches
                            if round(transaction['balance'], 2) == round(current_balance_amount + transaction['amount'], 2):
                                running_balance = round(running_balance + transaction['amount'], 2)
                                current_balance_amount = round(transaction['balance'], 2)
                            else:
                                errors.append(_('The current account balance and balance for transaction do not match'))
                                _logger.error('The transaction {transaction_id} has a balance of {transaction_balance}, which is not the same as the current balance of {current_balance}'.format(transaction_id=transaction['id'], transaction_balance=transaction['balance'], current_balance=current_balance_amount + transaction['amount']))
                                break                                
                            # TODO: Next we need to try and locate the partner on the transaction
                            transactions.append(vals)
                        current_balance_amount = round(current_balance_amount, 2)
                        running_balance = round(running_balance, 2)
                        if not current_balance_amount == running_balance:
                            _logger.warn('There is a difference between the reported ending balance and the balance computed. Reported ending balance as of last transaction: {ending}. Computed balance as of last transaction: {last}'.format(ending=current_balance_amount, last=running_balance))
                            errors.append(_('There is a difference between the reported ending balance and the balance computed. Reported ending balance as of last transaction: %s. Computed balance as of last transaction: %s' % (current_balance_amount, running_balance)))
                        statement['transactions'] = transactions
                        statement['balance_end_real'] = current_balance_amount
                        bank_statement['statement'] = [statement]
                    else:
                        _logger.warn('There are no transactions for journal {journal} in company {company} for period {from_date} - {to_date}'.format(journal=self.journal_id.name, company=self.company_id.display_name, from_date=from_date, to_date=to_date))
                        errors.append(_('There are no transactions for period %s - %s' % (from_date, to_date)))
            else:
                errors.append(_('The request ID of the returned bank statement does not match the request ID that we generated. Something is wrong and you might need to contact support if the issue persists'))
        else:
            errors.append(_('No bank statements have been returned'))
        self.request_status = 'success'
        if is_scheduler:
            return bank_statement, errors
        else:
            if not errors:
                return bank_statement, errors
            else:
                raise ValidationError("\n".join(errors))

    def get_bank_statement_data_from_bankintegration_api(self, auth_header, last_import_date, last_import_balance):
        response_data = {}
        errors = []
        next_import_date = datetime.datetime.today() - datetime.timedelta(days=1)
        use_last_entry_date_as_statement_date = self.company_id.use_last_entry_date_as_statement_date
        # Some users prefer to have the bank statement be on the same date as the last transaction of the statement
        # This we therefore configure the system to handle by modifying the date where we import from
        if use_last_entry_date_as_statement_date:
            last_import_date = last_import_date + datetime.timedelta(days=1)
        use_extended_import = self.company_id.use_extended_import
        bankintegration_api_url = ACCOUNT_STATEMENT_API_URL + \
            str(self.request_id) + '&from=' + \
            last_import_date.strftime('%Y-%m-%d') + '&to=' + next_import_date.strftime('%Y-%m-%d')
        if use_extended_import:
            bankintegration_api_url = bankintegration_api_url + '&type=Full'
        try:
            headers = {
                'Authorization': str('Basic ' + auth_header),
                'Content-type': 'application/json'
            }
            self.request_text = json.dumps(headers, sort_keys=True, indent=4)
            response = requests.get(
                bankintegration_api_url,
                verify=False,
                headers=headers,
            )
            self.response_text = response.text
            if response.status_code == 200:
                response_data = response.json()
                entries = response_data['entries']
                for entry in entries:
                    entry.update({'payment_type': entry['type']})
                    if use_extended_import:
                        entry.update(entry['amounts'])
                        del entry['amounts']
                    else:
                        advice_msg = False
                        transaction_type = ''
                        if 'creditorText' in entry:
                            transaction_type = 'Credit'
                            if 'creditorMessage' in entry:
                                advice_msg = entry['creditorMessage']
                        elif 'debtorText' in entry:
                            transaction_type = 'Debit'
                            if 'debtorMessage' in entry:
                                advice_msg = entry['debtorMessage']
                        entry.update({'type': transaction_type})
                        entry.update({'advis': [advice_msg] if advice_msg else []})
            elif response.status_code == 401:
                error_msg = _('There was an authentication error when trying to get the bank statements. Please make sure that you bank account number and integration code are correct and try again')
                _logger.error(error_msg)
                errors.append(error_msg)
            else:
                error_msg = _('There was an error communicating with bankintegration.dk. Bankintegration.dk responded with error code %s' % response.status_code)
                _logger.error(error_msg)
                errors.append(error_msg)
        except Exception:
            tb = traceback.format_exc()
            _logger.error('There was an error fetching bank statements from bankintegration.dk: {}'.format(tb))
            errors.append(_('There was an error fetching bank statements from bankintegration.dk. Details have been saved in your Odoo serverlogs. Please contact support if the issue persists'))
        _logger.info(errors)
        return response_data, errors


    def cron_bankintegration_payment_status(self):
        for company in self.env['res.company'].search([]):
            # Validate if we should even process data for this company
            if not company.has_valid_bankintegration_config():
                continue
            # Validate if we can even process payments out of the payment journal configured on the company
            if not company.payment_journal.has_valid_bankintegration_config():
                continue
            # Get the status of any payments that have not yet been processed
            pending_requests = self.search([('company_id', '=', company.id), ('request_status', 'in', [PAYMENT_STATUS_CODE['1'], PAYMENT_STATUS_CODE['2'], PAYMENT_STATUS_CODE['4'], PAYMENT_STATUS_CODE['128']])])
            if not pending_requests.ids:
                _logger.warn('No payments to check')
                continue
            request = self.create({
                'company_id': company.id
            })
            request.set_request_id()
            auth_header = request.get_payment_status_token()
            if auth_header:
                request.update_payment_status(auth_header, pending_requests)
            else:
                _logger.error('It was not possible to generate the Authentication header for communication with bankintegration.dk')

    def get_payment_status_token(self):
        try:
            # Get value to use as account number from journal
            acc_number = self.company_id.payment_journal.get_bankintegration_acc_number()
            # Get integration code for the specific bank account
            customer_code = self.company_id.payment_journal.customer_code
            
            auth_vals = OrderedDict([
                ('token', sha256(str(customer_code).encode('utf-8')).hexdigest()),
                ('custacc', acc_number),
                ('currency', ''),
                ('reqid', self.request_id),
                ('paydate', ''),
                ('amount', ''),
                ('credacc', ''),
                ('erp', self.company_id.erp_provider),
                ('payid', self.request_id),
                ('now', self.request_date.strftime("%Y%m%d%H%M%S")),
            ])
            auth_key = self.generate_auth_key(auth_vals)
            if auth_key:
                auth_dict = OrderedDict([
                    ("serviceProvider", self.company_id.erp_provider),
                    ("account", acc_number),
                    ("time", self.request_date.strftime("%Y-%m-%dT%H:%M:%S")),
                    ("requestId", self.request_id),
                    ("hash", [
                        OrderedDict([
                            ("id", self.request_id),
                            ("hash", auth_key)
                        ])
                    ]),
                ])
                auth_obj = json.dumps(auth_dict)
                auth_obj = auth_obj.replace(" ", "")
                auth_header = base64.b64encode(auth_obj.encode('ascii')).decode()
                return auth_header
            else:
                _logger.error('Authentication key for bankintegration.dk could not be generated for {company}'.format(company=self.company_id.display_name))
                return False
        except Exception:
            tb = traceback.format_exc()
            _logger.error('There was an error generating the Authentication token for bankintegration.dk for company {company}: {error}'.format(company=self.company_id.display_name, error=tb))

    def update_payment_status(self, auth_header, pending_requests):
        self.ensure_one()
        pending_payment_ids = []
        for request in pending_requests:
            for invoice in request.invoice_ids:
                pending_payment_ids.append(invoice.payment_id)
        vals = {
            'requestId': self.request_id,
            'paymentId': pending_payment_ids
        }
        headers = {
            'Authorization': str('Basic ' + auth_header),
            'Content-type': 'application/json'
        }
        self.request_text = json.dumps(vals, sort_keys=True, indent=4)
        response = requests.post(
            PAYMENT_STATUS_API_URL,
            verify=False,
            headers=headers,
            json=vals
        )
        self.response_text = response.text
        if response.status_code == 200:
            response_data = response.json()
            if response_data['requestId'] == self.request_id:
                entries = response_data['answers'] or False
                if entries:
                    for entry in entries:
                        self._update_invoice_payment_status(entry)
                else:
                    _logger.warn('There were no entries in the data returned from bankintegration.dk')
                # Allow other modules to work with the returned data, we call this method
                self._process_response_data(response.json())
            else:
                _logger.error('The Request ID of the returned payment status data does not match the Request ID in the data that was sent to query the payment status')
        else:
            _logger.error('There was an error getting payment status from bankintegration.dk. Error code {code}'.format(code=response.status_code))
            _logger.error(response.text)

    def _process_response_data(self, response_data):
        # Just return something for other methods to override
        return response_data

    def _update_invoice_payment_status(self, status_update):
        invoice = self.env['account.invoice'].search([('payment_id', '=', status_update['paymentId'])], limit=1, order='id desc')
        if not invoice.id:
            # In case that we cannot find the payment ID, we might still be in a transaction where the payment Id is not yet committed
            # so we instead make the lookup based on the invoice ID
            payment_data = status_update['paymentId'].split('_')
            # In case some old payment comes back, where it was made using oh_bankintegration 1.x version
            if len(payment_data) == 1:
                try:
                    payment_data[0] = int(payment_data[0])
                except:
                    _logger.error('Could not convert paymentId {} to int. Giving up'.format(payment_data[0]))
                    return False
                invoice = self.env['account.invoice'].search([('id', '=', payment_data[0])], limit=1, order='id desc')
            # New way where are more descriptive paymentID is made
            else:
                invoice = self.env['account.invoice'].search([('id', '=', payment_data[3])], limit=1, order='id desc')
            if not invoice.id:
                _logger.error('The PaymentID {} was not found'.format(status_update['paymentId']))
                return False
        request = self.search([('request_id', '=', invoice.request_id)], limit=1)
        if not request.id:
            _logger.warn('No request with request ID {} was found. Skipping'.format(invoice.request_id))
        request.write({'request_status': PAYMENT_STATUS_CODE[str(status_update['status'])]})
        vals = {
            'payment_status':PAYMENT_STATUS_CODE[str(status_update['status'])]
        }
        if 'errors' in status_update:
            errors = status_update['errors']
            vals['payment_error'] = "\n".join(["{code}: {text}".format(code=error['code'] if 'code' in error else '', text=error['text']) for error in errors])
        elif 'warnings' in status_update:
            warnings = status_update['warnings']
            vals['payment_error'] = "\n".join(["{code}: {text}".format(code=warning['code'] if 'code' in warning else '', text=warning['text']) for warning in warnings])
        invoice.write(vals)
        return True