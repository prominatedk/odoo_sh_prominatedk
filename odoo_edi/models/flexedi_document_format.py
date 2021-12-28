import re
from odoo import models, api, fields, _

class FlexediDocumentFormat(models.Model):
    _name = 'flexedi.document.format'
    _description = 'FlexEDI Document Format'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    type = fields.Char(required=True)
    edi_network = fields.Char(required=True, string="EDI Communications Channel")
    requires_vat = fields.Boolean(string='Documents require VAT number present')
    requires_gln = fields.Boolean(string='Documents require GLN number present')

    def is_valid(self, document):
        """
        Returns information on whether the document has passed validation or not
        :param document: A record of flexedi.document, or an inherited model
        :returns dict: Dictionary with the validation result
        Example:
        {
            'valid': True, # A summarized state on whether the document can be sent or not
            'error_state': 'error', # Can be 'warning' if sending is not blocked
            'messages': [
                ...
            ] # A list of all error messages generated during validation
        }
        """
        self.ensure_one()
        # List to contain result of each validation
        valid = []
        blocking = False
        messages = []
        # Base validation for all documents, regardless of type
        company = document.company_id or self.env.user.company_id
        # Validate if company level settings are correct
        company_validation_result = company.is_valid_for_flexedi()
        # If any messages are provided during company validation, append them to the list of messages
        if len(company_validation_result['messages']) > 0:
            messages += company_validation_result['messages']
        if not company_validation_result['valid']:
            blocking = True
        if self.requires_gln:
            if company.gln:
                valid.append(True)
            else:
                valid.append(False)
                blocking = True
                messages.append(
                    _('A valid GLN number has not been provided on %s' % (company.display_name,))
                )
        if self.requires_vat:
            if company.company_registry:
                valid.append(True)
            else:
                valid.append(False)
                blocking = True
                messages.append(
                    _('A valid VAT number has not been provided on %s' % (company.display_name,))
                )
        
        # Check for specific validation methods of the document format
        validation_method_name = '_validate_%s_%s' % (self.code, self.type)
        if hasattr(self, validation_method_name):
            validation_method = getattr(self, validation_method_name)
            result = validation_method(document)
            validation_results = result['valid']
            validation_blocked = result['blocking']
            validation_messages = result['messages']
            if type(validation_results) == list:
                valid += validation_results
            else:
                valid.append(validation_results)
            if not blocking and validation_blocked:
                blocking = True
            messages += validation_messages
        error_state = ''
        if all(valid):
            if len(messages):
                error_state = 'info'
        elif blocking:
            error_state = 'error'
        else:
            error_state = 'warning'
        return {
            'valid':all(valid),
            'error_state': error_state,
            'messages': messages
        }