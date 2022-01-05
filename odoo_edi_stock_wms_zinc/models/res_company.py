from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    zinc_wms_auto_create_missing_partner = fields.Boolean(string='Automatically create missing partners', help='If a partner cannot be found during reception of a document\nOdoo will automatically create the partner, if this is required to create the document')
    zinc_wms_origin_identity = fields.Char()
    zinc_wms_document_key = fields.Char(string="Document Shared Key", help='A shared key to use for document exchange')
    zinc_wms_default_warehouse_id = fields.Many2one('stock.warehouse')

    zinc_wms_order_placeholder_contact = fields.Many2one('res.partner')