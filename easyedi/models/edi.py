from odoo import models,fields,api

class edi(models.TransientModel):

    _inherit = "res.config.settings"


    userid = fields.Integer(related="company_id.userid")
    password = fields.Char(related="company_id.password")
    orders_as_draft = fields.Boolean('Import orders as draft',related="company_id.orders_as_draft")
    link_delivery = fields.Boolean('Link deliveries to salesorder',related="company_id.link_delivery")
    send_all_orders = fields.Boolean('Send all orders',related="company_id.send_all_orders")
    send_all_desadv = fields.Boolean('Send all despatch advices',related="company_id.send_all_desadv")
    send_all_invoic = fields.Boolean('Send all invoices',related="company_id.send_all_invoic")
    send_all_purchase = fields.Boolean('Send all purchase orders',related="company_id.send_all_purchase")
    errormail = fields.Char(related="company_id.errormail")

class EdiCustomFields(models.Model):
    _name = "edi.fields"

    e_model = fields.Many2one('ir.model',string="Model",required=True)
    e_fieldname = fields.Many2one('ir.model.fields',string="Field Name",required=True)
    e_fieldtype = fields.Selection(selection='_get_field_types', string='Field Type')

    @api.model
    def _get_field_types(self):
        return sorted((key, key) for key in fields.MetaField.by_type)

    @api.onchange('e_fieldname')
    def onchange_fieldname(self):
        if self.e_fieldname:
            self.e_fieldtype = self.e_fieldname.ttype

