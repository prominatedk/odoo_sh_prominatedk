# -*- coding: utf-8 -*-
import hashlib
import re
import time
import hmac
import base64
import uuid
import array
from time import strftime
import datetime
from collections import OrderedDict
import json
import requests
import ast
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

#CUSTOMER_CODE = 'kgDc%IdjLIa7uS9F'
#PAYMENT_API_BASE_URL = 'https://api-debug.bankintegration.dk'
PAYMENT_API_BASE_URL = 'https://api.bankintegration.dk'
PAYMENT_API_URL = PAYMENT_API_BASE_URL + '/payment'
PAYMENT_STATUS_API_URL = PAYMENT_API_BASE_URL + '/status?requestId='
ACCOUNT_STATEMENT_API_URL = PAYMENT_API_BASE_URL + '/report/account?requestId='

PAYMENT_STATUS_CODE = {
    '1': 'created',
    '2': 'pending',
    '4': 'accepted',
    '8': 'success',
    '16': 'rejected',
    '32': 'failed',
    '64': 'not_found',
    '128': 'warning',
    '256': 'canceling',
}


class AccountInvoice(models.Model):
    _name = "account.invoice"
    _inherit = ["account.invoice"]

    payment_status = fields.Selection([
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('success', 'Success'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
        ('not_found', 'Not Found'),
    ], string='Payment status', index=True)
    payment_duedate = fields.Date(
        string='Payment date', index=True, help="Due date for payment")
    payment_autopay = fields.Boolean(
        string='Auto pay', default=False, help="If this is set our scheduler automatic make payment")
    payment_journal = fields.Many2one(
        'account.journal', string='Payment journal', domain=[('type', '=', 'bank')])
    payment_reference = fields.Char(string='Payment Reference')
    payment_error = fields.Char(string='Payment Error')
    request_id = fields.Char(string="Request id")
    payment_id = fields.Char(string="Payment id")
    payment_count = fields.Integer(string="Payment count", default=0)
    fik_number = fields.Char(string="FIK Number", default='')

    @api.model
    def create(self, vals):
        payment_margin = self.env[
            'ir.config_parameter'].sudo().get_param('payment_margin')
        payment_autopay = self.env[
            'ir.config_parameter'].sudo().get_param('autopay')
        payment_journal = self.env.user.company_id.payment_journal.id
        if payment_autopay == 'True':
            vals['payment_autopay'] = True
        if payment_journal:
            vals['payment_journal'] = payment_journal
        if vals.get('date_due', False) and not vals.get('payment_duedate', False):
            if payment_margin:
                try:
                    payment_duedate = datetime.datetime.strptime(vals.get(
                        'date_due'), "%Y-%m-%d").date() + datetime.timedelta(days=int(payment_margin))
                except:
                    payment_duedate = vals.get(
                        'date_due') + datetime.timedelta(days=int(payment_margin))
            else:
                payment_duedate = vals.get('date_due')
            vals['payment_duedate'] = payment_duedate
        invoice = super(AccountInvoice, self).create(vals)
        return invoice

    @api.multi
    def write(self, vals):
        payment_margin = self.env[
            'ir.config_parameter'].sudo().get_param('payment_margin')
        if vals.get('date_due', False) and not vals.get('payment_duedate', False):
            if payment_margin:
                try:
                    payment_duedate = datetime.datetime.strptime(vals.get(
                        'date_due'), "%Y-%m-%d").date() + datetime.timedelta(days=int(payment_margin))
                except:
                    payment_duedate = vals.get(
                        'date_due') + datetime.timedelta(days=int(payment_margin))
            else:
                payment_duedate = vals.get('date_due')
            vals['payment_duedate'] = payment_duedate
        invoice = super(AccountInvoice, self).write(vals)
        return invoice

    @api.model
    def get_bankintegration_settings(self):
        erp_key = ''
        customer_code = ''
        try:
            erp_key = self.env[
                'ir.config_parameter'].sudo().get_param('bi_api_key')
            payment_journal_id = self.env[
                'ir.config_parameter'].sudo().get_param('payment_journal')
            if payment_journal_id:
                account_model = self.env['account.journal']
                payment_journal = account_model.browse(int(payment_journal_id))
                if payment_journal.customer_code:
                    customer_code = payment_journal.customer_code
        except Exception as e:
            _logger.debug('Some Error: %s', str(e))
        return erp_key, customer_code

    @api.model
    def generate_auth_key(self, auth_vals_dict):
        try:
            erp_key = self.env[
                'ir.config_parameter'].sudo().get_param('bi_api_key')
            payload_raw = "#".join(str(v) for v in auth_vals_dict.values())
            #print ('payload_raw-----------',payload_raw)
            erp_uuid = uuid.UUID(hex=erp_key)
            map_arr = array.array('B', erp_uuid.bytes_le)
            payload = bytes(payload_raw, 'utf-8')
            #print ('payload-----------',payload)
            dig = hmac.new(map_arr.tobytes(), payload, hashlib.sha256).digest()
            encodedSignature = base64.b64encode(dig).decode()
            return encodedSignature
        except Exception as e:
            print('Auth Key Generation Error: ', str(e))
        return False

    @api.multi
    def generate_payment_json_old(self, invoice_id):
        # Scheduler code will be added here
        set_validate_payment = self.env[
            'ir.config_parameter'].sudo().get_param('set_validate_payment')
        if isinstance(set_validate_payment, str):
            set_validate_payment = ast.literal_eval(set_validate_payment)
        duedate = None
        if invoice_id:
            invoice_model = self.env['account.invoice']
            payment_invoice = invoice_model.browse(invoice_id)
            if payment_invoice.payment_duedate:
                duedate = payment_invoice.payment_duedate
            elif payment_invoice.date_due:
                duedate = payment_invoice.date_due
            if duedate:
                if duedate < datetime.datetime.today().date():
                    duedate = datetime.datetime.today().date()
                pay_date = duedate.strftime("%Y%m%d")
                paymentDate = duedate.strftime("%Y-%m-%d")
        if duedate:
            try:
                ERP_PROVIDER = self.env[
                    'ir.config_parameter'].sudo().get_param('erp_provider')
                utc_datetime = datetime.datetime.utcnow()
                request_model = self.env['bank.integration.request']
                request_obj = request_model.create(
                    {'invoice_id': invoice_id, 'request_datetime': utc_datetime})
                request_datetime = request_obj.request_datetime
                request_datetime = request_datetime.strftime(
                    "%Y-%m-%d %H:%M:%S")
                request_datetime_obj = datetime.datetime.strptime(
                    request_datetime, '%Y-%m-%d %H:%M:%S')
                if not set_validate_payment:
                    pay_date = request_datetime_obj.strftime("%Y%m%d")
                    paymentDate = request_datetime_obj.strftime("%Y-%m-%d")
                now_date = request_datetime_obj.strftime("%Y%m%d%H%M%S")
                time_format = request_datetime_obj.strftime(
                    "%Y-%m-%dT%H:%M:%S")
                invoice_model = self.env['account.invoice']
                payment_invoice = invoice_model.browse(invoice_id)
                amount = 0
                transactions = []
                vendor_account_number = ''
                request_obj_vals = {}
                vendor_account_id = 0
                customer_account = ''
                customer_account_id = 0
                request_id = request_obj.request_id
                total_request_amount = 0
                if payment_invoice:
                    amount = payment_invoice.residual
                    total_request_amount += amount
                    vendor_banks = self.env['res.partner.bank'].search(
                        [('partner_id', '=', payment_invoice.partner_id.id)], order='id', limit=1)
                    vals = OrderedDict()
                    paymentId = str(invoice_id)
                    if payment_invoice.payment_count:
                        paymentId = paymentId + 'OH' + \
                            str(payment_invoice.payment_count)
                    vals['paymentId'] = paymentId
                    vals['paymentDate'] = paymentDate
                    vals['amount'] = "%.2f" % amount
                    vals['currency'] = payment_invoice.currency_id.name
                    payment_ref = payment_invoice.payment_reference if payment_invoice.payment_reference else payment_invoice.reference
                    if not payment_ref:
                        payment_ref = payment_invoice.company_id.name
                    vals['text'] = payment_invoice.number + \
                        ' ' + payment_invoice.partner_id.name
                    creditor_info = OrderedDict()
                    creditor_info['name'] = payment_invoice.partner_id.name
                    vals['creditorText'] = payment_ref
                    vals['urgency'] = 1
                    if payment_invoice.fik_number:
                        fik_number = payment_invoice.fik_number
                        vals['account'] = fik_number
                        vendor_account_number = fik_number
                        request_obj_vals.update({'fik_number': fik_number})
                    elif vendor_banks:
                        if isinstance(vendor_banks, list):
                            vendor_bank = vendor_banks[0]
                        else:
                            vendor_bank = vendor_banks
                        if vendor_bank.bankintegration_acc_number:
                            vendor_account_number = vendor_bank.bankintegration_acc_number
                        else:
                            vendor_account_number = vendor_bank.get_bban() if callable(
                                getattr(vendor_bank, "get_bban", None)) and vendor_bank.acc_type == 'iban' else vendor_bank.sanitized_acc_number
                        vals['account'] = vendor_account_number
                        vals['vendor_account'] = vendor_bank.id
                        vendor_account_id = vendor_bank.id
                        request_obj_vals.update(
                            {'vendor_account': vendor_account_id})
                        if vendor_bank.bank_id and vendor_bank.bank_id.bic:
                            if not vendor_bank.bankintegration_acc_number:
                                creditor_info['bic'] = vendor_bank.bank_id.bic
                                vals['type'] = 11

                    vals['creditor'] = creditor_info
                    transactions.append(vals)

                    if payment_invoice.payment_journal.bank_account_id.bankintegration_acc_number:
                        customer_account = payment_invoice.payment_journal.bank_account_id.bankintegration_acc_number
                    else:
                        customer_account = payment_invoice.payment_journal.bank_account_id.get_bban() if callable(getattr(
                            payment_invoice.payment_journal.bank_account_id, "get_bban", None)) and payment_invoice.payment_journal.bank_account_id.acc_type == 'iban' else payment_invoice.payment_journal.bank_account_id.sanitized_acc_number
                    customer_account_id = payment_invoice.payment_journal.bank_account_id.id
                    vals['bank_account'] = customer_account_id
                    request_obj_vals.update(
                        {'bank_account': customer_account_id, 'payment_id': paymentId})

                    if transactions and total_request_amount:
                        customer_code = payment_invoice.payment_journal.customer_code
                        #print('customer_code', customer_code)
                        auth_vals = OrderedDict()
                        auth_vals['token'] = hashlib.sha256(
                            customer_code.encode('utf-8')).hexdigest()
                        auth_vals['custacc'] = customer_account
                        auth_vals[
                            'currency'] = payment_invoice.currency_id.name
                        auth_vals['reqid'] = request_id
                        auth_vals['paydate'] = pay_date
                        auth_vals['amount'] = "%.2f" % amount
                        auth_vals['credacc'] = vendor_account_number
                        auth_vals['erp'] = ERP_PROVIDER
                        auth_vals['payid'] = paymentId
                        auth_vals['now'] = now_date
                        request_obj.write(request_obj_vals)
                        #print('auth_vals', auth_vals)
                        auth_key = self.generate_auth_key(auth_vals)
                        if auth_key:
                            hashed = OrderedDict()
                            hashed["id"] = paymentId
                            hashed["hash"] = auth_key

                            auth_dict = OrderedDict()
                            auth_dict["serviceProvider"] = ERP_PROVIDER
                            auth_dict["account"] = customer_account
                            auth_dict["time"] = time_format
                            auth_dict["requestId"] = request_id
                            auth_dict["hash"] = [hashed]
                            #print('auth_dict', auth_dict)
                            auth_obj = json.dumps(auth_dict)
                            auth_header = base64.b64encode(
                                auth_obj.encode()).decode()
                            #print('Auth Header', auth_header)
                            # print('-------------------------')
                            #print('Auth auth_obj', auth_obj)
                            # print('-------------------------')
                            #print('Auth transactions', transactions)
                            return [auth_header, request_id, transactions]

            except Exception as e:
                print('Generate Payment Json Error: ', str(e))
        return [False, False, False]

    @api.multi
    def generate_payment_json(self, invoice_id, utc_datetime):
        vals = {}
        # Scheduler code will be added here
        set_validate_payment = self.env[
            'ir.config_parameter'].sudo().get_param('set_validate_payment')
        ERP_PROVIDER = self.env[
            'ir.config_parameter'].sudo().get_param('erp_provider')
        if isinstance(set_validate_payment, str):
            set_validate_payment = ast.literal_eval(set_validate_payment)
        duedate = None
        if invoice_id:
            invoice_model = self.env['account.invoice']
            payment_invoice = invoice_model.browse(invoice_id)
            if payment_invoice.payment_duedate:
                duedate = payment_invoice.payment_duedate
            elif payment_invoice.date_due:
                duedate = payment_invoice.date_due
            if duedate:
                if duedate < datetime.datetime.today().date():
                    duedate = datetime.datetime.today().date()
                pay_date = duedate.strftime("%Y%m%d")
                paymentDate = duedate.strftime("%Y-%m-%d")
        if duedate:
            try:
                request_datetime = utc_datetime.strftime(
                    "%Y-%m-%d %H:%M:%S")
                request_datetime_obj = datetime.datetime.strptime(
                    request_datetime, '%Y-%m-%d %H:%M:%S')
                if not set_validate_payment:
                    pay_date = request_datetime_obj.strftime("%Y%m%d")
                    paymentDate = request_datetime_obj.strftime("%Y-%m-%d")
                now_date = request_datetime_obj.strftime("%Y%m%d%H%M%S")
                time_format = request_datetime_obj.strftime(
                    "%Y-%m-%dT%H:%M:%S")
                invoice_model = self.env['account.invoice']
                payment_invoice = invoice_model.browse(invoice_id)
                amount = 0
                transactions = []
                vendor_account_number = ''
                request_obj_vals = {}
                vendor_account_id = 0
                customer_account = ''
                customer_account_id = 0
                total_request_amount = 0
                if payment_invoice:
                    amount = payment_invoice.residual
                    total_request_amount += amount
                    vendor_banks = self.env['res.partner.bank'].search(
                        [('partner_id', '=', payment_invoice.partner_id.id)], order='id', limit=1)
                    paymentId = str(invoice_id)
                    if payment_invoice.payment_count:
                        paymentId = paymentId + 'OH' + \
                            str(payment_invoice.payment_count)
                    vals['paymentId'] = paymentId
                    vals['invoice_id'] = invoice_id
                    vals['paymentDate'] = paymentDate
                    vals['amount'] = "%.2f" % amount
                    vals['currency'] = payment_invoice.currency_id.name
                    payment_ref = payment_invoice.payment_reference if payment_invoice.payment_reference else payment_invoice.reference
                    if not payment_ref:
                        payment_ref = payment_invoice.company_id.name
                    vals['text'] = payment_invoice.number + \
                        ' ' + payment_invoice.partner_id.name
                    creditor_info = OrderedDict()
                    creditor_info['name'] = payment_invoice.partner_id.name
                    vals['creditorText'] = payment_ref
                    vals['urgency'] = 1
                    vals['request_datetime'] = request_datetime
                    if payment_invoice.fik_number:
                        fik_number = payment_invoice.fik_number
                        vals['account'] = fik_number
                        vals['fik_number'] = fik_number
                    elif payment_invoice.partner_bank_id:
                        vals['vendor_account'] = payment_invoice.partner_bank_id.id
                        customer_account = payment_invoice.bank_account_id.get_bban() if callable(getattr(
                            payment_invoice.partner_bank_id, "get_bban", None)) and payment_invoice.partner_bank_id.acc_type == 'iban' else payment_invoice.partner_bank_id.sanitized_acc_number
                        vals['account'] = customer_account
                        if payment_invoice.partner_bank_id.bank_id.bic:
                            creditor_info['bic'] = payment_invoice.partner_bank_id.bank_id.bic
                            vals['type'] = 11
                    elif vendor_banks:
                        if isinstance(vendor_banks, list):
                            vendor_bank = vendor_banks[0]
                        else:
                            vendor_bank = vendor_banks
                        if vendor_bank.bankintegration_acc_number:
                            vendor_account_number = vendor_bank.bankintegration_acc_number
                        else:
                            vendor_account_number = vendor_bank.get_bban() if callable(
                                getattr(vendor_bank, "get_bban", None)) and vendor_bank.acc_type == 'iban' else vendor_bank.sanitized_acc_number
                        vals['account'] = vendor_account_number
                        vendor_account_id = vendor_bank.id
                        vals['vendor_account'] = vendor_account_id
                        if vendor_bank.bank_id and vendor_bank.bank_id.bic:
                            if not vendor_bank.bankintegration_acc_number:
                                creditor_info['bic'] = vendor_bank.bank_id.bic
                                vals['type'] = 11

                    vals['creditor'] = creditor_info

                    if payment_invoice.payment_journal.bank_account_id.bankintegration_acc_number:
                        customer_account = payment_invoice.payment_journal.bank_account_id.bankintegration_acc_number
                    else:
                        customer_account = payment_invoice.payment_journal.bank_account_id.get_bban() if callable(getattr(
                            payment_invoice.payment_journal.bank_account_id, "get_bban", None)) and payment_invoice.payment_journal.bank_account_id.acc_type == 'iban' else payment_invoice.payment_journal.bank_account_id.sanitized_acc_number
                    customer_account_id = payment_invoice.payment_journal.bank_account_id.id
                    vals['bank_account'] = customer_account_id
                    vals['custacc'] = customer_account
                    vals['payment_id'] = paymentId
                    if vals and total_request_amount:
                        customer_code = payment_invoice.payment_journal.customer_code
                        vals['customer_code'] = customer_code
                        vals['token'] = hashlib.sha256(
                            customer_code.encode('utf-8')).hexdigest()
                        vals['custacc'] = customer_account
                        vals['currency'] = payment_invoice.currency_id.name
                        vals['paydate'] = pay_date
                        vals['amount'] = "%.2f" % amount
                        vals['credacc'] = vendor_account_number
                        vals['erp'] = ERP_PROVIDER
                        vals['payid'] = paymentId
                        vals['now'] = now_date
                        vals['time_format'] = time_format
            except Exception as e:
                print('Generate Payment Json Error: ', str(e))
        _logger.info('Transaction vals: %s', vals)
        return vals

    @api.multi
    def send_for_payment(self, transactions_data):
        if transactions_data:
            try:
                request_model = self.env['bank.integration.request']
                invoice_model = self.env['account.invoice']
                request_id = request_model.generateReqId()
                transactions = []
                hash_list = []
                for transaction in transactions_data:
                    vals = OrderedDict()
                    vals['paymentId'] = transaction['paymentId']
                    vals['paymentDate'] = transaction['paymentDate']
                    vals['amount'] = transaction['amount']
                    vals['currency'] = transaction['currency']
                    vals['account'] = transaction['account']
                    vals['text'] = transaction['text']
                    creditor_info = OrderedDict()
                    vals['creditorText'] = transaction['creditorText']
                    vals['urgency'] = transaction['urgency']

                    if transaction.get('type', False):
                        vals['type'] = 11
                    vals['creditor'] = transaction['creditor']
                    request_obj = request_model.create({
                        'request_id': request_id,
                        'invoice_id': transaction['invoice_id'],
                        'request_datetime': transaction['request_datetime'],
                        'bank_account': transaction['bank_account'],
                        'payment_id': transaction['payment_id'],
                        'vendor_account': transaction['vendor_account'] if transaction.get('vendor_account', False) else False,
                        'fik_number': transaction['fik_number'] if transaction.get('fik_number', False) else False,
                    })
                    transactions.append(vals)
                    auth_vals = OrderedDict()
                    auth_vals['token'] = transaction['token']
                    auth_vals['custacc'] = transaction['custacc']
                    auth_vals['currency'] = transaction['currency']
                    auth_vals['reqid'] = request_id
                    auth_vals['paydate'] = transaction['paydate']
                    auth_vals['amount'] = transaction['amount']
                    auth_vals['credacc'] = transaction['account']
                    auth_vals['erp'] = transaction['erp']
                    auth_vals['payid'] = transaction['payid']
                    auth_vals['now'] = transaction['now']
                    auth_key = self.generate_auth_key(auth_vals)

                    if auth_key:
                        hashed = OrderedDict()
                        hashed["id"] = transaction['payid']
                        hashed["hash"] = auth_key
                        hash_list.append(hashed)
                auth_dict = {}
                auth_dict["serviceProvider"] = transaction['erp']
                auth_dict["account"] = transaction['custacc']
                auth_dict["time"] = transaction['time_format']
                auth_dict["requestId"] = request_id
                auth_dict["hash"] = hash_list
                auth_obj = json.dumps(auth_dict)
                auth_header = base64.b64encode(auth_obj.encode()).decode()
                return [auth_header, request_id, transactions]
            except Exception as e:
                print('Generate Payment Json Error: ', str(e))
        return [False, False, False]


    # Function to if two float values are same or not
    def isClose(self, a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    def get_invoice_number(self, invoice_text):
        invoice_text_list = invoice_text.split(',')
        invoice_str = []
        if invoice_text_list:
            for invoice_text_item in invoice_text_list:
                invoice_list = invoice_text_item.strip(' ').split(' ')
                if invoice_list:
                    for invoice_item in invoice_list:
                        invoice_item = re.sub("[^0-9]", "", invoice_item)
                        invoice_item = invoice_item.lstrip('0')
                        if invoice_item:
                            invoice_str.append(invoice_item)
        return invoice_str

    @api.model
    def get_partner_id(self, statement):
        try:
            stmt_text = None
            invoice_list = None
            if 'creditorText' in statement:
                invoice_type = 'vendor'
                stmt_text = statement['creditorText']
            elif 'debtorText' in statement:
                invoice_type = 'customer'
                stmt_text = statement['debtorText']
            if 'text' in statement:
                stmt_text = stmt_text + ' ' + statement['text']

            stmt_value = abs(statement['amount'])
            if stmt_text:
                invoice_list = self.get_invoice_number(stmt_text)
            partner = None
            if invoice_list:
                invoice_total = 0
                invoice_line = None
                for invoice_number in invoice_list:
                    if invoice_type == 'customer':
                        invoice_lines = self.search(
                            [('number', '=', invoice_number), ('partner_id.customer', '=', 'true')])
                    else:
                        invoice_lines = self.search(
                            ['|', ('reference', 'ilike', invoice_number), ('number', 'ilike', invoice_number), ('partner_id.supplier', '=', 'true')])
                    if invoice_lines:
                        for invoice_line in invoice_lines:
                            invoice_total = invoice_total + invoice_line.residual
                            if(self.isClose(invoice_line.residual, float(stmt_value)) or self.isClose(invoice_total, float(stmt_value))):
                                partner = invoice_line.partner_id
                                break
        except Exception as e:
            print('Partner Exception:', str(e))
        return partner

    @api.model
    def get_bank_statements(self, auth_header, request_id, last_import_date, last_import_balance):
        errors = []
        stmts_data = {}
        transactions = []
        error_msg = _(
            'Something has went wrong. Please check with your administartor')
        use_note_msg = self.env[
            'ir.config_parameter'].sudo().get_param('use_note_msg')
        if isinstance(use_note_msg, str):
            use_note_msg = ast.literal_eval(use_note_msg)
        # Scheduler code will be added here
        conversion_list = []
        conversion_obj = self.env['bankintegration.conversion_list'].search(
            [('active', '=', True)])
        for each in conversion_obj:
            conversion_list.append({each.from_text: each.to_text})

        next_sequence = None
        last_import_sequence = self.env['account.bank.statement.line'].search(
            [], order='id desc', limit=1).ref
        try:
            next_sequence = int(last_import_sequence)
        except ValueError:
            print('Previous reference sequence is not a number')
        last_import_date = last_import_date.strftime('%Y-%m-%d')
        today_date = datetime.datetime.now()
        next_import_date = today_date - datetime.timedelta(days=1)
        next_import_date = next_import_date.strftime('%Y-%m-%d')
        current_balance_amount = 0
        try:
            headers = {
                'Authorization': str('Basic ' + auth_header),
                'Content-type': 'application/json'
            }
            account_statement_url = ACCOUNT_STATEMENT_API_URL + \
                str(request_id) + '&from=' + \
                last_import_date + '&to=' + next_import_date
            response = requests.get(
                account_statement_url,
                verify=False,
                headers=headers,
            )
            #print('response code ----------', response.status_code)
            if response.status_code == 200:
                #response_data = json.loads(response.content.decode('UTF-8'))
                response_data = json.loads(response.text)
                #print ('Response data ', response.content.decode('UTF-8'))
                if response_data['requestId'] == str(request_id):
                    if response_data['currency'] and response_data['entries']:
                        statement_date = response_data['created'].split('T')[0]
                        from_date = datetime.datetime.strptime(response_data['from'].split('T')[
                                                               0], '%Y-%m-%d').strftime('%d-%m-%Y')
                        to_date = datetime.datetime.strptime(response_data['to'].split('T')[
                                                             0], '%Y-%m-%d').strftime('%d-%m-%Y')
                        statement = {
                            'name': _('Bank statement from ' + from_date + ' to ' + to_date),
                            'balance_start': 0,
                            'balance_end_real': 0,
                            'date': datetime.datetime.strptime(statement_date, '%Y-%m-%d'),
                            'transactions': [],
                        }
                        stmts_data = {'account': response_data['account'], 'currency': response_data[
                            'currency'], 'statement': [statement]}
                        bank_statements = response_data['entries']
                        if bank_statements:
                            i = 0
                            n = len(bank_statements)
                            break_point = False
                            for bank_statement in bank_statements:
                                name_text = ''
                                note_msg = ''
                                if 'creditorText' in bank_statement:
                                    name_text = bank_statement['creditorText']
                                    if 'creditorMessage' in bank_statement:
                                        note_msg = bank_statement[
                                            'creditorMessage']
                                elif 'debtorText' in bank_statement:
                                    name_text = bank_statement['debtorText']
                                    if 'debtorMessage' in bank_statement:
                                        note_msg = bank_statement[
                                            'debtorMessage']
                                # else:
                                if name_text == '':
                                    name_text = bank_statement['text']
                                if note_msg == '':
                                    note_msg = bank_statement['text']
                                vals = {
                                    'name': note_msg if use_note_msg else name_text,
                                    'date': datetime.datetime.strptime(bank_statement['date']['value'], '%Y-%m-%dT%H:%M:%S'),
                                    'amount': bank_statement['amount'],
                                    'note': note_msg,
                                    'json_log': json.dumps(bank_statement)
                                }
                                print(bank_statement)
                                partner = self.get_partner_id(bank_statement)
                                if partner:
                                    vals['partner_id'] = partner.id
                                if 'subFamily' in bank_statement['transactionCodes']:
                                    if bank_statement['transactionCodes']['subFamily'] == 'CHRG':
                                        vals['name'] = 'Gebyr ' + vals['name']
                               # for conversion in conversion_list:
                               #     match_from = conversion.keys()[0]
                               #     if match_from in vals['name']:
                               #         vals['name'] = vals['name'].replace(match_from, conversion[match_from])
                               #     if match_from in vals['note']:
                               #         vals['note'] = vals['note'].replace(match_from, conversion[match_from])
                                line_start_balance = bank_statement[
                                    'balance'] - bank_statement['amount']
                                current_balance_amount = bank_statement[
                                    'balance']
                                if self.isClose(last_import_balance, current_balance_amount):
                                    break_point = True
                                    i = 1
                                    continue
                                if not break_point and self.isClose(line_start_balance, last_import_balance):
                                    break_point = True
                                    i = 1
                                if next_sequence:
                                    next_sequence = next_sequence + 1
                                vals['ref'] = str(next_sequence)
                                if i:
                                    if i == 1:
                                        statement[
                                            'balance_start'] = line_start_balance
                                    statement[
                                        'balance_end_real'] = current_balance_amount
                                    transactions.append(vals)
                                    i += 1
                            if break_point:
                                if transactions:
                                    stmts_data['statement'][0].update(
                                        {'transactions': transactions, })
                                else:
                                    error_msg = _('Nothing to import.')
                                    errors.append(error_msg)
                                    raise ValidationError(error_msg)
                            if not break_point:
                                error_msg = _('Entries not matching.')
                                errors.append(error_msg)
                                raise ValidationError(error_msg)
                        else:
                            error_msg = _('Nothing to import.')
                            errors.append(error_msg)
                            raise ValidationError(error_msg)
                    else:
                        error_msg = _('Nothing to import.')
                        errors.append(error_msg)
                        raise ValidationError(error_msg)
                else:
                    error_msg = _('Request Id is not matching.')
                    errors.append(error_msg)
                    raise ValidationError(error_msg)
            elif response.status_code == 401:
                error_msg = _('There was an authentication error when trying to get the bank statements. Please make sure that you bank account number and integration code are correct and try again')
                errors.append(error_msg)
            else:
                # Send email on error
                error_msg = _(
                    'Something has went wrong. Please try after sometime.')
                errors.append(error_msg)
                raise ValidationError(error_msg)
        except Exception as e:
            print('Exception:', str(e))
            raise ValidationError(error_msg)
        return stmts_data, errors

    @api.multi
    def update_payment_status(self, auth_header, request_id, payment_id):
        # Scheduler code will be added here
        try:
            # vals = OrderedDict([
            #    ('paymentId', str(request_id)),
            #])
            headers = {
                'Authorization': str('Basic ' + auth_header),
                'Content-type': 'application/json'
            }
            response = requests.get(
                PAYMENT_STATUS_API_URL +
                str(request_id) + '&paymentId=' + str(payment_id),
                verify=False,
                headers=headers,
            )
            api_request_model = self.env['bank.integration.request']
            invoice_model = self.env['account.invoice']
            invoice_obj = invoice_model.search(
                [('request_id', '=', str(request_id))])
            if response.status_code == 200:
                try:
                    response_data = json.loads(
                        response.content.decode('UTF-8'))
                except Exception as e:
                    print('Content Error:', str(e))
                    response_data = json.loads(response.content)
                if response_data['requestId'] == str(request_id):
                    entries = response_data['answers']
                    if entries:
                        for entry in entries:
                            if entry['status'] not in [1, 2]:
                                try:
                                    payment_id = int(
                                        entry.get('paymentId', False))
                                    api_request_ids = api_request_model.search(
                                        [('request_id', '=', str(request_id)), ('invoice_id', '=', payment_id)])
                                except:
                                    payment_id = entry.get('paymentId', False)
                                    api_request_ids = api_request_model.search(
                                        [('request_id', '=', str(request_id)), ('payment_id', '=', payment_id)])
                                if not api_request_ids:
                                    api_request_ids = api_request_model.search(
                                        [('request_id', '=', str(request_id))])
                                if api_request_ids:
                                    for api_request_id in api_request_ids:
                                        response_text = 'Success'
                                        payment_status = PAYMENT_STATUS_CODE[
                                            str(entry.get('status', False))]
                                        if entry.get('errors', False):
                                            errors_dict = entry.get(
                                                'errors')[0]
                                            response_text = errors_dict.get(
                                                'code', '') + ': ' + errors_dict.get('text', '')
                                        api_request_id.write(
                                            {'request_status': payment_status, 'response_text': response_text})
                                        #print(response_text, payment_status)
                                        if api_request_id.invoice_id.payment_status != 'success':
                                            api_request_id.invoice_id.write(
                                                {'request_id': str(request_id)})
                                            if entry['status'] in [16, 32]:
                                                # print('inside')
                                                api_request_id.invoice_id.write(
                                                    {'payment_error': response_text})
                                            if PAYMENT_STATUS_CODE[str(entry.get('status', False))]:
                                                api_request_id.invoice_id.write(
                                                    {'payment_status': payment_status})

            else:
                # Send email on error
                try:
                    api_request_obj = api_request_model.search(
                        [('request_id', '=', request_id)])
                    request_status = response.reason
                    # print(request_status)
                    request_status = request_status.strip().lower().replace(' ', '_')
                    if api_request_obj:
                        api_request_obj.write(
                            {'request_status': request_status})
                except Exception as e:
                    print(str(e))
                print('Something has went wrong')
        except Exception as e:
            print('Exception:', str(e))

    def get_customer_account(self, account_journal_obj):
        partner_bank_model = self.env['res.partner.bank']
        if account_journal_obj.bank_account_id.bankintegration_acc_number:
            return account_journal_obj.bank_account_id.bankintegration_acc_number
        else:
            account_number = account_journal_obj.bank_account_id.sanitized_acc_number
            if partner_bank_model.retrieve_acc_type(account_number) == 'iban':
                return account_journal_obj.bank_account_id.get_bban() if callable(getattr(
                    account_journal_obj.bank_account_id, "get_bban", None)) else account_journal_obj.bank_account_id.sanitized_acc_number
            else:
                return account_journal_obj.bank_account_id.sanitized_acc_number

    @api.model
    def get_bank_statement_token(self, request_obj_id, journal_id):
        # Scheduler code will be added here
        try:
            ERP_PROVIDER = self.env[
                'ir.config_parameter'].sudo().get_param('erp_provider')
            request_model = self.env['bank.integration.request']
            request_obj = request_model.browse([request_obj_id])
            request_id = request_obj.request_id
            payment_id = request_obj.payment_id
            if not payment_id:
                payment_id = request_id
            account_journal_model = self.env['account.journal']
            account_journal_obj = account_journal_model.browse([journal_id])
            customer_code = ''
            auth_header = False
            if account_journal_obj:
                customer_code = account_journal_obj.customer_code
            else:
                print('Integration Code not available')

            customer_account = self.get_customer_account(account_journal_obj)
            request_datetime_obj = datetime.datetime.now()
            now_date = request_datetime_obj.strftime("%Y%m%d%H%M%S")
            time_format = request_datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")
            #print ('customer_codeeeeee ------- ',customer_code)
            # Dict generate auth key
            auth_vals = OrderedDict([
                ('token', hashlib.sha256(str(customer_code).encode('utf-8')).hexdigest()),
                ('custacc', customer_account),
                ('currency', ''),
                ('reqid', request_id),
                ('paydate', ''),
                ('amount', ''),
                ('credacc', ''),
                ('erp', ERP_PROVIDER),
                ('payid', payment_id),
                ('now', now_date),
            ])
            auth_key = self.generate_auth_key(auth_vals)
            #print ('auth_vals----------',auth_vals )
            # Code to generate auth header
            if auth_key:
                auth_dict = OrderedDict([
                    ("serviceProvider", ERP_PROVIDER),
                    ("account", customer_account),
                    ("time", time_format),
                    ("requestId", request_id),
                    ("hash", [
                        OrderedDict([
                            ("id", request_id),
                            ("hash", auth_key)
                        ])
                    ]),
                ])
                auth_obj = json.dumps(auth_dict)
                # print('auth_obj---------',auth_obj)
                auth_obj = auth_obj.replace(" ", "")
                # t.encode('ascii')
                # print ('headeressssssssssss - ------ ', type(auth_obj))
                # auth_obj = bytes(auth_obj,'utf-8')
                # print ('bytes---converted ---- ',auth_obj)
                auth_header = base64.b64encode(
                    auth_obj.encode('ascii')).decode()
                #print ('encoded headeressssssssssss - ------ ', auth_header)
        except Exception as e:
            print('Request Error: ', str(e))
        return auth_header, request_id

    @api.multi
    def get_payment_status_token(self, request_obj_id):
        # Scheduler code will be added here
        try:
            ERP_PROVIDER = self.env[
                'ir.config_parameter'].sudo().get_param('erp_provider')
            request_model = self.env['bank.integration.request']
            request_obj = request_model.browse([request_obj_id])
            request_id = request_obj.request_id
            account_journal_model = self.env['account.journal']
            account_journal_ids = account_journal_model.search(
                [('bank_account_id', '=', request_obj.bank_account.id)])
            customer_code = ''
            auth_header = False
            if account_journal_ids:
                customer_code = account_journal_ids[0].customer_code
            else:
                print('Integration Code not available')
            if request_obj.bank_account.bankintegration_acc_number:
                customer_account = request_obj.bank_account.bankintegration_acc_number
            else:
                try:
                    customer_account = request_obj.bank_account.get_bban() if callable(getattr(
                        request_obj.bank_account, "get_bban", None)) else request_obj.bank_account.sanitized_acc_number
                except:
                    customer_account = request_obj.bank_account.sanitized_acc_number
            request_datetime_obj = datetime.datetime.now()
            now_date = request_datetime_obj.strftime("%Y%m%d%H%M%S")
            time_format = request_datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")

            # Dict generate auth key
            try:
                auth_vals = OrderedDict([
                    ('token', hashlib.sha256(
                        str(customer_code).encode('utf-8')).hexdigest()),
                    ('custacc', customer_account),
                    ('currency', ''),
                    ('reqid', request_id),
                    ('paydate', ''),
                    ('amount', ''),
                    ('credacc', ''),
                    ('erp', ERP_PROVIDER),
                    ('payid', request_id),
                    ('now', now_date),
                ])
                auth_key = self.generate_auth_key(auth_vals)
            except Exception as e:
                print('Encoding Error: ', str(e))

            # Code to generate auth header
            if auth_key:
                auth_dict = OrderedDict([
                    ("serviceProvider", ERP_PROVIDER),
                    ("account", customer_account),
                    ("time", time_format),
                    ("requestId", request_id),
                    ("hash", [
                        OrderedDict([
                            ("id", request_id),
                            ("hash", auth_key)
                        ])
                    ]),
                ])
                auth_obj = json.dumps(auth_dict)
                auth_header = base64.b64encode(auth_obj.encode()).decode()
        except Exception as e:
            print('Request Error: ', str(e))
        return auth_header, request_id

    @api.multi
    def make_payment(self, auth_header, request_id, transactions):
        account_invoice_model = self.env['account.invoice']
        request_model = self.env['bank.integration.request']
        request_objs = request_model.search([('request_id', '=', request_id)])
        try:
            check_payment_status = self.env[
                'ir.config_parameter'].sudo().get_param('check_payment_status')
            if isinstance(check_payment_status, str):
                check_payment_status = ast.literal_eval(check_payment_status)
            paymnet_dict = OrderedDict()
            paymnet_dict['requestId'] = request_id
            paymnet_dict['transactions'] = transactions
            paymnet_dict['options'] = {
                "waitForBankResponse": check_payment_status,
                "checkPaymentStatus": check_payment_status,
                "moveToNextBankDate": True,
                "useIban": False,
                "skipDuplicateCheck": False
            }
            headers = {
                'Authorization': str('Basic ' + auth_header),
                'Content-type': 'application/json'
            }
            for request_obj in request_objs:
                account_invoice_obj = account_invoice_model.browse(
                    [request_obj.invoice_id.id])
                account_invoice_obj.write(
                    {'payment_status': 'created', 'request_id': request_obj.id})
            response = requests.post(
                PAYMENT_API_URL,
                verify=False,
                data=json.dumps(paymnet_dict),
                headers=headers,
            )
            print(json.dumps(paymnet_dict), headers, response.__dict__)
            if response.status_code in [200, 201, 202, 204]:
                for request_obj in request_objs:
                    request_obj.write({'request_status': 'pending'})
                    account_invoice_obj = account_invoice_model.browse(
                        [request_obj.invoice_id.id])
                    account_invoice_obj.write({'payment_status': 'pending'})
                print('Payment Request Sent Successfully')
            else:
                for request_obj in request_objs:
                    account_invoice_obj = account_invoice_model.browse(
                        [request_obj.invoice_id.id])
                    request_obj.unlink()
                    account_invoice_obj.write(
                        {'payment_status': 'failed', 'payment_error': 'Check bank account number'})
                print('Err: Something has went wrong')
        except Exception as e:
            print('Make Payment Error: ', str(e))

    @api.multi
    def bankintegration_multi_payments(self, invoice_ids):
        invoice_model = self.env['account.invoice']
        error_msg = ''
        payment_vals = {}
        try:
            if invoice_ids:
                invoice_details = invoice_model.search([('id', 'in', invoice_ids), (
                    'payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open')])
                if len(invoice_ids) == len(invoice_details):
                    # Write code to make payments using REST API
                    utc_datetime = datetime.datetime.utcnow()
                    payment_vals = []
                    for invoice_obj in invoice_details:
                        _logger.info('Invoice_id: %s', str(invoice_obj.id))
                        try:
                            json_vals = self.generate_payment_json(
                                invoice_obj.id, utc_datetime)
                            if json_vals:
                                payment_vals.append(json_vals)
                            # if auth_header and request_id and transactions:
                            #    print(auth_header, request_id, transactions)
                            #    self.make_payment(
                            #        auth_header, request_id, transactions)
                        except:
                            pass
                    if payment_vals:
                        payment_vals.sort(key=lambda x: x['custacc'])
                        transactions_data = []
                        custacc = ''
                        for payment in payment_vals:
                            if custacc and custacc == payment['custacc']:
                                transactions_data.append(payment)
                            if custacc and custacc != payment['custacc']:
                                auth_header, request_id, transactions = self.send_for_payment(
                                    transactions_data)
                                if auth_header and request_id and transactions:
                                    self.make_payment(
                                        auth_header, request_id, transactions)
                                transactions_data = [payment]
                            if not custacc:
                                custacc = payment['custacc']
                                transactions_data.append(payment)
                        if transactions_data:
                            auth_header, request_id, transactions = self.send_for_payment(
                                transactions_data)
                            if auth_header and request_id and transactions:
                                self.make_payment(
                                    auth_header, request_id, transactions)
                else:
                    error_msg = _(
                        'Some of the selected invoices has already been processed.')
                    raise ValidationError(error_msg)
        except Exception as e:
            error_msg = 'Bank Integration Error: ' + str(e)
            print(error_msg)
            _logger.debug(str(e))
            raise ValidationError(error_msg)

    @api.multi
    def bankintegration_schedule_payment(self, invoice_ids):
        invoice_model = self.env['account.invoice']
        error_msg = ''
        try:
            if invoice_ids:
                invoice_details = invoice_model.search([('id', 'in', invoice_ids), (
                    'payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open')])
                if len(invoice_ids) == len(invoice_details):
                    # Write code to make payments using REST API
                    today_date = datetime.datetime.today()
                    for invoice_obj in invoice_details:
                        invoice_obj.write(
                            {'payment_autopay': True, 'payment_duedate': today_date.date()})
                else:
                    error_msg = _(
                        'Some of the selected invoices has already been processed.')
                    raise ValidationError(error_msg)
        except Exception as e:
            error_msg = 'Bank Integration Error: ' + str(e)
            _logger.debug(str(e))
            raise ValidationError(error_msg)

    @api.model
    def bankintegration_payment_status(self):
        erp_key, customer_code = self.get_bankintegration_settings()
        if erp_key and customer_code:
            request_model = self.env['bank.integration.request']
            request_ids = request_model.search(
                [('request_status', 'in', [PAYMENT_STATUS_CODE['1'], PAYMENT_STATUS_CODE['2'], PAYMENT_STATUS_CODE['4'], PAYMENT_STATUS_CODE['128']])], order='id desc')
            try:
                if request_ids:
                    # Write code to make payments using REST API
                    for request in request_ids:
                        auth_header, request_id = self.get_payment_status_token(
                            request.id)
                        self.update_payment_status(
                            auth_header, request_id, request.payment_id)
                else:
                    print('Nothing is Pending')
            except Exception as e:
                print('Something Wrong Happened: ', str(e))
        return True

    @api.multi
    def action_set_payment_again(self):
        self.ensure_one()
        if self.filtered(lambda inv: inv.payment_status not in ['rejected', 'failed']):
            raise UserError(
                _("Invoice must be in rejected or failed state in order to be reset."))
        elif self.filtered(lambda inv: inv.state not in ['open']):
            raise UserError(
                _("Invoice must be in open state in order to proceed."))
        return self.write({'payment_status': False, 'payment_error': False, 'payment_count': self.payment_count + 1, 'payment_id': str(self.id) + 'OH' + str(self.payment_count + 1)})

    @api.model
    def bankintegration_auto_payment(self):
        erp_key, customer_code = self.get_bankintegration_settings()
        try:
            if erp_key and customer_code:
                # Scheduler code will be added here
                invoice_model = self.env['account.invoice']
                today_date = datetime.datetime.today()
                set_validate_payment = self.env[
                    'ir.config_parameter'].sudo().get_param('set_validate_payment')
                if isinstance(set_validate_payment, str):
                    set_validate_payment = ast.literal_eval(
                        set_validate_payment)

                if set_validate_payment:
                    invoice_details = invoice_model.search(
                        [('payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open'), ('payment_autopay', '=', True)])
                else:
                    invoice_details = invoice_model.search([('payment_status', '=', False), (
                        'type', '=', 'in_invoice'), ('state', '=', 'open'), ('payment_duedate', '<=', today_date.date()), ('payment_autopay', '=', True)])

                if invoice_details:
                    invoice_ids = [x.id for x in invoice_details]
                    self.bankintegration_multi_payments(invoice_ids)
        except Exception as e:
            # print(str(e))
            return False
        return True
