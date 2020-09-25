# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    gln = fields.Char(string='GLN number', help='GLN identification number of the partner. This can also be called the EAN identifier/number')

    odoo_edi_send_enable = fields.Boolean(
        string='Enable EDI communication with this partner',
        help='Enabling this option allows you to choose which documents to exchange with partners using EDI'
    )

    @api.model
    def create(self, values):
        if 'gln' in values and values['gln']:
            values['odoo_edi_send_enable'] = True

        record = super(ResPartner, self).create(values)
        return record
    
