from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

class IntrastatReport(models.AbstractModel):
    _inherit = 'account.intrastat.report'

    def _get_columns_name(self, options):
        res = super(IntrastatReport, self)._get_columns_name(options)
        res += [{
            'name': _('Fiscal Position')
        }]
        return res

    def _create_intrastat_report_line(self, options, vals):
        res = super(IntrastatReport, self)._create_intrastat_report_line(options, vals)
        res += [{'name': c} for c in [
            vals['fiscal_position']
        ]]
        return res

    @api.model
    def _build_query(self, date_from, date_to, journal_ids, invoice_types=None, with_vat=False):
        res = super(IntrastatReport, self)._build_query(date_from, date_to, journal_ids, invoice_types=invoice_types, with_vat=with_vat)
        res['select'] += '''
            inv.fiscal_position_id as fiscal_position
        '''