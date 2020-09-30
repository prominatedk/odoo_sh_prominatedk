# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from dateutil.parser import parse
import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    customer_code = fields.Char(string='Integration Code', help="Please provide Integration Code for bankintegration.")

    def _get_oh_bank_statements_available_import_formats(self):
        return [('bankintegration_import', _('Auto import from bankintegration'))]

    def __get_bank_statements_available_sources(self):
        result = super(AccountJournal, self).__get_bank_statements_available_sources()
        formats_list = self._get_oh_bank_statements_available_import_formats()
        if formats_list:
            result += formats_list
        return result
        
    def has_valid_bankintegration_config(self):
        self.ensure_one()
        if not self.customer_code:
            _logger.error('Journal {journal} in company {company} cannot be processed as the integration code for bankintegration.dk is missing'.format(journal=self.name, company=self.company_id.display_name))
            return False
        if not self.bank_id.id:
            _logger.error('No bank has been defined on journal {journal} in company {company}'.format(journal=self.name, company=self.company_id.display_name))
            return False
        if not self.bank_account_id.id:
            _logger.error('No bank account is linked to journal {journal} in company {company}'.format(journal=self.name, company=self.company_id.display_name))
            return False
        if self.bank_account_id.acc_type == 'iban':
            if not self.bank_account_id.bankintegration_acc_number:
                _logger.error('The bank account linked to journal {journal} in company {company} is of type IBAN, but bankintegration_acc_number field is not filled'.format(journal=self.name, company=self.company_id.display_name))
                return False
            elif not len(self.bank_account_id.bankintegration_acc_number) == 14:
                _logger.error('The bank account linked to journal {journal} in company {company} has an invalid bankintegration_acc_number {bank_acc}, which is only {bank_acc_len} digits long'.format(journal=self.name, company=self.company_id.display_name, bank_acc=self.bank_account_id.bankintegration_acc_number, bank_acc_len=len(self.bank_account_id.bankintegration_acc_number)))
                return False
        elif self.bank_account_id.acc_type == 'bank':
            if not self.bank_account_id.bankintegration_acc_number:
                if not len(self.bank_account_id.acc_number) == 14:
                    _logger.error('The bank account linked to journal {journal} in company {company} has an invalid acc_number {bank_acc}, which is only {bank_acc_len} digits long'.format(journal=self.name, company=self.company_id.display_name, bank_acc=self.bank_account_id.acc_number, bank_acc_len=len(self.bank_account_id.acc_number)))
                    return False
            elif not len(self.bank_account_id.bankintegration_acc_number) == 14:
                _logger.error('The bank account linked to journal {journal} in company {company} has an invalid bankintegration_acc_number {bank_acc}, which is only {bank_acc_len} digits long'.format(journal=self.name, company=self.company_id.display_name, bank_acc=self.bank_account_id.bankintegration_acc_number, bank_acc_len=len(self.bank_account_id.bankintegration_acc_number)))
                return False
                
        return True

    def get_bankintegration_acc_number(self):
        self.ensure_one()
        return self.bank_account_id.bankintegration_acc_number or self.bank_account_id.acc_number
    
    def _get_last_bank_statement(self):
        self.ensure_one()
        if not self.type == 'bank':
            return False
        # Get last bank statement based on the date, as doing it based on ID is not reliable enough when users are allowed to manually create statements
        bank_statement_id = self.env['account.bank.statement'].search([('journal_id', '=', self.id)], limit=1, order='date desc')
        if bank_statement_id.id:
            return bank_statement_id
        else:
            _logger.error('For first time import please make a starting statement, with ending balance filled out, and a unposted transaction with starting reference number.')
            return False

    def cron_bankintegration_bank_statement_import(self):
        for company in self.env['res.company'].search([]):
            # Validate if we should even process data for this company
            if not company.has_valid_bankintegration_config():
                continue
            # Process all journals in the company, where bankintegration has been set as the source
            for journal in self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', company.id), ('bank_statements_source', '=', 'bankintegration_import'), ('customer_code','!=', False)]):
                # Validate if we should process the specific account.journal entry
                if not journal.has_valid_bankintegration_config():
                    continue
                BankIntegrationRequest = self.env['bank.integration.request']
                AccountBankStatementImport = self.env['account.bank.statement.import']
                last_bank_statement = journal._get_last_bank_statement()
                if not last_bank_statement:
                    continue
                if last_bank_statement.date == fields.Date.today(self):
                    _logger.warn('There are no new transactions to import, as transactions have already been imported once today')
                    continue
                request = BankIntegrationRequest.create({
                    'journal_id': journal.id,
                    'company_id': company.id
                })
                request.set_request_id()
                auth_header = request.get_bank_statement_token()
                bank_statement, errors = request.get_bank_statements(auth_header, last_bank_statement, is_scheduler=True)
                if not 'statement' in bank_statement:
                    _logger.error('No transactions to process')
                    errors.append(_('There are no transactions to process in the period from %s to %s' % (bank_statement['from_date'], bank_statement['to_date'])))
                if errors:
                    _logger.error('There were errors during processing on the journal {journal} in company {company}:\n{errors}'.format(journal=journal.name, company=company.display_name, errors=errors))
                    continue
                statement_ids, errors = AccountBankStatementImport.bankintegration_import_statements(bank_statement, is_scheduler=True)
                if errors:
                    _logger.error('There were errors during processing on the journal {journal} in company {company}:\n{errors}'.format(journal=journal.name, company=company.display_name, errors=errors))
                    continue
                
    def action_bankintegration_import_now(self):
        for record in self:
            # Validate if we should even process data for this company
            if not record.company_id.has_valid_bankintegration_config():
                raise UserError(_('Journal %s for company %s could not be processed as the ERP provider and Bankintegration.dk API key are not defined' % (record.name, record.company_id.display_name)))
            # Validate if we should process the specific account.journal entry
            if not record.has_valid_bankintegration_config():
                raise UserError(_('The configuration of the journal %s is not valid for use with bankintegration.dk. Please check that your integration code and bank account details are correctly configured'))
            BankIntegrationRequest = self.env['bank.integration.request']
            AccountBankStatementImport = self.env['account.bank.statement.import']
            last_bank_statement = record._get_last_bank_statement()
            if not last_bank_statement:
                raise ValidationError(_('For first time import please make a starting statement, with ending balance filled out, and a unposted transaction with starting reference number'))
            if last_bank_statement.date == fields.Date.today(self):
                raise UserError(_('There are no new transactions to import, as transactions have already been imported once today'))
            request = BankIntegrationRequest.create({
                'journal_id': record.id,
                'company_id': record.company_id.id
            })
            request.set_request_id()
            auth_header = request.get_bank_statement_token()
            bank_statement, errors = request.get_bank_statements(auth_header, last_bank_statement, is_scheduler=False)
            if not 'statement' in bank_statement:
                errors.append(_('There are no transactions to process in the period from %s to %s' % (bank_statement['from_date'], bank_statement['to_date'])))
            if errors:
                raise ValidationError(_('There were errors during processing on the journal %s in company %s:\n%s' %(record.name, record.company_id.display_name, "\n".join(errors))))
            action = AccountBankStatementImport.bankintegration_import_statements(bank_statement, is_scheduler=False)
            return action

    def action_send_bankintegration_payments(self):
        for record in self:
            # Validate if we should even process data for this company
            if not record.company_id.has_valid_bankintegration_config():
                continue
            # Validate if we can even process payments out of the payment journal configured on the company
            if not record.has_valid_bankintegration_config():
                continue
            # Process all vendor bills in the company, which are to be paid using bankintegration today
            AccountInvoice = self.env['account.invoice']
            vendor_bill_domain = AccountInvoice._get_bankintegration_vendorbill_domain(record.company_id)
            bills = AccountInvoice.search(vendor_bill_domain)
            bills._pay_with_bankintegration(is_scheduler=False)

                
