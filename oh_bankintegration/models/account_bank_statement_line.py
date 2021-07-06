# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import re


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    json_log = fields.Text(string='Log')

    # Function to if two float values are same or not
    def isclose(self, a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    # Get invoice number from text
    def get_invoice_number(self, invoice_text):
        invoice_text_list = invoice_text.split(',')
        invoice_str = []
        if invoice_text_list:
            for invoice_text_item in invoice_text_list:
                invoice_text_item = invoice_text_item.replace('.', ' ')
                invoice_list = invoice_text_item.strip(' ').split(' ')
                if invoice_list:
                    for invoice_item in invoice_list:
                        #invoice_item = re.sub("[^0-9]", "", invoice_item)
                        invoice_item = invoice_item.lstrip('0')
                        if invoice_item:
                            invoice_str.append(invoice_item)
                            if len(invoice_item) > 2:
                                # Remove last char if it is FIK Payment
                                invoice_item = invoice_item[:-1]
                                invoice_str.append(invoice_item)
        return invoice_str

    # get partner id from text and amount
    def get_partner_id(self, stmt_text, stmt_value):
        invoice_type = 'customer'
        if stmt_value < 0:
            invoice_type = 'vendor'
        stmt_value = abs(stmt_value)
        invoice_list = self.get_invoice_number(stmt_text)
        partner = None
        if invoice_list:
            invoice_total = 0
            invoice_line = None
            for invoice_number in invoice_list:
                if invoice_type == 'customer':
                    invoice_line = self.env['account.move'].search(
                        [('name', '=', invoice_number), ('partner_id.customer_rank', '>', 0)])
                else:
                    invoice_line = self.env['account.move'].search(
                        [('name', '=', invoice_number), ('partner_id.supplier_rank', '>', 0)])
                if invoice_line:
                    invoice_total = invoice_total + invoice_line.amount_total
                    if(self.isclose(invoice_line.amount_total, float(stmt_value)) or self.isclose(invoice_total, float(stmt_value))):
                        partner = invoice_line.partner_id.id
                        break
        return partner
