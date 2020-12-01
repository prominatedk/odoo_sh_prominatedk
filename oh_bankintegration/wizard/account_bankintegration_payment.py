from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountBankintegrationPayment(models.TransientModel):
    _name = 'account.bankintegration.payment'
    _description = 'Pay selected invoices with bankintegration'

    def _default_invoice_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return False
        else:
            return self.env['account.invoice'].browse(active_ids)

    invoice_ids = fields.Many2many('account.invoice', default=_default_invoice_ids, ondelete='cascade')

    def action_pay_with_bankintegration(self):
        self.ensure_one()
        if any([record.payment_status in ['created', 'pending', 'accepted', 'success', 'rejected', 'failed', 'not_found'] for record in self.invoice_ids]):
            raise UserError(_('One or more of the selected invoices are already under payment with bankintegration'))
        
        if any([record.state != 'open' for record in self.invoice_ids]):
            raise UserError(_('One or more of the selected invoices has not yet been validated'))

        if not all([record.payment_journal.id == self.invoice_ids[0].payment_journal.id for record in self.invoice_ids]):
            # We have mixed journals
            journals = []
            # Fetch all journals
            # NOTE: The double loop below might not necessarily be the best solution as it will have performance issues on larger datasets
            for record in self.invoice_ids:
                if not record.payment_journal in journals:
                    journals.append(record.payment_journal)
            for journal in journals:
                invoices = self.invoice_ids.filtered(lambda x: x.payment_journal.id == journal.id)
                invoices._pay_with_bankintegration(journal, is_scheduler=False)

        else:
            # All invoices have the same journal. Process the entire recordset at once
            self.invoice_ids._pay_with_bankintegration(self.invoice_ids[0].payment_journal, is_scheduler=False)

        return {}