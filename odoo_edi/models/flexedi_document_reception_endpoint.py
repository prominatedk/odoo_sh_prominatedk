from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class FlexediDocumentReceptionEndpoint(models.Model):
    _name = 'flexedi.document.reception.endpoint'
    _description = 'FlexEDI Document Reception Endpoint'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    endpoint = fields.Char(required=True)

    def process_documents_to_recieve(self, company, documents):
        self.ensure_one()
        reception_method_name = '_recieve_%s_document' % (self.code,)
        if hasattr(self, reception_method_name):
            reception_method = getattr(self, reception_method_name)
            for document in documents:
                result = reception_method(company, document)
                # We have to force a commit at this point to make sure that external data and internal data matches after processing each document
                self.env.cr.commit()
                if not result:
                    # Result is False, something has gone wrong and we should not even attempt to run the post_reception_hook
                    return False
                # Allow any other modules to hook into the data. Unless the hook commits the current transaction, it is commited after processing the next document
                result._document_post_reception_hook(document)
                # We have to force a commit at this point to make sure that data added in the postprocessing hook is also persisted.
                self.env.cr.commit()
        else:
            _logger.error('Attempted to process document reception, but it was not possible to call the required application logic to handle the document')
            _logger.debug('Could not process document, as method %s does not exist on model %s' % (reception_method_name,self._name))