# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    json_log = fields.Text(string='Log')