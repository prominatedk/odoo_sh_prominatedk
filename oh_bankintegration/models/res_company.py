# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    bankintegration_payment_margin = fields.Integer(
        string=_('Payment Margin'), help="Payment Margin", default=0)
    bankintegration_autopay = fields.Boolean(string=_('Default auto pay'), default=False)
    bankintegration_send_on_validate = fields.Boolean(
        string=_('Set for payment after validate?'), default=False)
    bankintegration_payment_journal_id = fields.Many2one(
        'account.journal', string='Payment journal', domain="[('type', '=', 'bank')]")
    bankintegration_erp_provider = fields.Char(
        string='ERP Provider', help="Please enter ERP Provider name.")
    bankintegration_provider_api_key = fields.Char(string='API Key', help="Please enter API Key.")
    bankintegration_statement_note_as_label = fields.Boolean(
        string=_('Use note as label?'), default=False)
    bankintegration_check_payment_status = fields.Boolean(
        string=_('Check payment status on payment.'), default=False)
    bankintegration_use_odoo_bban = fields.Boolean(string=_('Use odoo bban'), default=False)
    bankintegration_extended_import_format = fields.Boolean(
        string=_('Use extended import?'), default=False)
    bankintegration_last_entry_date_as_statement_date = fields.Boolean(string='Use the date of the last entry as the statement date',
                                                           help='Checking this will set the date of the bank statement\nto the date of the last transaction in the statement\nThis is normally only used if you wish to have the statement\non the same date as the transactions')
    bankintegration_transaction_accounting_date = fields.Selection(string='Accounting date for transactions', selection=[
        ('value', 'Value date'),
        ('booking', 'Booking date')
    ], help='Choose which date to use as the accounting date of bankintegration.dk bank statements in Odoo\n [Value date] will use the date where the money is actually deposited/withdrawn from the account\n[Booking date] will use the date on which the bank posts the amount in their book keepting', default='booking')

    def has_valid_bankintegration_config(self):
        self.ensure_one()
        if not self.bankintegration_erp_provider or not self.bankintegration_provider_api_key:
            _logger.error('Company {company} could not be processed as the ERP provider and Bankintegration.dk API key are not defined'.format(
                company=self.display_name))
            return False
        if not self.bankintegration_payment_journal_id:
            _logger.error('Company {company} could not be processed as no payment journal has been defined'.format(
                company=self.display_name))
            return False
        return True
