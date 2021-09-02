# -*- coding: utf-8 -*-
import base64
import io
from odoo import api, fields, models, _
import xlsxwriter
import logging
_logger = logging.getLogger(__name__)


class MonthlySalesReport(models.TransientModel):
    _name = 'monthly.sales.report'
    _description = 'XLS and PDF Reports'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True)

    def print_report_xls(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        format_header = workbook.add_format({'font_size': 18, 'bold': True, 'border': 1, 'align': 'Center'})
        table_header = workbook.add_format({'font_size': 12, 'bold': True})
        table_body = workbook.add_format({'font_size': 12})
        table_body1 = workbook.add_format({'font_size': 12, 'align': 'right', 'bold': True})
        table_date = workbook.add_format({'font_size': 12, 'num_format': 'dd-mm-yyyy'})
        table_acc = workbook.add_format({'font_size': 12, 'num_format': '#,##0.00'})

        data = self.env['account.move'].search([('state', '!=', 'draft'),
                                                   ('state', '!=', 'cancelled'),
                                                   ('currency_id', '=', self.currency_id.id),
                                                   ('move_type', '=', 'out_invoice'),
                                                   ('date', '>=', self.date_from),
                                                   ('date', '<=', self.date_to)], order="date")

        sheet = workbook.add_worksheet('Monthly Sales Report')
        sheet.set_column('A:AP', 25)
        sheet.write('A1', 'SP_CODE', table_header)
        sheet.write('B1', 'SP_ORDERNUMBER', table_header)
        sheet.write('C1', 'PROJECT_CODE', table_header)
        sheet.write('D1', 'CUSTOMER_NUMBER', table_header)
        sheet.write('E1', 'CUSTOMER', table_header)
        sheet.write('F1', 'CUSTOMER_UNIT', table_header)
        sheet.write('G1', 'CUSTOMER_DIVISION', table_header)
        sheet.write('H1', 'CUSTOMER_CONTACT', table_header)
        sheet.write('I1', 'CUSTOMER_STREET', table_header)
        sheet.write('J1', 'CUSTOMER_ZIP', table_header)
        sheet.write('K1', 'CUSTOMER_CITY', table_header)
        sheet.write('L1', 'CUSTOMER_COUNTRY', table_header)
        sheet.write('M1', 'CUSTOMER_COSTCENTER', table_header)
        sheet.write('N1', 'CUSTOMER_ORDERNUMBER', table_header)
        sheet.write('O1', 'ORDER_DATE', table_header)
        sheet.write('P1', 'ORDER_COUNTRY', table_header)
        sheet.write('Q1', 'ORDER_SHIPDATE', table_header)
        sheet.write('R1', 'ORDER_CURRENCY', table_header)
        sheet.write('S1', 'DELIVERY_CUSTOMER', table_header)
        sheet.write('T1', 'DELIVERY_DEPARTMENT', table_header)
        sheet.write('U1', 'DELIVERY_ZIP', table_header)
        sheet.write('V1', 'DELIVERY_CITY', table_header)
        sheet.write('W1', 'DELIVERY_COUNTRY', table_header)
        sheet.write('X1', 'INVOICE_DATE', table_header)
        sheet.write('Y1', 'INVOICE_TOTAL', table_header)
        sheet.write('Z1', 'PRODUCT', table_header)
        sheet.write('AA1', 'PRODUCT_CODE', table_header)
        sheet.write('AB1', 'PRODUCT_FAMILY_CODE', table_header)
        sheet.write('AC1', 'PRODUCT_DESCRIPTION', table_header)
        sheet.write('AD1', 'PRODUCT_GROUP', table_header)
        sheet.write('AE1', 'PRODUCT_PRICE', table_header)
        sheet.write('AF1', 'PRODUCT_QUANTITY', table_header)
        sheet.write('AG1', 'PRODUCT_COO', table_header)
        sheet.write('AH1', 'PRODUCT_CUSTOMS_TARIF_NUMBER', table_header)
        sheet.write('AI1', 'PRODUCTLINE_TOTAL', table_header)
        sheet.write('AJ1', 'SALESUNIT_QUANTITY', table_header)
        sheet.write('AK1', 'SUPPLIER', table_header)
        sheet.write('AL1', 'SUPPLIER_AUDIT_STATUS', table_header)
        sheet.write('AM1', 'SLA_STATUS', table_header)
        sheet.write('AN1', 'SLA_PROBLEM', table_header)
        sheet.write('AO1', 'ORDER_TYPE', table_header)
        sheet.write('AP1', 'PRODUCT_BRAND', table_header)
        sheet.write('AQ1', 'CREDIT_NOTES', table_header)

        j = 1

        for item in data.mapped('invoice_line_ids'):
            if item.product_id.default_code not in ['1099', '1098', '1097', '1096', '1095', '1093', '1099', '503', 'Environmental tax - Export'] and item.product_id:
                sheet.write(j, 0, '', table_body) #C
                sheet.write(j, 1, item.move_id.invoice_origin, table_body) # B
                sheet.write(j, 2, item.product_id.x_studio_field_vdINR, table_body) #C
                sheet.write(j, 3, '', table_body) #D
                project_string = str(item.product_id.x_studio_field_vdINR)
                project_codes = project_string.split('_', 1)
                project_code = project_codes[0]
                if item.move_id.partner_id.parent_id and item.move_id.partner_id.parent_id.country_id.name: # E
                    sheet.write(j, 4, project_code + ' ' +
                                str(item.move_id.partner_id.parent_id.country_id.name), table_body)
                elif item.move_id.partner_id.parent_id:
                    sheet.write(j, 4, project_code, table_body)
                elif item.move_id.partner_id.country_id.name:
                    sheet.write(j, 4, project_code + ' ' +
                                str(item.move_id.partner_id.country_id.name), table_body)
                else:
                    sheet.write(j, 4, project_code, table_body)
                sheet.write(j, 5, '', table_body) # F
                sheet.write(j, 6, '', table_body) # G
                if item.move_id.partner_id.mobile:
                    sheet.write(j, 7, item.move_id.partner_id.mobile, table_body) # H
                else:
                    sheet.write(j, 7, '', table_body) # H
                if item.move_id.partner_id.street2:
                    sheet.write(j, 8, item.move_id.partner_id.street + ', ' + item.move_id.partner_id.street2, # I
                                table_body)
                else:
                    sheet.write(j, 8, item.move_id.partner_id.street, table_body) # I
                sheet.write(j, 9, item.move_id.partner_id.zip, table_body) # J
                sheet.write(j, 10, item.move_id.partner_id.city, table_body) # K
                sheet.write(j, 11, item.move_id.partner_id.country_id.code, table_body) # L
                sheet.write(j, 12, '', table_body) # M
                sheet.write(j, 13, '', table_body) # N
                if item.mapped('sale_line_ids'):
                    sheet.write(j, 14, item.mapped('sale_line_ids')[0].order_id.date_order.date(), table_date) # O
                sheet.write(j, 15, item.move_id.partner_id.country_id.code, table_body) # P
                if item.move_id.invoice_origin:
                    shipment = self.env['stock.picking'].search([('sale_id.name', '=', item.move_id.invoice_origin)])
                    shipdates = []
                    for i in shipment:
                        if i.date_done:
                            shipdates.append(i.date_done.strftime("%d-%m-%Y"))
                    shipdate = ",".join(shipdates)
                    sheet.write(j, 16, shipdate, table_body) # Q
                sheet.write(j, 17, item.move_id.currency_id.name, table_body) # R
                sheet.write(j, 18, item.move_id.partner_shipping_id.name, table_body) # S
                sheet.write(j, 19, '', table_body) # T
                sheet.write(j, 20, item.move_id.partner_shipping_id.zip, table_body) # U
                sheet.write(j, 21, item.move_id.partner_shipping_id.city, table_body) # V
                sheet.write(j, 22, item.move_id.partner_shipping_id.country_id.code, table_body) # W
                sheet.write(j, 23, item.move_id.invoice_date, table_date) # X
                sheet.write(j, 24, item.price_subtotal, table_acc) # Y
                sheet.write(j, 25, '', table_body) # Z
                sheet.write(j, 26, item.product_id.default_code, table_body) # AA
                if item.product_id.categ_id.name:
                    try:
                        int(item.product_id.categ_id.name[:2])
                        sheet.write(j, 27, item.product_id.categ_id.name[3:], table_body)
                    except ValueError:
                        sheet.write(j, 27, item.product_id.categ_id.name, table_body) # AB
                sheet.write(j, 28, item.product_id.name, table_body) # AC
                sheet.write(j, 29, item.product_id.x_studio_field_Mj7AZ, table_body) # AD
                sheet.write(j, 30, item.price_unit, table_acc) # AE
                sheet.write(j, 31, item.quantity, table_acc) # AF
                sheet.write(j, 32, item.product_id.x_studio_field_hqRIw, table_body) # AG
                sheet.write(j, 33, item.product_id.x_studio_field_cA6I2, table_body) # AH
                sheet.write(j, 34, item.price_total, table_acc) # AI
                sheet.write(j, 35, '', table_body) # AJ
                sheet.write(j, 36, '', table_body) # AK
                if len(item.product_id.seller_ids) > 0: 
                    if item.product_id.seller_ids[0].name.audited:
                        sheet.write(j, 37, 'Yes', table_body) # AL
                    else:
                        sheet.write(j, 37, 'No', table_body) # AL
                else:
                    sheet.write(j, 37, 'No', table_body) # AL
                sheet.write(j, 38, '', table_body)
                sheet.write(j, 39, '', table_body)
                sheet.write(j, 40, '', table_body)
                sheet.write(j, 41, '', table_body)
                # credit_note = self.env['account.move'].search([('invoice_origin', '=', item.move_id.number),
                #                                                   ('type', '=', 'out_refund')], limit=1)
                # if credit_note:
                #     sheet.write(j, 42, credit_note.number, table_body)
                # else:
                #     sheet.write(j, 42, '', table_body)

                j += 1

        workbook.close()

        attach_id = self.env['monthly.sales.report.excel'].create({
            'name': 'Monthly Sales Report.xlsx',
            'xls_output': base64.encodebytes(output.getvalue())
        })
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'monthly.sales.report.excel',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


class CrmReportExcel(models.TransientModel):
    _name = 'monthly.sales.report.excel'

    xls_output = fields.Binary(string='Excel Output', readonly=True)
    name = fields.Char(string='File Name', help='Save report as .xls format', default='CRM Report.xlsx')
