# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    payment_margin = fields.Integer(string=_('Payment Margin'), help="Payment Margin", default=0)
    autopay = fields.Boolean(string=_('Default auto pay'), default=False)
    set_validate_payment = fields.Boolean(string=_('Set for payment after validate?'), default=False)
    payment_journal = fields.Many2one('account.journal', string='Payment journal', domain="[('type', '=', 'bank')]")
    erp_provider = fields.Char(string='ERP Provider', help="Please enter ERP Provider name.")
    bi_api_key = fields.Char(string='API Key', help="Please enter API Key.")
    use_note_msg = fields.Boolean(string=_('Use note as label?'), default=False)
    check_payment_status = fields.Boolean(string=_('Check payment status on payment.'), default=False)
    use_bban = fields.Boolean(string=_('Use odoo bban'), default=False)
    use_extended_import = fields.Boolean(string=_('Use extended import?'), default=False)

    def has_valid_bankintegration_config(self):
        self.ensure_one()
        if not self.erp_provider or not self.bi_api_key:
            _logger.error('Company {company} could not be processed as the ERP provider and Bankintegration.dk API key are not defined'.format(company=self.display_name))
            return False
        if not self.payment_journal:
            _logger.error('Company {company} could not be processed as no payment journal has been defined'.format(company=self.display_name))
            return False
        return True