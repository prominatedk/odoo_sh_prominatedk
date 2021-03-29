# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bankintegration_payment_margin = fields.Integer(string=_('Payment Margin'), help="Payment Margin", related="company_id.bankintegration_payment_margin", readonly=False, oldname='payment_margin')
    bankintegration_autopay = fields.Boolean(string=_('Default auto pay'), related="company_id.bankintegration_autopay", readonly=False, oldname='autopay')
    bankintegration_send_on_validate = fields.Boolean(string=_('Set for payment after validate?'), related="company_id.bankintegration_send_on_validate", readonly=False, oldname='set_validate_payment')
    bankintegration_payment_journal_id = fields.Many2one('account.journal', string='Payment journal', related='company_id.bankintegration_payment_journal_id', readonly=False, oldname='payment_journal')
    bankintegration_erp_provider = fields.Char(string='ERP Provider', help="Please enter ERP Provider name.", related='company_id.bankintegration_erp_provider', readonly=False, oldname='erp_provider')
    bankintegration_provider_api_key = fields.Char(string='API Key', help="Please enter API Key.", related='company_id.bankintegration_provider_api_key', readonly=False, oldname='bi_api_key')
    bankintegration_statement_note_as_label = fields.Boolean(string=_('Use note as label?'), related='company_id.bankintegration_statement_note_as_label', readonly=False, oldname='use_note_msg')
    bankintegration_check_payment_status = fields.Boolean(string=_('Check payment status on payment.'), related='company_id.bankintegration_check_payment_status', readonly=False, oldname='check_payment_status')
    bankintegration_use_odoo_bban = fields.Boolean(string=_('Use odoo bban'), related='company_id.bankintegration_use_odoo_bban', readonly=False, oldname='use_bban')
    bankintegration_extended_import_format = fields.Boolean(string=_('Use extended import?'), related='company_id.bankintegration_extended_import_format', readonly=False, oldname='use_extended_import')
    bankintegration_last_entry_date_as_statement_date = fields.Boolean(related='company_id.bankintegration_last_entry_date_as_statement_date', string='Use the date of the last entry as the statement date', help='Checking this will set the date of the bank statement\nto the date of the last transaction in the statement\nThis is normally only used if you wish to have the statement\non the same date as the transactions', readonly=False, oldname='use_last_entry_date_as_statement_date')
    bankintegration_transaction_accounting_date = fields.Selection(string='Accounting date for transactions', selection=[
        ('value', 'Value date'),
        ('booking', 'Booking date')
    ], help='Choose which date to use as the accounting date of bankintegration.dk bank statements in Odoo\n [Value date] will use the date where the money is actually deposited/withdrawn from the account\n[Booking date] will use the date on which the bank posts the amount in their book keepting', related='company_id.bankintegration_transaction_accounting_date', readonly=False)