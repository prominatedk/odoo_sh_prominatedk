from odoo import models,fields,api

class edi(models.Model):
	_inherit = 'purchase.order'


	ediindate = fields.Date('Incoming EDI Date')
	edioutdate = fields.Date('Outgoing EDI Date')	
	sendedi = fields.Boolean('Sent as EDI')
	