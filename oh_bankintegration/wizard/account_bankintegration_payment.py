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
            return self.env['account.move'].browse(active_ids)

    invoice_ids = fields.Many2many(
        'account.move', default=_default_invoice_ids, ondelete='cascade')

    def action_pay_with_bankintegration(self):
        self.ensure_one()
        if any([record.bankintegration_payment_status in ['created', 'pending', 'accepted', 'success', 'rejected', 'failed', 'not_found'] for record in self.invoice_ids]):
            raise UserError(
                _('One or more of the selected invoices are already under payment with bankintegration'))

        if any([record.state != 'posted' for record in self.invoice_ids]):
            raise UserError(
                _('One or more of the selected invoices has not yet been validated/posted'))

        if not all([record.bankintegration_payment_journal_id.id == self.invoice_ids[0].bankintegration_payment_journal_id.id for record in self.invoice_ids]):
            # We have mixed journals
            journals = []
            # Fetch all journals
            # NOTE: The double loop below might not necessarily be the best
            # solution as it will have performance issues on larger datasets
            for record in self.invoice_ids:
                if not record.bankintegration_payment_journal_id in journals:
                    journals.append(record.bankintegration_payment_journal_id)
            for journal in journals:
                invoices = self.invoice_ids.filtered(
                    lambda x: x.bankintegration_payment_journal_id.id == journal.id)
                invoices._pay_with_bankintegration(journal, is_scheduler=False)

        else:
            # All invoices have the same journal. Process the entire recordset
            # at once
            self.invoice_ids._pay_with_bankintegration(
                self.invoice_ids[0].bankintegration_payment_journal_id, is_scheduler=False)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoices have been marked for payment with bankintegration.dk'),
                'message': _('The following invoices have been succesfully marked as being paid using bankintegration.dk: %s' % (", ".join([record.name for record in self.invoice_ids]),)),
                'sticky': False,
                'type': 'success'
            }
        }
