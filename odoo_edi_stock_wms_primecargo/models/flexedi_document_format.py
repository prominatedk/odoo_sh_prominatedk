from odoo import models, fields, api, _

class FlexediDocumentFormat(models.Model):
    _inherit = 'flexedi.document.format'

    @api.model
    def _validate_primecargo_wms(self, document):
        result = {
            'valid': [True],
            'blocking': False,
            'messages': []
        }

        company = document.company_id or self.env.user.company_id

        # 1. Ensure that authentication credentials for PrimeCargo is present
        if not company.primecargo_username or not company.primecargo_password:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The company %s as not properly configured for PrimeCargo WMS. One or more authentication details is missing' % (company.display_name,))
            )
            # Here we will return early as there is no point in doing more if there is no authentication configured
            return result
        
        # 2. Check if the ownercode is defined. Without this, PrimeCargo cannot link the document to the proper account in their system
        if not company.primecargo_ownercode:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The company %s as not properly configured for PrimeCargo WMS. The Owner Code is missing' % (company.display_name,))
            )
            # Here we will return early as there is no point in doing more if there is no authentication configured
            return result

        return result
    
    @api.model
    def _validate_primecargo_wms_product(self, document):
        result = {
            'valid': [],
            'blocking': False,
            'messages': []
        }
        result = self._validate_primecargo_wms(document)

        # Validate required data for products to be created in PrimeCargo

        # 1. First check if we have a barcode and log a warning in case that no barcode is there
        if not document.barcode:
            result['messages'].append(
                _('The product does not have a barcode assigned. While technically valid, it might not be usable in the warehouse without')
            )
        
        # 2. Check if an internal reference is defined on the product and log a warning in case of it not being given
        if not document.default_code:
            result['messages'].append(
                _('The product does not have an internal reference / Part number assigned. While technically valid, it might not be usable in the warehouse without')
            )

        # 3. Check for the optional customs description. Log a warning in case it is missing
        if not document.product_tmpl_id.primecargo_customs_description:
            result['messages'].append(
                _('The product does not have a description for customs documents. It is not required for products to be usable, but can cause issues if the product is to be sent to a country where a customs declaration is required')
            )

        if not document.weight > 0:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The product does not have a weight assigned. This is required')
            )

        if not document.volume > 0:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The product does not have a volume assigned. This is required')
            )

        return result

    @api.model
    def _validate_primecargo_wms_picking_out(self, document):
        result = {
            'valid': [],
            'blocking': False,
            'messages': []
        }
        result = self._validate_primecargo_wms(document)

        if not document.scheduled_date:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The picking does not have a date for when it is to be processed. Without this, the warehouse cannot know when to ship the order')
            )
        
        partner = document.partner_id
        if not partner.street:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('Recipient address is not valid. Address is missing')
            )
        if not partner.zip:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('Recipient address is not valid. ZIP-code is missing')
            )
        if not partner.city:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('Recipient address is not valid. City is missing')
            )
        if not partner.country_id:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('Recipient address is not valid. Country is missing')
            )

        # Some fields are only required for special circumstances which are defined in agreement with PrimeCargo and the company
        # TODO: Make this configurable so that we only put warning messages when they are relevant. For now we check under the same conditions a missing barcode for products
        if not partner.email:
            result['messages'].append(
                _('Recipient does not have an email address. Under some conditions this can be required for PrimeCargo to properly handle the delivery')
            )
        if not partner.phone:
            result['messages'].append(
                _('Recipient does not have an phone number. Under some conditions this can be required for PrimeCargo to properly handle the delivery')
            )

        europe = self.env.ref('base.europe')
        if not partner.country_id.id in europe.country_ids.ids:
            # Shipment is going outside Europe and customs declaration might be required
            if not all([product.product_tmpl_id.primecargo_customs_description for product in document.move_ids.mapped('product_id')]):
                result['messages'].append(
                    _('One or more products on the shipment is missing a customs description. This might cause issues since the shipment is to be delivered in %s, which is outside of Europe' % (partner.country_id.name,))
                )

        return result

    @api.model
    def _validate_primecargo_wms_picking_in(self, document):
        result = {
            'valid': [],
            'blocking': False,
            'messages': []
        }
        result = self._validate_primecargo_wms(document)

        if not document.scheduled_date:
            result['valid'].append(False)
            result['blocking'] = True
            result['messages'].append(
                _('The picking does not have a date for when it is to be processed. Without this, the warehouse cannot know when the order is coming to the warehouse')
            )

        return result

    @api.model
    def _validate_primecargo_wms_stock_correction(self, document):
        result = {
            'valid': [],
            'blocking': False,
            'messages': []
        }
        result = self._validate_primecargo_wms(document)

        return result

    