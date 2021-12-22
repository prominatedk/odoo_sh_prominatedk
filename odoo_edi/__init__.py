# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID, _
import logging
_logger = logging.getLogger(__name__)

# TODO: Build post_init_hook for linking uom.uom records to flexedi.uom.uom records

def _post_install_hook_map_uom(cr, registry):
    """
    This method is executed after the installation of the module.
    It serves the purpose of populating a mapping table between uom.uom and odoo_edi.uom
    We cannot use a data file here, as sometimes users have deleted standard records from uom.uom
    causing loading of a data file to fail when trying to map these together.
    This method will check for the existence of each standard uom.uom record and map it
    to the corresponding odoo_edi.uom record.
    If a uom.uom record does not exist, we skip the mapping
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Populate a dict of known standard uom.uom records with the full xmlid as the key
    # Build on latest iteration of uom_data.xml for 14.0 branch:
    # https://github.com/odoo/odoo/blob/4882902278c88922f62f19c7cb16ae38326a27bd/addons/uom/data/uom_data.xml
    # If this is changed in a later commit to the 14.0 branch, the below mapping is to be updated, but the change will only affect new installs of the module
    mapping = {
        'uom.product_uom_unit': 'odoo_edi.edi_EA',
        'uom.product_uom_dozen': 'odoo_edi.edi_DZN',
        'uom.product_uom_kgm': 'odoo_edi.edi_KGM',
        'uom.product_uom_gram': 'odoo_edi.edi_GRM',
        'uom.product_uom_day': 'odoo_edi.edi_DAY',
        'uom.product_uom_hour': 'odoo_edi.edi_HUR',
        'uom.product_uom_ton': 'odoo_edi.edi_TNE',
        'uom.product_uom_meter': 'odoo_edi.edi_MTR',
        'uom.product_uom_km': 'odoo_edi.edi_KTM',
        'uom.product_uom_cm': 'odoo_edi.edi_CMT',
        'uom.product_uom_litre': 'odoo_edi.edi_LTR',
        'uom.product_uom_cubic_meter': 'odoo_edi.edi_MTQ',
        # Americanization of units of measure
        'uom.product_uom_lb': 'odoo_edi.edi_LBR',
        'uom.product_uom_oz': 'odoo_edi.edi_EA',
        'uom.product_uom_inch': 'odoo_edi.edi_INH',
        'uom.product_uom_foot': 'odoo_edi.edi_FOT',
        'uom.product_uom_mile': 'odoo_edi.edi_SMI',
        'uom.product_uom_floz': 'odoo_edi.edi_OZA',
        'uom.product_uom_qt': 'odoo_edi.edi_QT',
        'uom.product_uom_gal': 'odoo_edi.edi_GLL',
        'uom.product_uom_cubic_inch': 'odoo_edi.edi_INQ',
        'uom.product_uom_cubic_foot': 'odoo_edi.edi_FTQ'
    }

    # Create a list with all uom.uom records
    uom_xml_ids = env['ir.model.data'].search([('model', '=', 'uom.uom'), ('module', '=', 'uom')])

    uom_edi_default_mappings = []

    company_ids = env['res.company'].sudo().search([]).ids

    for xmlid in uom_xml_ids:
        # Fetch the uom.uom record from the database based on the res_id from the xmlid record
        uom = env['uom.uom'].browse(xmlid.res_id)
        edi_uom = env.ref(mapping[xmlid.complete_name])
        # Check if it exists and if not, it is flushed from the Odoo cache
        if uom.exists():
            if edi_uom.exists():
                uom.write({'edi_product_uom_id': edi_uom.id})
                for company in company_ids:
                    uom_edi_default_mappings.append({
                        'uom_id': uom.id,
                        'edi_uom_id': edi_uom.id,
                        'company_id': company
                    })
            else:
                _logger.warning('EDI Unit "{}" does not exist and can therefore not be mapped to "{}"'.format(
                    mapping[xmlid],
                    xmlid
                ))
        else:
            _logger.warning('Unit of Measure with XMLID "{}" does not exist. It will be skipped'.format(xmlid))
    
    # Add mappings for UoM to EDI UoM for alle created companies
    env['flexedi.uom.mapping'].create(uom_edi_default_mappings)