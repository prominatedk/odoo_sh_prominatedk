from odoo import models,fields,api

class edi(models.Model):
	_inherit = 'res.partner'


	gln = fields.Char('GLN')
	send_orders = fields.Boolean('Send orderconfirmation')
	send_desadv = fields.Boolean('Send despatch advice')
	send_invoic = fields.Boolean('Send invoices')

