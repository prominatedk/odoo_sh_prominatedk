from odoo import models, fields, api, _

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    origin_country_id = fields.Many2one('res.country')

    @api.model
    def _get_fpos_by_origin_country(self, origin_country_id, country_id=False, state_id=False, zipcode=False, vat_required=False):
        """
        Reimplements logic from _get_fpos_by_region, but allows passing a country of origin to use instead of the company origin country
        """
        if not country_id:
            return False
        base_domain = [
            ('auto_apply','=', True),
            ('vat_required', '=', vat_required),
            ('origin_country_id', '=', origin_country_id),
            ('company_id', 'in', [self.env.company_id, False])
        ]
        null_state_domain = state_domain = [('state_ids', '=', False)]
        null_zip_domain = zip_domain = [('zip_from', '=', False), ('zip_to', '=', False)]
        null_country_domain = [('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]
        
        if state_id:
            state_domain = [('state_ids', '=', state_id)]
        
        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_country_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        # return records that best match the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_domain + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_domain, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_domain + null_zip_domain, limit=1)
        
        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_country_group + null_state_domain + null_zip_domain, limit=1)
        
        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_domain, limit=1)

        return fpos


    @api.model
    def get_fiscal_position_by_origin_country(self, origin_country_id, partner_id, delivery_id=None):
        """
        Reimplements the logic from get_fiscal_position, but with support for accepting an origin country
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner_id:
            return self.env['account.fiscal.position']
        
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)
        delivery = PartnerObj.browse(delivery_id) if delivery_id else partner

        company = self.env.company
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        if company.vat and delivery.vat:
            intra_eu = company.vat[:2] in eu_country_codes and delivery.vat[:2] in eu_country_codes
            vat_exclusion = company.vat[:2] == delivery.vat[:2]
        
        # partner manually set fiscal position always win as per Odoo standard, but not here as we want it to change

        # First search only matching VAT positions
        vat_required = bool(delivery.vat)
        fpos = self._get_fpos_by_origin_country(origin_country_id, delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required)

        return fpos or self.env['account.fiscal.position']


        