import base64
import io
from odoo import api, fields, models, _
import xlsxwriter

class MonthlySalesReport(models.TransientModel):
    _name = 'monthly.sales.report'
    _description = 'XLS and PDF Reports'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)

    def print_report_xls(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        format_header = workbook.add_format({'font_size': 18, 'bold': True, 'border': 1, 'align': 'Center'})
        table_header = workbook.add_format({'font_size': 12, 'bold': True})
        table_body = workbook.add_format({'font_size': 12})
        table_body1 = workbook.add_format({'font_size': 12, 'align': 'right', 'bold': True})
        table_date = workbook.add_format({'font_size': 12, 'num_format': 'dd/mm/yyyy'})
        table_acc = workbook.add_format({'font_size': 12, 'num_format': '#,#'})

        data = self.env['sale.order'].search([('date_order', '>=', self.date_from),
                                              ('date_order', '<=', self.date_to)])
        sorted_data = sorted(data, key=lambda x: x.date_order)


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

        j = 1

        for item in sorted_data:
            orderlines = item.order_line
            products = []
            product_codes = []
            product_prices = []
            product_quantities = []
            product_totals = []
            product_categories = []
            parent_categories = []
            commodity_codes = []
            project_codes = []
            coos = []
            for lines in orderlines:
                products.append(lines.product_id.name)
                product_codes.append(str(lines.product_id.default_code))
                product_prices.append(lines.price_unit)
                product_quantities.append(lines.product_uom_qty)
                product_totals.append(lines.price_total)
                product_categories.append(str(lines.product_id.categ_id.name))
                parent_categories.append(str(lines.product_id.categ_id.parent_id.name))
                commodity_codes.append(str(lines.product_id.x_studio_field_cA6I2))
                project_codes.append(str(lines.product_id.x_studio_field_vdINR))
                coos.append(str(lines.product_id.x_studio_field_hqRIw))
            sheet.write(j, 0, '', table_body)
            sheet.write(j, 1, item.name, table_body)
            k = j
            for project_code in project_codes:
                sheet.write(k, 2, project_code, table_body)
                k += 1
            # sheet.write(j, 2, '', table_body)
            sheet.write(j, 3, '', table_body)
            sheet.write(j, 4, item.partner_id.name, table_body)
            sheet.write(j, 5, '', table_body)
            sheet.write(j, 6, '', table_body)
            if item.partner_id.mobile:
                sheet.write(j, 7, item.partner_id.mobile, table_body)
            else:
                sheet.write(j, 7, '', table_body)
            if item.partner_id.street2:
                sheet.write(j, 8, item.partner_id.street + ', ' + item.partner_id.street2, table_body)
            else:
                sheet.write(j, 8, item.partner_id.street, table_body)
            sheet.write(j, 9, item.partner_id.zip, table_body)
            sheet.write(j, 10, item.partner_id.city, table_body)
            sheet.write(j, 11, item.partner_id.country_id.code, table_body)
            sheet.write(j, 12, '', table_body)
            sheet.write(j, 13, '', table_body)
            sheet.write(j, 14, item.date_order, table_date)
            sheet.write(j, 15, item.partner_id.country_id.code, table_body)
            shipment = self.env['stock.picking'].search([('origin', '=', item.name)])
            shipdates = []
            for i in shipment:
                shipdates.append(shipment.scheduled_date.strftime("%m/%d/%Y"))
            shipdate = ",".join(shipdates)
            sheet.write(j, 16, shipdate, table_body)
            sheet.write(j, 17, item.currency_id.name, table_body)
            sheet.write(j, 18, item.partner_shipping_id.name, table_body)
            sheet.write(j, 19, '', table_body)
            sheet.write(j, 20, item.partner_shipping_id.zip, table_body)
            sheet.write(j, 21, item.partner_shipping_id.city, table_body)
            sheet.write(j, 22, item.partner_shipping_id.country_id.code, table_body)
            invoices = self.env['account.invoice'].search([('origin', '=', item.name)])
            invoice_dates = []
            invoice_amounts = []
            for lines in invoices:
                invoice_dates.append(str(lines.date_invoice))
                invoice_amounts.append(str(lines.amount_total))
            invoice_date = ",".join(invoice_dates)
            invoice_amount = ",".join(invoice_amounts)
            if len(invoice_dates) > 0:
                sheet.write(j, 23, invoice_date, table_date)
            else:
                sheet.write(j, 23, '', table_date)
            sheet.write(j, 24, invoice_amount, table_body)
            sheet.write(j, 25, '', table_body)
            k = j
            for product_code in product_codes:
                sheet.write(k, 26, product_code, table_body)
                k += 1
            k = j
            for parent_category in parent_categories:
                sheet.write(k, 27, parent_category, table_body)
                k += 1
            k = j
            for product in products:
                sheet.write(k, 28, product, table_body)
                k += 1
            k = j
            for product_category in product_categories:
                sheet.write(k, 29, product_category, table_body)
                k += 1
            k = j
            for price in product_prices:
                sheet.write(k, 30, price, table_acc)
                k += 1
            k = j
            for quantity in product_quantities:
                sheet.write(k, 31, quantity, table_body)
                k += 1
            k = j
            for coo in coos:
                sheet.write(k, 32, coo, table_body)
                k += 1
            k = j
            for commodity_code in commodity_codes:
                sheet.write(k, 33, commodity_code, table_body)
                k += 1
            k = j
            for total in product_totals:
                sheet.write(k, 34, total, table_acc)
                k += 1
            sheet.write(j, 35, '', table_body)
            sheet.write(j, 36, '', table_body)
            sheet.write(j, 37, '', table_body)
            sheet.write(j, 38, '', table_body)
            sheet.write(j, 39, '', table_body)
            sheet.write(j, 40, '', table_body)
            sheet.write(j, 41, '', table_body)

            if k >= j:
                j = k

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
