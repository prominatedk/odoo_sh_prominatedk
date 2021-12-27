# FlexEDI Framework for EDI documents in Odoo
As Odoo has yet to implement a working EDI-framework/base we have made our own, which behaves similar to Odoos `account_edi` module.
To properly understand this documentation, it is asumed that the basic official Odoo technical training has been completed.
Examples in this documentation are for the purpose of illustration and might not direcly represent a valid implementation on the given Odoo version in case field names have changed between versions.

## Implement a new document format or document type
Document formats defines what types of documents can be sent/recieved and what format the exchange is performed in.
To allow the implementation to be easily extendable by other modules, we define document formats for controlling validation logic and data preparation

A document format consists on the following fields:
 - name: A human readable name such as "OIOUBL Faktura/Kreditnota"
 - code: A machine/technical name used to idenfity the generic format of document such as `nemhandel_oioubl` for any document to be sent of the NemHandel Network using the OIOUBL format specification
 - type: A machine/technical name used to identify what specific document type is used, such `invoice` for an Invoice or `order` for a Sales/Purchase Order
 - edi_network: Defines a preconfigured value for the FlexEDI REST API, which identifies the network or communications channel to use for distribution of a document. The value is supplied by FlexEDI ApS
 - requires_gln: Defines if this format does always require the `res.company` record to have GLN number configured
 - requires_vat: Defines if this format does always require the `res.company` record to a valid VAT number configured in the Company Registry field

These formats are marked `Read-Only` on the Odoo access rights, as they are meant to be managed programmatically through datafiles in individual modules, but having them as records in Odoo makes it a lot easier to work with.

All documents for pass the following validation rules to be considered valid:
 - A country must be defined on the `res.company` record in use
 - An API token for the FlexEDI REST API must be defined on the `res.company` record in use
 - If the format requires a GLN number, it must be present on the `res.company` record in use
 - If the format requires a VAT number, it must be present on the `res.company` record in use

A defined file could look something like this:
```xml
<odoo>
    <data>
        <record id="flexedi_document_format_nemhandel_oioubl_invoice" model="flexedi.document.format">
            <field name="name">NemHandel Invoice (OIOUBL)</field>
            <field name="code">nemhandel_oioubl</field>
            <field name="type">invoice</field>
            <field name="edi_network">nemhandel</field>
            <field name="requires_gln" eval="False"/>
            <field name="requires_vat" eval="True"/>
        </record>
    </data>
</odoo>
```

If a document format requires specific additional validation logic, the framework is designed to look for sepcific methods on the model, based on the values given on the `flexedi.document.format` record.
The method name consists of `_validate_`, then the value of the `code` field on the document format and finally the value of the `type` field separated by an `_`.
For the above example, the validation method name would be `_validate_nemhandel_oioubl_invoice`. If no method is found, no additional validation is triggered.

### Define validation method
A validation method takes one argument, which is the document to validate. It is up to the validation method to ensure that argument is of the proper type

A validation method is expected to return a `dict` with the following structure:

```python
{
    'valid': list,
    'blocking': bool,
    'messages': list
}
```

During validation, the `valid` key contains a list, where a boolean value is appended each time a validation either passes or fails. This can then later be used for statistics, such as informing the user that X out of Y validation rules have passed. It is initialized as an empty `list`.
During validation, the `blocking` key can be set to a boolean value to indicate if sending of the document should be prevented regardless of the validation result. This is usually used in cases where the underlying configuration in Odoo is invalid or where conditions of creating the document were bypassed and prevent proper processing of the document. It is initialized as `False` as it asumes that the document has passed all conditions checked during document creation and validation rules then specifically have to set it to `True` for preventing the document of being sent.
During validation, any messages that we want to give to the user can be added the `list` inside the `messages` key. The messages are then later converted to an HTML list and shown to the user.

A `blocking_level` field is set on the relevant document based on the information inside the validation `dict`. If `blocking` is `True`, the `blocking_level` is set to `error` and the document will not be sent and is also set to a failed state. All items from the `messages` key are stored. If one or more values in the `valid` key is `False` a `blocking_level` of warning is set and all items from the `messages` key are stored. The document is however still attempted sent as there is nothing blocking it from being sent. A `warning` level case could fx. be that the partner on the document is missing a value which might be required for most recipients, but it not technically a blocking error
If `blocking` is `False` and all items in `valid` are `True` and there are items in `messages`, then the `blocking_level` is set to `info` as the messages contain information, which might be of interest to the user.

## Add FlexEDI support to a document in Odoo
Adding support for FlexEDI in a given Odoo document/model is quite easy.
It consists of a few steps:
 1. Inherit `flexedi.document` as a copy onto a new model and define a `Many2one` relation from the model to the source model in Odoo
 2. Define a reverse of step to using a `One2many` relation on the source model
 3. Add data files for `ir.cron` entries required, as each document model to send requires a separate cron job
 4. Define computed fields to show the latest document state on the source model
 5. Define computed fields to handle whether the record on the source model can be sent using FlexEDI
 6. Define view logic to show valuable information on the source document
 7. Define view logic to show the related FlexEDI documents on the source model
 8. Define an option to connect the model and the document format on a partner

The above points are just the minimum required parts to get a working solution. Many more parts are possible to implement, such as custom form view for the FlexEDI documents, specific validation rules for a document format or for at given model regardless of the document format etc.

### 1. Inherit `flexedi.document`
```python
from odoo import models, fields

class FlexediDocumentInvoice(models.Model):
    _name = 'flexedi.document.invoice'
    _inherit = 'flexedi.document'

    move_id = fields.Many2one('account.move', domain=[('type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])])

```

The above creates a new model `flexedi.document.invoice` as a copy of the `flexedi.document` model. This means that any methods or fields from `flexedi.document` are automatically inherited on to `flexedi.document.invoice`, but fields and methods from `flexedi.document.invoice` are not inherited by other models that inherit `flexedi.document`.

The required `Many2one` relation is created on the `move_id` field for linking it to account moves with the move type of invoices and refunds.

### 2. Define a reverse relationship
```python
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    flexedi_invoice_ids = fields.One2many('flexedi.document.invoice', 'move_id')

```

Here we inherit `account.move` and link back to the `flexedi.document.invoice` model using the `id` of the `account.move` record as a loookup into the `move_id` field on `flexedi.document.invoice`

### 3. Add cron jobs for sending the documents
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record model="ir.cron" id="odoo_edi_send_invoices">
            <field name="name">FlexEDI: Send EDI Invoices</field>
            <field name="model_id" ref="odoo_edi_invoice.model_flexedi_document_invoice"/>
            <field name="state">code</field>
            <field name="code">model._cron_process_flexedi_documents(job_count=20)</field>
            <field name="interval_number">5</field>
            <field name="interval_type">minutes</field>
            <field name="numbercall">-1</field>
            <field name="doall" eval="False"/>
        </record>
        <record model="ir.cron" id="odoo_edi_invoice_status_updates">
            <field name="name">FlexEDI: Check for status updates on customer invoices</field>
            <field name="model_id" ref="odoo_edi_invoice.model_flexedi_document_invoice"/>
            <field name="state">code</field>
            <field name="code">model._cron_get_status_update(job_count=20)</field>
            <field name="interval_number">30</field>
            <field name="interval_type">minutes</field>
            <field name="numbercall">-1</field>
            <field name="doall" eval="False"/>
        </record>
    </data>
</odoo>
```

This defines two cron jobs.

The first job sends out `flexedi.document.invoice` records in batches of 20 documents every 5 minutes

The second job queries the FlexEDI REST API for status updates on previously sent documents. This runs every 30 minutes on batches of 20 documents.

The methods are defined in `flexedi.document` and the status updates are fetched based on the current document state in Odoo. This has the benefit of being able to fetch the status again if the job is cancelled before the database transaction is committed.

### 4. Define computed method to get the state of the last document generated
```python
from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    ...

    flexedi_document_status = fields.Selection(selection=[
        ('pending', 'Waiting to be sent to VANS'),
        ('sent', 'Sent to VANS'),
        ('validated', 'Validated by VANS'),
        ('recieved', 'Recieved from VANS'),
        ('processed', 'Processing confirmed by client'),
        ('failed_internal', 'Document failed internally'),
        ('failed_vans', 'Document failed at VANS')
    ], compute='_compute_flexedi_document_status', string="FlexEDI Status", store=True, help='Shows the status of the last time the document was sent to FlexEDI')

    ...

    @api.depends('flexedi_invoice_ids.state')
    def _compute_flexedi_document_status(self):
        for record in self:
            record.flexedi_document_status = record.flexedi_invoice_ids[0].state if len(record.flexedi_invoice_ids) else False

```

Records in models that inherit `flexedi.document` are sorted with latest document on top, so the method will always get the latest document. The field `flexedi_document_status` is marked as `store=True` in order to allow filtering, sorting and reporting of the source model records.

### 5. Define computed fields for validation and view logic
```python
from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    ...

    flexedi_can_send_document = fields.Boolean(compute='_compute_flexedi_can_send_document', string="Sendable using FlexEDI", help='Determines if the document can be sent using FlexEDI')

    is_using_flexedi = fields.Boolean(compute='_compute_is_using_flexedi', string="Document is using FlexEDI")

    @api.depends('partner_id', 'partner_id.flexedi_document_format_mapping_ids')
    def _compute_flexedi_can_send_document(self):
        for record in self:
            record.flexedi_can_send_document = any(record.partner_id.flexedi_document_format_mapping_ids.filtered(lambda f: f.model == 'account.move'))

    @api.depends('flexedi_invoice_ids')
    def _compute_is_using_flexedi(self):
        for record in self:
            record.is_using_flexedi = len(record.flexedi_invoice_ids) > 0

```

### 6. Show valuable information to users
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record id="inherit_view_invoice_form" model="ir.ui.view">
            <field name="name">account.invoice.form</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_move_form"/>
            <field name="arch" type="xml">
                <xpath expr="//div[@class='alert alert-info']" position="after">
                    <field name="is_using_flexedi" invisible="1"/>
                    <field name="flexedi_can_send_document" invisible="1"/>
                    <field name="flexedi_document_status" invisible="1"/>
                    <div class="alert alert-info" role="alert" style="margin-bottom:0px;" attrs="{'invisible': ['|', '|', '|', ('is_move_sent', '=', True), ('flexedi_can_send_document', '=', False), ('state', '!=', 'draft'), ('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        When validating this invoice, it will be validated for use with EDI
                    </div>
                    <div class="alert alert-danger" role="alert" style="margin-bottom:0px;" attrs="{'invisible': ['|', '|', ('is_using_flexedi','=',False), ('flexedi_document_status', 'not in', ['failed_internal', 'failed_vans']), ('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        The invoice has failed during processing. Please see the details on the <em>FlexEDI</em> tab
                    </div>
                    <div class="alert alert-info" role="alert" style="margin-bottom:0px;" attrs="{'invisible': ['|', '|', ('is_using_flexedi','=',False), ('flexedi_document_status', '!=', 'pending'), ('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        The EDI invoice has been generated. We will update the invoice once it has been sent to our VANS provider
                    </div>
                    <div class="alert alert-success" role="alert" style="margin-bottom:0px;" attrs="{'invisible': ['|', '|', ('is_using_flexedi','=',False), ('flexedi_document_status', '!=', 'is_move_sent'), ('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        The invoice has been sent using EDI. We will update the invoice once it has been processed at our VANS provider
                    </div>
                    <div class="alert alert-success" role="alert" style="margin-bottom:0px;" attrs="{'invisible': ['|', '|', ('is_using_flexedi','=',False), ('flexedi_document_status', '!=', 'validated'), ('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        The invoice has been delivered by our VANS provider
                    </div>
                </xpath>
            </field>
        </record>
        <record id="inherit_view_invoice_tree" model="ir.ui.view">
            <field name="name">account.invoice.tree</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_invoice_tree"/>
            <field name="arch" type="xml">
                <xpath expr="//field[@name='state']" position="after">
                    <field name="flexedi_document_status" optional="show"/>
                </xpath>
            </field>
        </record>
    </data>
</odoo>
```

The above shows the document state on the list/tree view as well as showing a status message to the user inside the form view.

### 7. Show documents to the user
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record id="inherit_view_invoice_form" model="ir.ui.view">
            <field name="name">account.invoice.form</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_move_form"/>
            <field name="arch" type="xml">
                <xpath expr="//notebook" position="inside">
                    <page name="flexedi_documents" string="FlexEDI" attrs="{ 'invisible': [('flexedi_invoice_ids', '=', [])] }">
                        <group name="flexedi_document_list" string="Documents">
                            <field name="flexedi_invoice_ids" nolabel="1">
                                <tree create="0" edit="0" delete="0" decoration-danger="state in ['failed_vans', 'failed_internal']" decoration-success="state in ['sent', 'validated']" decoration-info="state in ['pending']">
                                    <field name="create_date" readonly="1"/>
                                    <field name="document_format_id" readonly="1"/>
                                    <field name="edi_uuid" readonly="1"/>
                                    <field name="state" readonly="1"/>
                                    <button name="action_retry" type="object" string="Retry" icon="fa-repeat" states="failed_internal,failed_vans"/>
                                </tree>
                            </field>
                        </group>
                    </page>
                </xpath>
            </field>
        </record>
    </data>
</odoo>
```

The above can seem strange, but in the most basic form, this shows a list of all documents linked to the source model instance/record and gives a specific color the the ones that have an error as well as the ones not yet sent and the ones that have completed.
Additionally it shows an option, `action_retry`, to make a copy of the document and send it again

### 8. Link document formats, models and partners
```python
from odoo import models, fields, api, _

class FlexediDocumentFormatPartner(models.Model):
    _inherit = 'flexedi.document.format.partner'

    model = fields.Selection(selection_add=[
        ('account.move', 'Invoice/CreditNote')
    ])
```

On a partner in Odoo, FlexEDI only works if the document format for a given model can be set. The above code creates a new option to link a document format to the `account.move` model. On the base implementation of `flexedi.document.format.partner` there is a constraint to ensure only one format per model per partner.

On `res.partner` a utility method called `get_format_for_model` is availble to fetch the `flexedi.document.format` record that is linked to the provided model. This is only required to be done by the module that does the actual implementation of the EDI document.
Modules that only define a new format, does not have to implement this.

#### An example
`odoo_edi_invoice` implements support to send invoices and refunds from Odoo. It defines the above code, but not directly any formats.
`odoo_edi_nemhandel_invoice` defines a specific format and corresponding validation logic, but does not contain the above code example, since that was prepared in `odoo_edi_invoice`
`odoo_edi_dagrofa_editfact_invoice` defines a specific format, validation logic and altered data, but does not contain the above code example, since it does not implement a new model, but just a new format. This does again depend on `odoo_edi_invoice`

The result is that a model of `account.move` can be selected and then either `NemHandel Invoice` or `Dagrofa EDIFACT Invoice` can be selected as the format

### Final notes
Remember to add view modifications to the modules `__manifest__.py` in order to have them be loaded and usable

## Define a document that can be recieved in Odoo
To recieve new documents into Odoo, where a record might not already exists, in case of vendor bills from vendors using EDI, we define what is called a reception endpoint. This is defined by creating a record in the `flexedi.document.reception.endpoint` model.

This behaves similar to how validation works on `flexedi.document.format`, as it checks for a specific method on the model.

The reception endpoint is defined like this:

```xml
<odoo>
    <data>
        <record id="nemhandel_invoice_refund" model="flexedi.document.reception.endpoint">
            <field name="name">Vendor Bills/Refunds: Recieve from EDI</field>
            <field name="code">nemhandel_invoice_refund</field>
            <field name="endpoint">invoices/queue/</field>
        </record>
    </data>
</odoo>
```

When a document is recieved from a reception endoint, it expects a method to exist in `flexedi.document.reception.endpoint`, which is constructed as `_recieve_`, then the value of the `code` field and finally `_document`.
In the above example, the method would be named `_recieve_nemhandel_invoice_refund_document`.

The `endpoint` field on `flexedi.document.reception.endpoint` defines the relative path from the root of the FlexEDI REST API. A traling `/` is required. This field is the only part that is required to be defined by FlexEDI ApS.

The expected reception method must define the logic required to extract relevant data from the data returned by the reception endpoint. It is also responsible for validating if the data is usable and update the document state in both Odoo and the FlexEDI REST API.

If at some point the reception of the document requires other things, such as fx. recieving a an order confirmation for a sales order and automatically validating it, then that can be built as an inherited version of the `_document_post_reception_hook`.
This method is executed after the reception method has done the work that it needs to do and the database transaction has been forcefully committed to ensure consistency of data between the Odoo database and the FlexEDI REST API.
Any error during the `_document_post_reception_hook` is rolled back like usual, but the actual reception of the document is not.