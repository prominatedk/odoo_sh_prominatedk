from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

try:
    from suds.client import Client
    _suds_lib_imported = True

except ImportError:
    _suds_lib_imported = False
    _logger.info(
        "The `suds-jurko` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install suds-jurko` to install it."
    )

import time
import datetime
import smtplib
import sys
from email.mime.text import MIMEText
from io import BytesIO
import traceback


class editransfer(models.Model):

    _name = 'easyedi.transfer'

    @api.model
    def fetch_files(self):
        try:
            url = 'http://web.nemedi.dk/webEDIService/superEDIXWebService.asmx?WSDL'
            client = Client(url)
            _setting = self.env['res.company'].browse(1)
            filecontent = client.service.StreamFile(
                _setting.userid, _setting.password)
            #filecontent = ["filetype;PartnerILN;BuyerILN;DeliveryILN;delivery_date;Barcode;Itemcode;Quantity;Description;Price"]
            # filecontent.append("ORDERS;5662;767;7676;;123;12;12;sdsdasdasd;34")
            # print(filecontent)
            while filecontent != 'No Files':
                lines = filecontent.split('\n')
                header = lines[0]
                fieldnames = header.split(';')
                if lines and len(lines) > 1:
                    firstline = lines[1]
                    fields = firstline.split(';')
                    filetype = fields[0].strip('"')
                    if filetype == 'ORDERS':
                        iln = self._fieldvalue('PartnerILN', fieldnames, fields)
                        partner = self.env['res.partner'].search([('gln', '=', iln)])
                        if not partner:
                            partner = self.env['res.partner'].create({'name': iln, 'gln': iln})
                        buyeriln = self._fieldvalue('BuyerILN', fieldnames, fields)
                        buyer = self.env['res.partner'].search([('gln', '=', buyeriln)])
                        if not buyer:
                            if partner:
                                buyer = partner
                            else:
                                buyer = self.env['res.partner'].create({'name': buyeriln, 'gln': buyeriln})
                        deliveryiln = self._fieldvalue('DeliveryILN', fieldnames, fields)
                        delivery_date = self._fieldvalue('delivery_date', fieldnames, fields)
                        delivery = self.env['res.partner'].search([('gln', '=', deliveryiln)])
                        if not delivery:
                            delivery = self.env['res.partner'].create({'name': deliveryiln, 'gln': deliveryiln})
                        if buyer and delivery:
                            saleorder_vals = {
                                'partner_id': partner.id,
                                'partner_invoice_id': buyer.id,
                                'partner_shipping_id': delivery.id,
                                'ediindate': datetime.date.today()
                            }
                            if delivery_date:
                                saleorder_vals.update({'requested_date': delivery_date})
                            if partner and partner.property_payment_term_id:
                                saleorder_vals.update({'payment_term_id': partner.property_payment_term_id.id})
                            saleorder = self.env['sale.order'].create(saleorder_vals)
                            if _setting.orders_as_draft == False:
                                saleorder.state = 'sale'
                            for x in range(16, len(fields) - 1):
                                if not fieldnames[x].startswith("line"):
                                    setattr(saleorder, fieldnames[x].strip('"'), fields[x].strip('"'))
                            i = 0
                            for line in lines:
                                if i != 0:
                                    if line != '':
                                        fields = line.split(';')
                                        ean = self._fieldvalue('Barcode', fieldnames, fields)
                                        itemcode = self._fieldvalue('Itemcode', fieldnames, fields)
                                        if ean != '':
                                            product = self.env['product.product'].search([('barcode', '=', ean)])
                                        elif itemcode != '':
                                            product = self.env['product.product'].search([('default_code', '=', itemcode)])
                                        if not product:
                                            try:
                                                product = self.env['product.product'].create({'default_code': itemcode, 'barcode': ean, 'name': ean})
                                            except:
                                                saleorder.unlink()
                                                raise ValueError('Cannot create Product as barcode or itemcode not found.')
                                        if product.name == False:
                                            saleorder.unlink()
                                            raise ValueError('Product not found. EAN = ' + ean + ', ItemCode = ' + itemcode)
                                        quantity = self._fieldvalue('Quantity', fieldnames, fields)
                                        description = self._fieldvalue('Description', fieldnames, fields)
                                        if description == '':
                                            description = product.name
                                        price = self._fieldvalue('Price', fieldnames, fields)
                                        if price == '':
                                            price = product.list_price
                                        discount = self._fieldvalue('line_discount', fieldnames, fields)
                                        if discount == '':                                            
                                            product_price = product.list_price
                                            partner_product_price = partner.property_product_pricelist.get_product_price(product,1,partner)
                                            if product_price != partner_product_price:
                                                discount =  (product_price - partner_product_price)/product_price*100

                                        line = self.env['sale.order.line'].create({'order_id': saleorder.id,
                                                                                   'product_id': product.id,
                                                                                   'name': description,
                                                                                   'price_unit': price,
                                                                                   'product_uom': 1,
                                                                                   'product_uom_qty': quantity,
                                                                                   'discount': discount,})
                                        line.tax_id = line.product_id.taxes_id
                                        for x in range(16, len(fields) - 1):
                                            if fieldnames[x].startswith("line"):
                                                setattr(line, fieldnames[x].strip(
                                                    '"'), fields[x].strip('"'))
                                i = i + 1
                    elif filetype == 'DESADVout':
                        iln = self._fieldvalue('PartnerILN', fieldnames, fields)
                        partner = self.env['res.partner'].search([('gln', '=', iln)])
                        buyeriln = self._fieldvalue('BuyerILN', fieldnames, fields)
                        buyer = self.env['res.partner'].search([('gln', '=', buyeriln)])
                        deliveryiln = self._fieldvalue('DeliveryILN', fieldnames, fields)
                        delivery = self.env['res.partner'].search([('gln', '=', deliveryiln)])
                        min_date = self._fieldvalue('Date', fieldnames, fields)
                        ordernumber = self._fieldvalue('OrderNumber', fieldnames, fields)
                        picking = self.env['stock.picking'].search([('origin', '=', ordernumber)])
                        picking.action_confirm()
                    elif filetype == 'INVOIC':
                        jc = 0
                    filecontent = client.service.StreamFile(
                        _setting.userid, _setting.password)
                    #filecontent = 'No Files'
        except ValueError as err:
            msg = MIMEText(err.args[0])
            msg['Subject'] = 'Error from EDI'
            msg['From'] = 'noreply@easyedi.dk'
            msg['To'] = _setting.errormail
            smtp = smtplib.SMTP()
            smtp.connect('mail.nemedi.dk')
            smtp.login('noreply@easyedi.dk', 'secret(5/')
            smtp.sendmail('noreply@easyedi.dk', [
                          _setting.errormail], msg.as_string())
            smtp.quit()
        except:
            e = sys.exc_info()[0]
            msg = MIMEText(traceback.format_exc())
            msg['Subject'] = 'Error from EDI'
            msg['From'] = 'noreply@easyedi.dk'
            msg['To'] = _setting.errormail
            smtp = smtplib.SMTP()
            smtp.connect('mail.nemedi.dk')
            smtp.login('noreply@easyedi.dk', 'secret(5/')
            smtp.sendmail('noreply@easyedi.dk', [
                          _setting.errormail], msg.as_string())
            smtp.quit()

    def _fieldvalue(self, fieldname, field_list, fields):
        i = 0
        for field in field_list:
            if field.strip('"') == fieldname:
                return(fields[i]).strip('"')
            i = i + 1
        return ''
        
    @api.model
    def send_files(self):
        try:
            url = 'http://web.nemedi.dk/webEDIService/superEDIXWebService.asmx?WSDL'
            client = Client(url)
            _setting = self.env['res.company'].browse(1)
            # Sending invoices for partners
            if _setting.send_all_invoic:
                fields = self.env['edi.fields'].search([('e_model.name', '=', 'Invoice')])
                linefields = self.env['edi.fields'].search([('e_model.name', '=', 'Invoice Line')])
                partners = self.env['res.partner'].search([('send_invoic', '=', 'true')])
                for partner in partners:
                    documents = self.env['account.invoice'].search([('partner_id', '=', partner.id), ('state', '=', 'open'), ('sendedi', '!=', True)])
                    if len(documents) > 0:                      
                        filecontent = Filecontent()
                        for document in documents:
                            delivery = self.env['stock.picking'].search([('name', '=', document.origin)])
                            if delivery:
                                if len(delivery) > 1:
                                    delivery = delivery[0]
                                salesorder = delivery.sale_id
                            else:
                                delivery = self.env['stock.picking'].search([('origin', '=', document.origin)])
                                if delivery:
                                    if len(delivery) > 1:
                                        delivery = delivery[0]
                                salesorder = self.env['sale.order'].search([('name', '=', document.origin)])

                            customer = document.partner_id

                            if salesorder:
                                shipping_customer = salesorder.partner_shipping_id
                            else:
                                shipping_customer = document.partner_shipping_id

                            linenum = 1
                            for line in document.invoice_line_ids:
                                filecontent.linenum = linenum
                                #Document Fields
                                if document.type == 'out_invoice':
                                    filecontent.add_document_field('DocType', 'INVOIC')                                    
                                else:
                                    filecontent.add_document_field('DocType', 'CREDIT')
                                filecontent.add_document_field('DocNumber', document.number)
                                #Customer Fields                                
                                filecontent.add_document_field('PartnerILN', customer.gln)      
                                filecontent.add_document_field('BuyerPlace', customer.name)
                                filecontent.add_document_field('BuyerAddress', customer.street)          
                                filecontent.add_document_field('BuyerZIP', customer.zip)  
                                filecontent.add_document_field('BuyerCity', customer.city) 
                                #Shipping Customer Fields
                                filecontent.add_document_field_two('DeliveryILN', shipping_customer, shipping_customer.gln) 
                                filecontent.add_document_field('DeliveryPlace', shipping_customer.name) 
                                filecontent.add_document_field('DeliveryAddress', shipping_customer.street) 
                                filecontent.add_document_field('DeliveryZIP', shipping_customer.zip) 
                                filecontent.add_document_field('DeliveryCity', shipping_customer.city)
                                #Document Fields 2
                                filecontent.add_document_field('DocumentDate', document.date_invoice)
                                filecontent.add_document_field('DocumentDueDat', document.date_due)                               
                                #Sales Order Fields
                                if salesorder:
                                    filecontent.add_document_field('CustomerOrderReference', salesorder.client_order_ref)
                                    filecontent.add_document_field('OrderNumber', salesorder.name)
                                    filecontent.add_document_field('OrderDate', salesorder.date_order)
                                else:
                                    filecontent.add_document_field('CustomerOrderReference', document.name)
                                    filecontent.add_document_field('OrderNumber', document.origin)
                                    filecontent.add_document_field('OrderDate', document.date_invoice)
                                #Delivery Fields
                                filecontent.add_document_field('DeliveryNumber', delivery.name) 
                                filecontent.add_document_field('DeliveryDate', delivery.scheduled_date) 
                                filecontent.add_document_field('DeliveryDate', delivery.scheduled_date) 
                                #Amount
                                filecontent.add_document_field('AmountUntaxed', document.amount_untaxed) 
                                filecontent.add_document_field('AmountTax', document.amount_tax) 
                                filecontent.add_document_field('AmountTaxed', document.amount_total) 
                                filecontent.add_document_field('AmountResidual', document.residual) 
                                #Line Fields
                                filecontent.add_document_field('LineNumber', linenum) 
                                filecontent.add_document_field('EANNumber', line.product_id.barcode) 
                                filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                                filecontent.add_document_field('Quantity', line.quantity) 
                                filecontent.add_document_field('Price', line.price_unit) 
                                filecontent.add_document_field('LineTotal', line.price_subtotal)
                                filecontent.add_document_field('Discount', line.discount)
                                filecontent.add_document_field('Unit', line.uom_id.name)
                                filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                                filecontent.add_document_field('OrderDateCreate', salesorder.create_date)
                                filecontent.add_document_field('OrderDateOrder', salesorder.date_order)
                                filecontent.add_document_field_with_replace('Comment', document.comment)
                                #Custom Fields for order and order line
                                for field in fields:
                                    filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                                for field in linefields:
                                    filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                                #Prepare for next line
                                linenum = linenum + 1
                                filecontent.filecontent_values +='\r\n'
                                
                            document.sendedi = True
                            document.edioutdate = datetime.date.today()
                        filecontent.print_file_content()
                        # result = client.service.UploadString(filecontent, 'INVOIC_' + str(
                        #     datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

            # Orders for partners
            partners = self.env['res.partner'].search([('send_orders', '=', 'true')])
            fields = self.env['edi.fields'].search([('e_model.name', '=', 'Sales Order')])
            linefields = self.env['edi.fields'].search([('e_model.name', '=', 'Sales Order Line')])           
            for partner in partners:
                documents_sale = self.env['sale.order'].search([('partner_id', '=', partner.id), ('state', '=', 'progress'), ('sendedi', '!=', True)])
                documents_manual = self.env['sale.order'].search([('partner_id', '=', partner.id), ('state', '=', 'manual'), ('sendedi', '!=', True)])
                documents = documents_sale + documents_manual
                if len(documents) > 0:                    
                    for document in documents:
                        filecontent = Filecontent()
                        linenum = 1
                        customer = document.partner_id
                        shipping_customer = document.partner_shipping_id
                        for line in document.order_line:
                            filecontent.linenum = linenum
                            #Document Fields
                            filecontent.add_document_field('DocType', 'ORDRSP')
                            filecontent.add_document_field('DocNumber', document.name)
                            #Customer Fields                                
                            filecontent.add_document_field('PartnerILN', customer.gln)      
                            filecontent.add_document_field('BuyerPlace', customer.name)
                            filecontent.add_document_field('BuyerAddress', customer.street)          
                            filecontent.add_document_field('BuyerZIP', customer.zip)  
                            filecontent.add_document_field('BuyerCity', customer.city) 
                            #Shipping Customer Fields
                            filecontent.add_document_field_two('DeliveryILN', shipping_customer, shipping_customer.gln) 
                            filecontent.add_document_field('DeliveryPlace', shipping_customer.name) 
                            filecontent.add_document_field('DeliveryAddress', shipping_customer.street) 
                            filecontent.add_document_field('DeliveryZIP', shipping_customer.zip) 
                            filecontent.add_document_field('DeliveryCity', shipping_customer.city)
                            #Document Fields 2
                            filecontent.add_document_field_two('Incoterms', document.incoterm, document.incoterm.name)
                            filecontent.add_document_field('CustomerOrderReference', document.client_order_ref)
                            #Amount Fields
                            filecontent.add_document_field('AmountUntaxed', document.amount_untaxed) 
                            filecontent.add_document_field('AmountTax', document.amount_tax) 
                            filecontent.add_document_field('AmountTaxed', document.amount_total)
                            #Document Date Fields
                            filecontent.add_document_field('DateCreated', document.create_date)
                            filecontent.add_document_field('DateOrdered', document.date_order)
                            filecontent.add_document_field('DateConfirmed', document.confirmation_date)
                            #Line Fields
                            filecontent.add_document_field('LineNumber', linenum) 
                            filecontent.add_document_field_two('EANNumber', line.product_id, line.product_id.barcode) 
                            filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                            filecontent.add_document_field('Quantity', product_uom_qty) 
                            filecontent.add_document_field('Price', line.price_unit) 
                            filecontent.add_document_field('LineTotal', line.price_subtotal)
                            filecontent.add_document_field('Discount', line.discount)
                            filecontent.add_document_field_two('Unit', line.product_uom, line.product_uom.name)
                            filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                            #Custom Fields for order and order line
                            for field in fields:
                                filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                            for field in linefields:
                                filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                            #Prepare for next line
                            linenum = linenum + 1
                            filecontent.filecontent_values +='\r\n'
                        document.sendedi = True
                        document.edioutdate = datetime.date.today()
                    filecontent.print_file_content()
                    # result = client.service.UploadString(filecontent, 'ORDERS_' + str(
                    #     datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

        # All for partners
            if _setting.send_all_orders:
                fields = self.env['edi.fields'].search([('e_model.name', '=', 'Sales Order')])
                linefields = self.env['edi.fields'].search([('e_model.name', '=', 'Sales Order Line')])                
                documents = self.env['sale.order'].search([('state', '=', 'sale'), ('sendedi', '!=', True)])
                if len(documents) > 0:                    
                    for document in documents:
                        filecontent = Filecontent()
                        linenum = 1
                        customer = document.partner_id
                        shipping_customer = document.partner_shipping_id
                        for line in document.order_line:
                            filecontent.linenum = linenum
                            #Document Fields
                            filecontent.add_document_field('DocType', 'ORDRSP')
                            filecontent.add_document_field('DocNumber', document.name)
                            #Customer Fields                                
                            filecontent.add_document_field('PartnerILN', customer.gln)      
                            filecontent.add_document_field('BuyerPlace', customer.name)
                            filecontent.add_document_field('BuyerAddress', customer.street)          
                            filecontent.add_document_field('BuyerZIP', customer.zip)  
                            filecontent.add_document_field('BuyerCity', customer.city) 
                            #Shipping Customer Fields
                            filecontent.add_document_field_two('DeliveryILN', shipping_customer, shipping_customer.gln) 
                            filecontent.add_document_field('DeliveryPlace', shipping_customer.name) 
                            filecontent.add_document_field('DeliveryAddress', shipping_customer.street) 
                            filecontent.add_document_field('DeliveryZIP', shipping_customer.zip) 
                            filecontent.add_document_field('DeliveryCity', shipping_customer.city)
                            #Document Fields 2
                            filecontent.add_document_field_two('Incoterms', document.incoterm, document.incoterm.name)
                            filecontent.add_document_field('CustomerOrderReference', document.client_order_ref)
                            #Amount Fields
                            filecontent.add_document_field('AmountUntaxed', document.amount_untaxed) 
                            filecontent.add_document_field('AmountTax', document.amount_tax) 
                            filecontent.add_document_field('AmountTaxed', document.amount_total)
                            #Document Date Fields
                            filecontent.add_document_field('DateCreated', document.create_date)
                            filecontent.add_document_field('DateOrdered', document.date_order)
                            filecontent.add_document_field('DateConfirmed', document.confirmation_date)
                            #Line Fields
                            filecontent.add_document_field('LineNumber', linenum) 
                            filecontent.add_document_field_two('EANNumber', line.product_id, line.product_id.barcode) 
                            filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                            filecontent.add_document_field('Quantity', line.product_uom_qty) 
                            filecontent.add_document_field('Price', line.price_unit) 
                            filecontent.add_document_field('LineTotal', line.price_subtotal)
                            filecontent.add_document_field('Discount', line.discount)
                            filecontent.add_document_field_two('Unit', line.product_uom, line.product_uom.name)
                            filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                            #Custom Fields for order and order line
                            for field in fields:
                                filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                            for field in linefields:
                                filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                            #Prepare for next line
                            linenum = linenum + 1
                            filecontent.filecontent_values +='\r\n'
                        document.sendedi = True
                        document.edioutdate = datetime.date.today()
                    filecontent.print_file_content()
                    # result = client.service.UploadString(filecontent, 'ORDERS_' + str(
                    #     datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

        # Delivery notes for partners
            partners = self.env['res.partner'].search([('send_desadv', '=', 'true')])
            fields = self.env['edi.fields'].search([('e_model.name', '=', 'Picking List')])
            linefields = self.env['edi.fields'].search([('e_model.name', '=', 'Stock Move')])            
            for partner in partners:
                documents = self.env['stock.picking'].search([('sendedi', '!=', 'True')])
                if len(documents) > 0:                    
                    found = False
                    for document in documents:
                        filecontent = Filecontent()
                        salesorder = document.sale_id
                        linenum = 1
                        if salesorder != False and salesorder.partner_id == partner:
                            found = True
                            customer = salesorder.partner_id
                            shipping_customer = document.partner_id
                            for line in document.move_lines:
                                filecontent.linenum = linenum
                                #Document Fields
                                filecontent.add_document_field('DocType', 'DESADV')
                                filecontent.add_document_field('DocNumber', document.name)
                                #Customer Fields                                
                                filecontent.add_document_field_two('PartnerILN',customer , customer.gln)      
                                filecontent.add_document_field_two('BuyerPlace',customer , customer.name)
                                filecontent.add_document_field_two('BuyerAddress',customer , customer.street)          
                                filecontent.add_document_field_two('BuyerZIP',customer , customer.zip)  
                                filecontent.add_document_field_two('BuyerCity',customer , customer.city) 
                                #Shipping Customer Fields
                                filecontent.add_document_field_two('DeliveryILN', shipping_customer, shipping_customer.gln) 
                                filecontent.add_document_field_two('DeliveryPlace', shipping_customer, shipping_customer.name) 
                                filecontent.add_document_field_two('DeliveryAddress', shipping_customer, shipping_customer.street) 
                                filecontent.add_document_field_two('DeliveryZIP', shipping_customer, shipping_customer.zip) 
                                filecontent.add_document_field_two('DeliveryCity', shipping_customer, shipping_customer.city)
                                #Salesorder Fields
                                filecontent.add_document_field_two('CustomerOrderReference',salesorder , salesorder.client_order_ref)   
                                filecontent.add_document_field_two('OrderNumber',salesorder , salesorder.name)        
                                #Line Fields
                                filecontent.add_document_field('LineNumber', linenum) 
                                filecontent.add_document_field_two('EANNumber', line.product_id, line.product_id.barcode) 
                                filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                                filecontent.add_document_field('Quantity', line.product_uom_qty)
                                filecontent.add_document_field_two('Unit', line.product_uom, line.product_uom.name)
                                filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                                #Date Fields
                                filecontent.add_document_field('OrderDateCreate', salesorder.create_date)
                                filecontent.add_document_field('OrderDateOrder', salesorder.date_order)
                                filecontent.add_document_field('OrderDateConfirm', salesorder.confirmation_date)
                                #Custom Fields for order and order line
                                for field in fields:
                                    filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                                for field in linefields:
                                    filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                                linenum = linenum + 1
                                filecontent.filecontent_values +='\r\n'
                            document.sendedi = True
                            document.edioutdate = datetime.date.today()
                            filecontent.print_file_content()
                    # if found == True:
                        # result = client.service.UploadString(filecontent, 'DESADV_' + str(
                        #     datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

            # Send All DESADV
            if _setting.send_all_desadv:
                fields = self.env['edi.fields'].search([('e_model.name', '=', 'Picking List')])
                documents = self.env['stock.picking'].search([('sendedi', '!=', 'True'), ('picking_type_code', '=', 'outgoing'), ('state', '=', 'assigned')])
                if len(documents) > 0:                   
                    for document in documents:
                        filecontent = Filecontent()
                        salesorder = document.sale_id
                        linenum = 1
                        if salesorder != False:
                            found = True
                            customer = salesorder.partner_id
                            shipping_customer = document.partner_id
                            for line in document.move_lines:
                                filecontent.linenum = linenum
                                #Document Fields
                                filecontent.add_document_field('DocType', 'DESADV')
                                filecontent.add_document_field('DocNumber', document.name)
                                #Customer Fields                                
                                filecontent.add_document_field_two('PartnerILN',customer , customer.gln)      
                                filecontent.add_document_field_two('BuyerPlace',customer , customer.name)
                                filecontent.add_document_field_two('BuyerAddress',customer , customer.street)          
                                filecontent.add_document_field_two('BuyerZIP',customer , customer.zip)  
                                filecontent.add_document_field_two('BuyerCity',customer , customer.city) 
                                #Shipping Customer Fields
                                filecontent.add_document_field_two('DeliveryILN', shipping_customer, shipping_customer.gln) 
                                filecontent.add_document_field_two('DeliveryPlace', shipping_customer, shipping_customer.name) 
                                filecontent.add_document_field_two('DeliveryAddress', shipping_customer, shipping_customer.street) 
                                filecontent.add_document_field_two('DeliveryZIP', shipping_customer, shipping_customer.zip) 
                                filecontent.add_document_field_two('DeliveryCity', shipping_customer, shipping_customer.city)
                                #Salesorder Fields
                                filecontent.add_document_field_two('CustomerOrderReference',salesorder , salesorder.client_order_ref)   
                                filecontent.add_document_field_two('OrderNumber',salesorder , salesorder.name)        
                                #Line Fields
                                filecontent.add_document_field('LineNumber', linenum) 
                                filecontent.add_document_field_two('EANNumber', line.product_id, line.product_id.barcode) 
                                filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                                filecontent.add_document_field('Quantity', line.product_uom_qty)
                                filecontent.add_document_field_two('Unit', line.product_uom, line.product_uom.name)
                                filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                                #Date Fields
                                filecontent.add_document_field('OrderDateCreate', salesorder.create_date)
                                filecontent.add_document_field('OrderDateOrder', salesorder.date_order)
                                filecontent.add_document_field('OrderDateConfirm', salesorder.confirmation_date)
                                #Custom Fields for order and order line
                                for field in fields:
                                    filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                                for field in linefields:
                                    filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                                linenum = linenum + 1
                                filecontent.filecontent_values +='\r\n'
                            document.sendedi = True
                            document.edioutdate = datetime.date.today()
                            filecontent.print_file_content()
                    # if found == True:
                    #     result = client.service.UploadString(filecontent, 'DESADV_' + str(
                    #         datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

            # Send All Purchase orders

            if _setting.send_all_purchase:
                fields = self.env['edi.fields'].search([('e_model.name', '=', 'Purchase Order')])
                linefields = self.env['edi.fields'].search([('e_model.name', '=', 'Purchase Order Line')])                
                documents = self.env['purchase.order'].search([('sendedi', '!=', 'True'), ('state', '!=', 'purchase')])
                if len(documents) > 0:                    
                    for document in documents:
                        filecontent = Filecontent()
                        supplier = document.partner_id
                        for line in document.move_lines:
                            filecontent.linenum = linenum
                            #Document Fields                            
                            filecontent.add_document_field('DocType', 'ORDRSP')
                            filecontent.add_document_field('DocNumber', document.name)
                            #Customer Fields                                
                            filecontent.add_document_field_two('PartnerILN',supplier , supplier.gln)      
                            filecontent.add_document_field_two('SupplierPlace',supplier , supplier.name)
                            filecontent.add_document_field_two('SupplierAddress',supplier , supplier.street)          
                            filecontent.add_document_field_two('SupplierZIP',supplier , supplier.zip)  
                            filecontent.add_document_field_two('SupplierCity',supplier , supplier.city) 
                            #Document Fields
                            filecontent.add_document_field('PartnerRef', document.partner_ref)
                            filecontent.add_document_field('OrderDate', document.order_date)
                            filecontent.add_document_field('PlannedDate', document.date_planned) 
                            #Line fields
                            filecontent.add_document_field('LineNumber', linenum) 
                            filecontent.add_document_field_two('EANNumber', line.product_id, line.product_id.barcode) 
                            filecontent.add_document_field_with_replace('ItemDescription', line.name) 
                            filecontent.add_document_field('Quantity', line.product_uom_qty)
                            filecontent.add_document_field_two('Unit', line.product_uom, line.product_uom.name)
                            filecontent.add_document_field_two('ItemCode', line.product_id, line.product_id.default_code)
                            #Custom Fields for order and order line
                            for field in fields:
                                filecontent.add_document_field(field.e_fieldname.name, str(eval('document.' + field.e_fieldname.name))+ '"')
                            for field in linefields:
                                filecontent.add_document_field(field.e_fieldname.name,  str(eval('line.' + field.e_fieldname.name)) + '"')
                            linenum = linenum + 1
                            filecontent.filecontent_values +='\r\n'

                            document.sendedi = True
                            document.edioutdate = datetime.date.today()
                            filecontent.print_file_content
                    # result = client.service.UploadString(filecontent, 'ORDERS_' + str(
                    #     datetime.datetime.now()) + '.csv', _setting.userid, _setting.edi_password)

        except ValueError as err:
            msg = MIMEText(err.args[0])
            msg['Subject'] = 'Error from EDI'
            msg['From'] = 'noreply@easyedi.dk'
            msg['To'] = _setting.errormail
            smtp = smtplib.SMTP()
            smtp.connect('mail.nemedi.dk')
            smtp.login('noreply@easyedi.dk', 'secret(5/')
            smtp.sendmail('noreply@easyedi.dk', [
                          _setting.errormail], msg.as_string())
            smtp.quit()
        except:
            e = sys.exc_info()[0]
            msg = MIMEText(traceback.format_exc())
            msg['Subject'] = 'Error from EDI'
            msg['From'] = 'noreply@easyedi.dk'
            msg['To'] = _setting.errormail
            smtp = smtplib.SMTP()
            smtp.connect('mail.nemedi.dk')
            smtp.login('noreply@easyedi.dk', 'secret(5/')
            smtp.sendmail('noreply@easyedi.dk', [
                          _setting.errormail], msg.as_string())
            smtp.quit()

class Filecontent:
    def __init__(self):
        self.filecontent_id = ''
        self.filecontent_values = ''
        self.linenum = -1    
    def add_document_field(self, data_id, data_value):
        if self.linenum == 1:
            self.filecontent_id = self.filecontent_id + data_id+";"
        if data_value == False:
            self.filecontent_values = self.filecontent_values + '";"'
        else:
            self.filecontent_values = self.filecontent_values + str(data_value) + '";"'
    def add_document_field_two(self, data_id, data_value, data_value2):
        if self.linenum == 1:
            self.filecontent_id = self.filecontent_id + data_id+";"
        if data_value == False or data_value2 == False:
            self.filecontent_values = self.filecontent_values + '";"'
        else:
            self.filecontent_values = self.filecontent_values + str(data_value2) + '";"'
    def add_document_field_with_replace(self, data_id, data_value):
        if self.linenum == 1:
            self.filecontent_id = self.filecontent_id + data_id+";"
        if data_value == False:
            self.filecontent_values = self.filecontent_values + '";"'
        else:
            self.filecontent_values = self.filecontent_values + str(data_value).replace(u"\u0022", u"\u02EE") + '";"'
    def print_file_content(self):
        print(self.get_file_content())   
    def get_file_content(self):
        return self.filecontent_id+'\r\n'+self.filecontent_values
