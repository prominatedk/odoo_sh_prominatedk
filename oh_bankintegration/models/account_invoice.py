# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import OrderedDict
import datetime
import re
import logging
_logger = logging.getLogger(__name__)

FI_PAYMENT_TYPES = {
    '+01': 3,
    '+04': 4,
    '+15': 5,
    '+71': 6,
    '+73': 7,
    '+75': 8,
}

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
    _inherit = "account.invoice"

    def _default_bankintegration_payment_autopay(self):
        return self.env.user.company_id.bankintegration_autopay

    def _default_bankintegration_payment_journal_id(self):
        return self.env.user.company_id.bankintegration_payment_journal_id

    bankintegration_payment_status = fields.Selection([
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('success', 'Success'),
        ('rejected', 'Rejected'),
        ('failed', 'Failed'),
        ('not_found', 'Not Found'),
    ], string='Payment status', index=True, oldname='payment_status')
    bankintegration_payment_date = fields.Date(
        string='Payment date', index=True, help="Due date for payment", oldname='payment_duedate')
    bankintegration_payment_autopay = fields.Boolean(
        string='Auto pay', default=_default_bankintegration_payment_autopay, help="If this is set our scheduler automatic make payment", oldname='payment_autopay')
    bankintegration_payment_journal_id = fields.Many2one(
        'account.journal', string='Payment journal', default=_default_bankintegration_payment_journal_id, domain=[('type', '=', 'bank')], oldname='payment_journal')
    payment_reference = fields.Char(string='Payment Reference')
    bankintegration_payment_error = fields.Char(string='Payment Error', oldname='payment_error')
    bankintegration_request_id = fields.Char(string="Request id", oldname='request_id')
    bankintegration_payment_id = fields.Char(string="Payment id", oldname='payment_id')
    bankintegration_payment_attempts = fields.Integer(string="Payment count", default=1, oldname='payment_count')
    # FIK Payment code
    payment_fik_number_payment_code = fields.Selection(selection=[
        ('+01', '+01'),
        ('+04', '+04'),
        ('+15', '+15'),
        ('+71', '+71'),
        ('+73', '+73'),
        ('+75', '+75'),
    ], oldname='fik_number_payment_code')
    # FIK payment string. Usually contains customer number, invoice number and control digi
    payment_fik_number_payment_string = fields.Char(size=16, oldname='fik_number_payment_string')
    # FIK Creditor number. The creditor FIK agreement number
    payment_fik_number_creditor = fields.Char(size=8, oldname='fik_number_creditor')

    # This will be computed and stored
    payment_fik_number = fields.Char(string="FIK Number", compute='_compute_payment_fik_number', inverse='_compute_inverse_payment_fik_number', store=True, oldname='fik_number')

    @api.depends('payment_fik_number_payment_code', 'payment_fik_number_payment_string', 'payment_fik_number_creditor', 'partner_id', 'company_id')
    def _compute_payment_fik_number(self):
        for record in self:
            # Partner and company must be in Denmark
            denmark = self.env.ref('base.dk').id
            if not record.partner_id.country_id.id == denmark and not record.company_id.country_id.id == denmark:
                record.payment_fik_number = False
            elif not record.payment_fik_number_creditor:
                record.payment_fik_number = False
            # Handle those that only require payment_fik_number_payment_code and payment_fik_number_creditor
            elif record.payment_fik_number_payment_code in ['+01', '+73']:
                record.payment_fik_number = '{code}<+{creditor}<'.format(code=record.payment_fik_number_payment_code, creditor=record.payment_fik_number_creditor)
            else:
                if not record.payment_fik_number_payment_string:
                    record.payment_fik_number = False
                else:
                    record.payment_fik_number = '{code}<{payment}+{creditor}<'.format(code=record.payment_fik_number_payment_code, payment=record.payment_fik_number_payment_string, creditor=record.payment_fik_number_creditor)

    def _compute_inverse_payment_fik_number(self):
        for record in self:
            # Regex for FI 01 and FI 73
            # (\+\d\d\<)(\+)(\d+)
            # Regex for others
            # (\+\d\d\<)(\d+)(\+)(\d+)(\<)
            if not record.payment_fik_number:
                continue

            # First check if FI payment string starts with +01 or +73
            matches = re.findall(r"(\+\d\d\<)(\+)(\d+)", record.payment_fik_number)
            if not matches:
                # If not match is found for +01 or +73 syntax, validate if we have the remaining
                matches = re.findall(r"(\+\d\d\<)(\d+)(\+)(\d+)(\<)", record.payment_fik_number)
                if not matches:
                    # If still no matches are found, then the provided FI payment string is not valid
                    record.payment_fik_number_payment_code = False
                    record.payment_fik_number_payment_string = False
                    record.payment_fik_number_creditor = False
                else:
                    parts = record.payment_fik_number.split('<')
                    # Extract creditor from payment string
                    parts[2] = parts[1].split('+')[1]
                    parts[1] = parts[1].replace('+' + parts[2], '')
                    record.payment_fik_number_payment_code = parts[0]
                    record.payment_fik_number_payment_string = parts[1]
                    record.payment_fik_number_creditor = parts[2]
            else:
                parts = record.payment_fik_number.split('<+')
                record.payment_fik_number_payment_code = parts[0]
                record.payment_fik_number_payment_string = False
                record.payment_fik_number_creditor = parts[1][:-1]


    @api.onchange('date_due')
    def _onchange_date_due(self):
        for record in self:
            if record.date_due:
                record.bankintegration_payment_date = record.date_due + datetime.timedelta(days=record.company_id.bankintegration_payment_margin)

    def action_reset_bankintegration_bankintegration_payment_status(self):
        self.ensure_one()
        if self.bankintegration_payment_status not in ['rejected', 'failed']:
            raise UserError(_('We do not allow resend of an invoice where the previous request has not returned an error or a rejection'))
        elif self.state != 'open':
            raise UserError(_('Invoices must be in the open state in order to proceed'))
        return self.write({
            'bankintegration_payment_status': False,
            'bankintegration_payment_error': False,
            'bankintegration_payment_attempts': self.bankintegration_payment_attempts + 1,
        })

    def cron_transfer_bankintegration_payments(self):
        for company in self.env['res.company'].search([]):
            # Validate if we should even process data for this company
            if not company.has_valid_bankintegration_config():
                continue
            # Validate if we can even process payments out of the payment journal configured on the company
            if not company.bankintegration_payment_journal_id.has_valid_bankintegration_config():
                continue
            # Process all vendor bills in the company, which are to be paid using bankintegration today
            vendor_bill_domain = self._get_bankintegration_vendorbill_domain(company)
            bills = self.search(vendor_bill_domain)
            bills._pay_with_bankintegration(is_scheduler=True)
            
    def _get_bankintegration_vendorbill_domain(self, company, journal):
        if company.bankintegration_send_on_validate:
            return [('bankintegration_payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open'), ('bankintegration_payment_autopay', '=', True), ('company_id', '=', company.id), ('bankintegration_payment_journal_id', '=', journal.id)]
        else:
            return [('bankintegration_payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open'), ('bankintegration_payment_date', '<=', fields.Date.today(self)), ('bankintegration_payment_autopay', '=', True), ('company_id', '=', company.id), ('bankintegration_payment_journal_id', '=', journal.id)]

    def _pay_with_bankintegration(self, journal, is_scheduler=False):
        BankIntegrationRequest = self.env['bank.integration.request']
        results = self._generate_bankintegration_transactions(is_scheduler=is_scheduler)
        if len(results) == 0:
            _logger.warn('No payments to make')
            return False
        if not all([result[2] for result in results]):
            _logger.warn('One or more payments could not be processed')
        for index, result in enumerate(results):
            if not result[2]:
                results.pop(index)
                _logger.error('During generation of payment data, there was an error generating payment details for vendor bill with ID {}. The payment has been removed from the list of payments to make. Please see previous log entries for details'.format(result[1]))
        if not results:
            _logger.error('There are no bills to process. Please check the error messages on each bill')
            return False
        first_bill = self.browse(results[0][1])
        # Extract the IDs of the vendor bills being paid
        bill_ids = [bill[1] for bill in results]
        # Extract all the payment values
        payment_vals = [bill[2] for bill in results]
        # Validate that all bills are paid from the same account and in the same currency
        if not any([val['currency'] == first_bill.currency_id.name for val in payment_vals if val]):
            _logger.error('All payments do not have the same currency')
            return False

        request_vals = {
            'company_id': first_bill.company_id.id,
            'journal_id': journal.id,
            'invoice_ids': bill_ids,
            'request_date': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }

        request = BankIntegrationRequest.create(request_vals)
        request.set_request_id()
        auth_header = request.get_vendorbill_payment_token(payment_vals)
        if not auth_header:
            _logger.error('Auth not generated')
            return False

        result = request.pay_invoice(payment_vals, auth_header)

        for payment in results:
            bill_id = payment[1]
            bill = self.browse(bill_id)
            payment_vals = payment[2]
            bill.write({
                'bankintegration_payment_id': payment_vals['paymentId'],
                'bankintegration_request_id': request.request_id
            })

    def _generate_bankintegration_transactions(self, is_scheduler=False):
        results = []
        for record in self:
            vals = record._generate_bankintegration_payment_transaction_data(is_scheduler=is_scheduler)
            if not vals:
                record.write({
                    'bankintegration_payment_error': _('There was an error trying to pay this vendor bill using bankintegration'),
                    'bankintegration_payment_status': PAYMENT_STATUS_CODE['32']
                })
                _logger.error('There was an error generating the transaction for vendor bill {bill}'.format(bill=record.display_name))
            results.append((record.company_id.id, record.id, vals))
            
        return results

    def _generate_bankintegration_payment_transaction_data(self, is_scheduler=False):
        self.ensure_one()
        # NOTE: Payment date is now computed by subtracing the payment margin from the due date if no payment date is there
        # TODO: It would be a great feature to have configurable urgency per bill, to force same day or immediate payment when necessary. For now we keep version 1.x.x implementation of setting it as 1 = normal payment
        # Legacy modification. If the invoice was created before the default value of bankintegration_payment_attempts was set to 1, then it will be 0 and we have to set it as one
        if self.bankintegration_payment_attempts == 0:
            self.write({'bankintegration_payment_attempts': 1})
        vals = {
            'amount': "%.2f" % self.residual,
            'currency': self.currency_id.name,
            'paymentDate': self.bankintegration_payment_date.strftime('%Y-%m-%d') if self.bankintegration_payment_date else (self.date_due - datetime.timedelta(days=int(self.company_id.bankintegration_payment_margin))).strftime('%Y-%m-%d'),
            'paydate': self.bankintegration_payment_date.strftime('%Y%m%d') if self.bankintegration_payment_date else (self.date_due - datetime.timedelta(days=int(self.company_id.bankintegration_payment_margin))).strftime('%Y%m%d'),
            'paymentId': 'PAY_{bill}_{provider}_{id}_{count}'.format(bill=self.number, provider=self.company_id.bankintegration_erp_provider, id=self.id, count=self.bankintegration_payment_attempts),
            'text': self.number + ' ' + self.partner_id.display_name,
            'urgency': 1,
            'creditorText': self.payment_reference or self.reference or self.company_id.display_name,
            'creditor': OrderedDict({
                'name': self.partner_id.display_name,
            })
        }

        if self.payment_fik_number:
            # Chekc if a FI payment string is set on the vendor bill
            if not self._payment_fik_number_is_valid():
                if is_scheduler:
                    return False
                else:
                    raise UserError(_('The FI payment string on the vendor bill is not valid'))
            # We asume that the payment is using FIK (Fælles Inbetalingskort)
            vals['account'] = self.payment_fik_number
            # Try to find the correct payment type in FI_PAYMENT_TYPES dict
            if self.payment_fik_number[:3] in FI_PAYMENT_TYPES:
                vals['type'] = FI_PAYMENT_TYPES[self.payment_fik_number[:3]]
            else:
                if is_scheduler:
                    return False
                else:
                    raise ValidationError(_('The value provided as the FI payment string appears to be valid, but no payment type could be found matching the FI payment type %s' % self.payment_fik_number[:3]))
        elif self.partner_bank_id:
            # If no FI payment string is set, check if a specific recipient bank account has been configured
            vals['account'] = self.partner_bank_id.get_bban() if self.company_id.bankintegration_use_odoo_bban else self.partner_bank_id.sanitized_acc_number
            # Set payment type as Foreign IBAN payment if account type is IBAN. Otherwise handle it as a domestic payment
            if self.partner_bank_id.bank_id.bic:
                vals['type'] = 11
                vals['creditor']['bic'] = self.partner_bank_id.bank_id.bic
            else:
                vals['type'] = 1
        else:
            # If neither a FI payment string or a bank account has been provided, then we look at the partner and use the first listed account
            if self.partner_id.bank_ids.ids:
                # Filter bank accounts on the partner by sequence and get the first one
                chosen_bank = self.partner_id.bank_ids.sorted(key='sequence')[0]
                vals['account'] = chosen_bank.get_bban() if self.company_id.bankintegration_use_odoo_bban else chosen_bank.sanitized_acc_number
                # Set payment type as Foreign IBAN payment if account type is IBAN. Otherwise handle it as a domestic payment
                if chosen_bank.bank_id.bic:
                    vals['type'] = 11
                    vals['creditor']['bic'] = chosen_bank.bank_id.bic
                else:
                    vals['type'] = 1
            else:
                if is_scheduler:
                    return False
                else:
                    raise ValidationError(_('No bank accounts have been configured on the partner for this vendor bill'))
        
        # If no FI payment string or bank account has been found at this point, we will not even get to this part of the code
        if not self._validate_bankintegration_required_fields(vals):
            error = _('One or more required fields are missing in order to make the payment through bankintegration')
            if is_scheduler:
                self.message_post(body=error, message_type='notification')
                return False
            else:
                raise ValidationError(error)
        return vals

    def _payment_fik_number_is_valid(self):
        self.ensure_one()
        # Regex for FI 01 and FI 73
        # (\+\d\d\<)(\+)(\d+)
        # Regex for others
        # (\+\d\d\<)(\d+)(\+)(\d+)(\<)

        # First check if FI payment string starts with +01 or +73
        matches = re.findall(r"(\+\d\d\<)(\+)(\d+)", self.payment_fik_number)
        if not matches:
            # If not match is found for +01 or +73 syntax, validate if we have the remaining
            matches = re.findall(r"(\+\d\d\<)(\d+)(\+)(\d+)(\<)", self.payment_fik_number)
            if not matches:
                # If still no matches are found, then the provided FI payment string is not valid
                return False
        return True

    def _validate_bankintegration_required_fields(self, vals):
        if vals:
            if not 'paymentId' in vals:
                return False
            if not 'paymentDate' in vals:
                return False
            if not 'account' in vals:
                return False
            if not 'amount' in vals:
                return False
            if vals['amount'] == 0:
                return False
            if not 'creditor' in vals:
                return False
            return True
        else:
            return False
