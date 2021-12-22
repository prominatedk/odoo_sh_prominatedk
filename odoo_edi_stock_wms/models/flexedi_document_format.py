from odoo import models, fields, api, _

class FlexediDocumentFormat(models.Model):
    _inherit = 'flexedi.document.format'

    def _validate_flexedi_wms_picking(self, document):
        result = {
            'valid': [],
            'blocking': False,
            'messages': []
        }

        # TODO: Add generic validation rules

        return result