from odoo import models, fields, api, _

class FlexEdiStatusEndpoint(models.Model):
    _name = 'flexedi.document.status.endpoint'
    _description = 'FlexEDI Status Endpoint'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    endpoint = fields.Char(required=True)
    model = fields.Char(required=True)