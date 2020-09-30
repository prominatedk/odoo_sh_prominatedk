# -*- coding: utf-8 -*-
import time
import datetime
from dateutil.relativedelta import relativedelta
import ast
import odoo
from odoo import SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_margin = fields.Integer(string=_('Payment Margin'), help="Payment Margin", related="company_id.payment_margin", readonly=False)
    autopay = fields.Boolean(string=_('Default auto pay'), related="company_id.autopay", readonly=False)
    set_validate_payment = fields.Boolean(string=_('Set for payment after validate?'), related="company_id.set_validate_payment", readonly=False)
    payment_journal = fields.Many2one('account.journal', string='Payment journal', related='company_id.payment_journal', readonly=False)
    erp_provider = fields.Char(string='ERP Provider', help="Please enter ERP Provider name.", related='company_id.erp_provider', readonly=False)
    bi_api_key = fields.Char(string='API Key', help="Please enter API Key.", related='company_id.bi_api_key', readonly=False)
    use_note_msg = fields.Boolean(string=_('Use note as label?'), related='company_id.use_note_msg', readonly=False)
    check_payment_status = fields.Boolean(string=_('Check payment status on payment.'), related='company_id.check_payment_status', readonly=False)
    use_bban = fields.Boolean(string=_('Use odoo bban'), related='company_id.use_bban', readonly=False)
    use_extended_import = fields.Boolean(string=_('Use extended import?'), related='company_id.use_extended_import', readonly=False)