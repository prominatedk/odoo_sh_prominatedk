from odoo import _, api, fields, models
import logging

_logger = logging.getLogger(__name__)

class IntrastatReport(models.AbstractModel):
    _inherit = 'account.sales.report'

    
    def _get_columns_name(self, options):
        return [
            {'name': ''},
            {'name': _('VAT')},
            {'name': _('Country Code')},
            {'name': _('Value'), 'class': 'number'},
            {'name': _('Fiscal Position')},
        ]

    @api.model
    def _prepare_query(self, options):
        query = """
            SELECT
                fisc.name AS fiscal_position,
                move.id AS move_id,
                move.partner_id,
                COALESCE(partner.name, commercial_partner.name) AS partner_name,
                partner.vat AS partner_vat,
                country.code AS country_code,
                move.currency_id AS currency_id,
                move.date AS date,
                move.amount_total_signed AS total_balance
            FROM account_move move
                LEFT JOIN account_fiscal_position fisc ON move.fiscal_position_id = fisc.id 
                LEFT JOIN res_partner partner ON move.partner_id = partner.id
                LEFT JOIN res_company company ON move.company_id = company.id
                LEFT JOIN res_partner company_partner ON company_partner.id = company.partner_id
                LEFT JOIN res_country country ON partner.country_id = country.id
                LEFT JOIN res_partner commercial_partner ON move.commercial_partner_id = commercial_partner.id
            WHERE move.state = 'posted'
                AND country.intrastat = TRUE AND (country.code != 'GB' OR move.date < '2021-01-01')
                AND company_partner.country_id != country.id
                AND move.company_id = %s
                AND COALESCE(move.date, move.invoice_date) BETWEEN %s AND %s
                AND move.move_type IN ('out_invoice', 'out_refund')
                AND partner.vat IS NOT NULL
                AND move.journal_id IN %s
        """
        # Date range
        params = [self.env.company.id, options['date']['date_from'], options['date']['date_to']]

        # Filter on selected journals
        journal_ids = self.env['account.journal'].search([('type', 'in', ('sale', 'purchase'))]).ids
        if options.get('journals'):
            journal_ids = [c['id'] for c in options['journals'] if c.get('selected')] or journal_ids
        params.append(tuple(journal_ids))

        return query, params

    @api.model
    def _get_lines(self, options, line_id=None):
        self.env['account.move.line'].check_access_rights('read')
        query, params = self._prepare_query(options)

        self._cr.execute(query, params)
        query_res = self._cr.dictfetchall()

        partners_values = {}
        total_value = 0

        # Aggregate total amount for each partner.
        # Take care of the multi-currencies.
        for vals in query_res:
            name = f"{vals['partner_name']} - {vals['fiscal_position']}"
            if name not in partners_values:
                partners_values[name] = {
                    'value': vals['total_balance'],
                    'partner_id': vals['partner_id'],
                    'partner_name': vals['partner_name'],
                    'partner_vat': vals['partner_vat'],
                    'country_code': vals['country_code'],
                    'fiscal_position': vals['fiscal_position'] if vals['fiscal_position'] else 'None'
                }
            else:
                partners_values[name]['value'] += vals['total_balance']
            total_value += vals['total_balance']
            
        lines = [self._create_sales_report_line(options, partners_values[partner_name]) for partner_name in sorted(partners_values)]

        # Create total line
        lines.append({
            'id': 0,
            'name': _('Total'),
            'class': 'total',
            'level': 2,
            'columns': [{'name': v} for v in [self.format_value(total_value)]],
            'colspan': 3,
        })
        _logger.info(lines)
        return lines

    @api.model
    def _create_sales_report_line(self, options, vals):
        return {
            'id': vals['partner_id'],
            'caret_options': 'res.partner',
            'model': 'res.partner',
            'name': vals['partner_name'],
            'columns': [{'name': c} for c in [
                vals['partner_vat'], vals['country_code'], self.format_value(vals['value']), vals['fiscal_position']]
            ],
            'level': 2,
        }