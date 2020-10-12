# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_bank import sanitize_account_number
import logging
_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def bankintegration_import_statements(self, bank_statement, is_scheduler=False):
        errors = []
        statement_ids = []
        # Validate that the data from bankintegration was correctly transformed before we attempt to load it
        self._check_parsed_data(bank_statement['statement'])
        # Find currency and journal in Odoo
        sanitized_account_number = sanitize_account_number(bank_statement['account'])
        currency_id = self.env['res.currency'].search([('name', '=ilike', bank_statement['currency'])], limit=1)
        journal_id = self.env['account.journal'].search([('bank_account_id.bankintegration_acc_number', '=', sanitized_account_number)])
        if not journal_id:
            journal_id = self.env['account.journal'].search([('bank_account_id.sanitized_acc_number', '=', sanitized_account_number)])
        # If either one is missing, then we cannot proceed
        if not journal_id:
            errors.append(_('A journal with bank account %s, could not be found' % bank_statement['account']))
        if journal_id:
            if not currency_id:
                currency_id = journal_id.currency_id
        if errors:
            if is_scheduler:
                return statement_ids, errors
            else:
                raise ValidationError("\n".join(errors))
        if journal_id.currency_id:
            if currency_id.id != journal_id.currency_id.id:
                error = _('The currency of the bank statement (%s) is not the same as the currency of the journal (%s).') % (currency_id.name, journal_id.currency_id.name)
                if is_scheduler:
                    _logger.error(error)
                    errors.append(error)
                    return statement_ids, errors
                else:
                    raise UserError(error)
        if not journal_id.default_debit_account_id or not journal_id.default_credit_account_id:
            error = _('You have to set a Default Debit Account and a Default Credit Account for the journal: %s') % (journal_id.name,)
            if is_scheduler:
                _logger.error(error)
                errors.append(error)
                return statement_ids, errors
            else:
                raise UserError(error)
        # Prepare statement data to be used for bank statements creation
        bank_statement = self._complete_stmts_vals(bank_statement['statement'], journal_id, bank_statement['account'])
        # Create the bank statements
        statement_ids, notifications = self._create_bank_statements(bank_statement)
        # Finally dispatch to reconciliation interface if method was executed from the UI
        if is_scheduler:
            return statement_ids, errors
        else:
            action = self.env.ref('account.action_bank_reconcile_bank_statements')
            return {
                'name': action.name,
                'tag': action.tag,
                'context': {
                    'statement_ids': statement_ids,
                    'notifications': notifications
                },
                'type': 'ir.actions.client',
            }
        

