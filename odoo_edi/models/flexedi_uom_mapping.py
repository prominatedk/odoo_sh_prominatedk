from odoo import models, fields

class FlexediUomMapping(models.Model):
    _name = 'flexedi.uom.mapping'
    _description = 'UoM mapping for FlexEDI'

    uom_id = fields.Many2one('uom.uom', string="Unit of Measure", required=True)
    edi_uom_id = fields.Many2one('odoo_edi.product.uom', string="EDI Counterpart", required=True)
    company_id = fields.Many2one('res.company', required=True)