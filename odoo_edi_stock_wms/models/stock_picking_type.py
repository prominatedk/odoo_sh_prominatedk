from odoo import models, fields, api, _

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    use_flexedi = fields.Boolean(string='Use FlexEDI', help='Check this to have the operation type use FlexEDI for picking operations')
    flexedi_document_format_id = fields.Many2one('flexedi.document.format', string='FlexEDI Format')