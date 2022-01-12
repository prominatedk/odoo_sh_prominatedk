# TODO: Build migration script to map UOM definitions
import logging
from odoo.sql_db import Cursor
_logger = logging.getLogger(__name__)

def migrate(cr: Cursor, version):
    cr.execute("SELECT id FROM res_company")
    company_ids = [c['id'] for c in cr.dictfetchall()]
    
    cr.execute("SELECT id, edi_product_uom_id FROM uom_uom;")    
    for uom in cr.dictfetchall():
        for company in company_ids:
            cr.execute("INSERT INTO flexedi_uom_mapping (uom_id, edi_uom_id, company_id) VALUES(%d, %d, %d)", [uom['id'], uom['edi_productuom_id'], company])
