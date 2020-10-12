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

        self.invoice_ids._pay_with_bankintegration(is_scheduler=False)

        return {}