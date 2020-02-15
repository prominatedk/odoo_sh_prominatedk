# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo import _


class EDICompany(models.Model):
    _inherit = 'res.company'

    userid = fields.Integer()
    password = fields.Char()
    orders_as_draft = fields.Boolean('Import orders as draft')
    link_delivery = fields.Boolean('Link deliveries to salesorder')
    send_all_orders = fields.Boolean('Send all orders')
    send_all_desadv = fields.Boolean('Send all despatch advices')
    send_all_invoic = fields.Boolean('Send all invoices')
    send_all_purchase = fields.Boolean('Send all purchase orders')
    errormail = fields.Char('Error mail')
