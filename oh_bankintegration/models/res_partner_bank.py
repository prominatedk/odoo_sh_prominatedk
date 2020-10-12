# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
import logging
_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bankintegration_acc_number = fields.Char('Domestic account number', help="For bankintegration insert domestic account number, if IBAN number is used in the Account Number field")