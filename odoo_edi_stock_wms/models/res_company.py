from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    flexedi_wms_autovalidate_done = fields.Boolean(string='Automatically validate pickings from WMS', help='Checking this will automatically validate any pickings recieving data from the WMS, if all moves are fully processed.\nIf one or more moves trigger a confirmation dialog or a backorder, nothing is validated')
    