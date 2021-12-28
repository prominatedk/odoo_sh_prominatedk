from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FlexediDocumentFormatPartner(models.Model):
    _name = 'flexedi.document.format.partner'
    _description = 'FlexEDI Document Format To Partner Mapping'

    partner_id = fields.Many2one('res.partner', required=True)
    model = fields.Selection(string='Type of document', selection=[], ondelete='cascade')
    flexedi_document_format_id = fields.Many2one('flexedi.document.format', string='Document Format', required=True)

    @api.constrains('partner_id', 'model')
    def _check_partner_model_unique(self):
        for record in self:
            existing = self.env['flexedi.document.format.partner'].search([('partner_id', '=', record.partner_id.id), ('model', '=', record.model), ('id', '!=', record.id)])
            if existing.ids:
                raise ValidationError(_('You can only have one document format per partner for %s' % (record.model,)))