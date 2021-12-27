# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    odoo_edi_token = fields.Char(string='EDI API Key', help='Define the API Key that is used for FlexEDI')
    gln = fields.Char(string='GLN number', help='GLN identification number of the company. This can also be called the EAN identifier/number')
    edi_mode = fields.Selection(string="EDI Operation mode", help="Choose how we handle EDI connections. Option 'Production' for running against a production environment and sending real documents to real customers. Option 'Test' is to send documents to the testing environment where data is processed but not actually sent. Option 'Development/Debug' is used when we do not want to contact a server, which results in the file just being dumped locally on the server",
                                selection=[('production', 'Production'), ('test', 'Test'), ('development', 'Development/Debugging')])
    edi_registration = fields.Selection(string="EDI Registration", selection=[('vat', 'CVR'), ('gln', 'GLN/EAN')], default='vat')

    flexedi_uom_mapping_ids = fields.One2many('flexedi.uom.mapping', 'company_id')
    
    def is_valid_for_flexedi(self):
        """
        Check if company-level configuration is generally OK.
        :returns dict: A dictionary with error state and messages
        Example:
        {
            'valid': True, # General state on whether the company configuration is valid or not
            'messages': [...] # List of error messages
        }
        """
        self.ensure_one()
        result = {
            'valid': [],
            'messages': []
        }
        if not self.country_id:
            result['valid'].append(False)
            result['messages'].append(
                _('A country has not been set on %s' % (self.display_name,))
            )
        else:
            result['valid'].append(True)
        if not self.odoo_edi_token:
            result['valid'].append(False)
            result['messages'].append(
                _('The authentication key / API Key for FlexEDI has not been provided for %s' % (self.display_name,))
            )
        else:
            result['valid'].append(True)

        result['valid'] = all(result['valid'])
        
        return result

    def get_uom_from_edi_unit(self, unit, category_id):
        self.ensure_one()
        for uom in self.flexedi_uom_mapping_ids:
            if uom.edi_uom_id.name == unit and uom.uom_id.category_id.id == category_id:
                return uom.uom_id