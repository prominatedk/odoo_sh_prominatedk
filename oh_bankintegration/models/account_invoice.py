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

    def _default_payment_autopay(self):
        return self.env.user.company_id.autopay

    def _default_payment_journal(self):
        return self.env.user.company_id.payment_journal

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
        string='Auto pay', default=_default_payment_autopay, help="If this is set our scheduler automatic make payment")
    payment_journal = fields.Many2one(
        'account.journal', string='Payment journal', default=_default_payment_journal, domain=[('type', '=', 'bank')])
    payment_reference = fields.Char(string='Payment Reference')
    payment_error = fields.Char(string='Payment Error')
    request_id = fields.Char(string="Request id")
    payment_id = fields.Char(string="Payment id")
    payment_count = fields.Integer(string="Payment count", default=1)
    fik_number = fields.Char(string="FIK Number", default='')

    @api.onchange('date_due')
    def _onchange_date_due(self):
        for record in self:
            if record.date_due:
                record.payment_duedate = record.date_due + datetime.timedelta(days=record.company_id.payment_margin)

    def action_reset_bankintegration_payment_status(self):
        self.ensure_one()
        if self.payment_status not in ['rejected', 'failed']:
            raise UserError(_('We do not allow resend of an invoice where the previous request has not returned an error or a rejection'))
        elif self.state != 'open':
            raise UserError(_('Invoices must be in the open state in order to proceed'))
        return self.write({
            'payment_status': False,
            'payment_error': False,
            'payment_count': self.payment_count + 1,
        })

    def cron_transfer_bankintegration_payments(self):
        for company in self.env['res.company'].search([]):
            # Validate if we should even process data for this company
            if not company.has_valid_bankintegration_config():
                continue
            # Validate if we can even process payments out of the payment journal configured on the company
            if not company.payment_journal.has_valid_bankintegration_config():
                continue
            # Process all vendor bills in the company, which are to be paid using bankintegration today
            vendor_bill_domain = self._get_bankintegration_vendorbill_domain(company)
            bills = self.search(vendor_bill_domain)
            bills._pay_with_bankintegration(is_scheduler=True)
            
    def _get_bankintegration_vendorbill_domain(self, company):
        if company.set_validate_payment:
            return [('payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open'), ('payment_autopay', '=', True), ('company_id', '=', company.id)]
        else:
            return [('payment_status', '=', False), ('type', '=', 'in_invoice'), ('state', '=', 'open'), ('payment_duedate', '<=', fields.Date.today(self)), ('payment_autopay', '=', True), ('company_id', '=', company.id)]

    def _pay_with_bankintegration(self, is_scheduler=False):
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
        first_bill = self.browse(results[0][1])
        # Extract the IDs of the vendor bills being paid
        bill_ids = [bill[1] for bill in results]
        # Extract all the payment values
        payment_vals = [bill[2] for bill in results]
        # Validate that all bills are paid from the same account and in the same currency
        if not any([val['currency'] == first_bill.currency_id.name for val in payment_vals]):
            _logger.error('All payments do not have the same currency')
            return False

        request_vals = {
            'company_id': first_bill.company_id.id,
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
                'payment_id': payment_vals['paymentId'],
                'request_id': request.request_id
            })

    def _generate_bankintegration_transactions(self, is_scheduler=False):
        results = []
        for record in self:
            vals = record._generate_bankintegration_payment_transaction_data(is_scheduler=is_scheduler)
            if not vals:
                record.write({
                    'payment_error': _('There was an error trying to pay this vendor bill using bankintegration'),
                    'payment_status': PAYMENT_STATUS_CODE['32']
                })
                _logger.error('There was an error generating the transaction for vendor bill {bill}'.format(bill=record.display_name))
            results.append((record.company_id.id, record.id, vals))
            
        return results

    def _generate_bankintegration_payment_transaction_data(self, is_scheduler=False):
        self.ensure_one()
        # NOTE: Payment date is now computed by subtracing the payment margin from the due date if no payment date is there
        # TODO: It would be a great feature to have configurable urgency per bill, to force same day or immediate payment when necessary. For now we keep version 1.x.x implementation of setting it as 1 = normal payment
        # Legacy modification. If the invoice was created before the default value of payment_count was set to 1, then it will be 0 and we have to set it as one
        if self.payment_count == 0:
            self.write({'payment_count': 1})
        vals = {
            'amount': "%.2f" % self.residual,
            'currency': self.currency_id.name,
            'paymentDate': self.payment_duedate.strftime('%Y-%m-%d') if self.payment_duedate else (self.date_due - datetime.timedelta(days=int(self.company_id.payment_margin))).strftime('%Y-%m-%d'),
            'paydate': self.payment_duedate.strftime('%Y%m%d') if self.payment_duedate else (self.date_due - datetime.timedelta(days=int(self.company_id.payment_margin))).strftime('%Y%m%d'),
            'paymentId': 'PAY_{bill}_{provider}_{id}_{count}'.format(bill=self.number, provider=self.company_id.erp_provider, id=self.id, count=self.payment_count),
            'text': self.number + ' ' + self.partner_id.display_name,
            'urgency': 1,
            'creditorText': self.payment_reference or self.reference or self.company_id.display_name,
            'creditor': OrderedDict({
                'name': self.partner_id.display_name,
            })
        }

        if self.fik_number:
            # Chekc if a FI payment string is set on the vendor bill
            if not self._fik_number_is_valid():
                if is_scheduler:
                    return False
                else:
                    raise UserError(_('The FI payment string on the vendor bill is not valid'))
            # We asume that the payment is using FIK (Fælles Inbetalingskort)
            vals['account'] = self.fik_number
            # Try to find the correct payment type in FI_PAYMENT_TYPES dict
            if self.fik_number[:3] in FI_PAYMENT_TYPES:
                vals['type'] = FI_PAYMENT_TYPES[self.fik_number[:3]]
            else:
                if is_scheduler:
                    return False
                else:
                    raise ValidationError(_('The value provided as the FI payment string appears to be valid, but no payment type could be found matching the FI payment type %s' % self.fik_number[:3]))
        elif self.partner_bank_id:
            # If no FI payment string is set, check if a specific recipient bank account has been configured
            vals['account'] = self.partner_bank_id.get_bban() if self.company_id.use_bban else self.partner_bank_id.sanitized_acc_number
            # Set payment type as Foreign IBAN payment if account type is IBAN. Otherwise handle it as a domestic payment
            vals['type'] = 11 if self.partner_bank_id.acc_type == 'iban' else 1
            if self.partner_bank_id.acc_type == 'iban':
                vals['creditor']['bic'] = self.partner_bank_id.bank_id.bic
        else:
            # If neither a FI payment string or a bank account has been provided, then we look at the partner and use the first listed account
            if self.partner_id.bank_ids.ids:
                # Filter bank accounts on the partner by sequence and get the first one
                chosen_bank = self.partner_id.bank_ids.sorted(key='sequence')[0]
                vals['account'] = chosen_bank.get_bban() if self.company_id.use_bban else chosen_bank.sanitized_acc_number
                # Set payment type as Foreign IBAN payment if account type is IBAN. Otherwise handle it as a domestic payment
                vals['type'] = 11 if chosen_bank.acc_type == 'iban' else 1
                if chosen_bank.acc_type == 'iban':
                    vals['creditor']['bic'] = chosen_bank.bank_id.bic
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

    def _fik_number_is_valid(self):
        self.ensure_one()
        # Regex for FI 01 and FI 73
        # (\+\d\d\<)(\+)(\d+)
        # Regex for others
        # (\+\d\d\<)(\d+)(\+)(\d+)(\<)

        # First check if FI payment string starts with +01 or +73
        matches = re.findall(r"(\+\d\d\<)(\+)(\d+)", self.fik_number)
        if not matches:
            # If not match is found for +01 or +73 syntax, validate if we have the remaining
            matches = re.findall(r"(\+\d\d\<)(\d+)(\+)(\d+)(\<)", self.fik_number)
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
