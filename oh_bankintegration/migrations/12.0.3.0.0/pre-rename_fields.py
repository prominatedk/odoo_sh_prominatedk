import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info('Apply migration 12.0.3.0.0 as part of migration from version {}'.format(version))
    # Fields to rename
    #
    #  account.invoice:
    # payment_id -> bankintegration_payment_id
    _logger.info('Renaming account.invoice.payment_id to account.invoice.bankintegration_payment_id')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_id\' FROM ir_model WHERE ir_model_fields.name = \'payment_id\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_id\' WHERE name = \'field_account_invoice__payment_id\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_id TO bankintegration_payment_id;')
    # request_id -> bankintegration_request_id
    _logger.info('Renaming account.invoice.request_id to account.invoice.bankintegration_request_id')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_request_id\' FROM ir_model WHERE ir_model_fields.name = \'request_id\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_request_id\' WHERE name = \'field_account_invoice__request_id\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME request_id TO bankintegration_request_id;')
    # payment_autopay -> bankintegration_payment_autopay
    _logger.info('Renaming account.invoice.payment_autopay to account.invoice.bankintegration_payment_autopay')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_autopay\' FROM ir_model WHERE ir_model_fields.name = \'payment_autopay\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_autopay\' WHERE name = \'field_account_invoice__payment_autopay\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_autopay TO bankintegration_payment_autopay;')
    # payment_status -> bankintegration_payment_status
    _logger.info('Renaming account.invoice.payment_status to account.invoice.bankintegration_payment_status')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_status\' FROM ir_model WHERE ir_model_fields.name = \'execute\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_status\' WHERE name = \'field_account_invoice__payment_status\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_status TO bankintegration_payment_status;')
    # payment_duedate -> bankintegration_payment_date
    _logger.info('Renaming account.invoice.payment_duedate to account.invoice.bankintegration_payment_date')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_date\' FROM ir_model WHERE ir_model_fields.name = \'payment_duedate\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_date\' WHERE name = \'field_account_invoice__payment_duedate\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_duedate TO bankintegration_payment_date;')
    # payment_journal -> bankintegration_payment_journal_id
    _logger.info('Renaming account.invoice.payment_journal to account.invoice.bankintegration_payment_journal_id')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_journal_id\' FROM ir_model WHERE ir_model_fields.name = \'payment_journal\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_journal_id\' WHERE name = \'field_account_invoice__payment_journal\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_journal TO bankintegration_payment_journal_id;')
    # payment_error -> bankintegration_payment_error
    _logger.info('Renaming account.invoice.payment_error to account.invoice.bankintegration_payment_error')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_error\' FROM ir_model WHERE ir_model_fields.name = \'payment_error\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_error\' WHERE name = \'field_account_invoice__payment_error\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_error TO bankintegration_payment_error;')
    # payment_count -> bankintegration_payment_attempts
    _logger.info('Renaming account.invoice.payment_count to account.invoice.bankintegration_payment_attempts')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_attempts\' FROM ir_model WHERE ir_model_fields.name = \'payment_count\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__bankintegration_payment_attempts\' WHERE name = \'field_account_invoice__payment_count\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME payment_count TO bankintegration_payment_attempts;')
    if version in ['12.0.2.9.0', '12.0.2.9.1']:
        # fik_number_payment_code -> payment_fik_number_payment_code
        _logger.info('Renaming account.invoice.fik_number_payment_code to account.invoice.payment_fik_number_payment_code')
        cr.execute('UPDATE ir_model_fields SET name = \'payment_fik_number_payment_code\' FROM ir_model WHERE ir_model_fields.name = \'fik_number_payment_code\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
        cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__payment_fik_number_payment_code\' WHERE name = \'field_account_invoice__fik_number_payment_code\' AND module = \'oh_bankintegration\';')
        cr.execute('ALTER TABLE account_invoice RENAME fik_number_payment_code TO payment_fik_number_payment_code;')
        # fik_number_payment_string -> payment_fik_number_payment_string
        _logger.info('Renaming account.invoice.fik_number_payment_string to account.invoice.payment_fik_number_payment_string')
        cr.execute('UPDATE ir_model_fields SET name = \'payment_fik_number_payment_string\' FROM ir_model WHERE ir_model_fields.name = \'fik_number_payment_string\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
        cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__payment_fik_number_payment_string\' WHERE name = \'field_account_invoice__fik_number_payment_string\' AND module = \'oh_bankintegration\';')
        cr.execute('ALTER TABLE account_invoice RENAME fik_number_payment_string TO payment_fik_number_payment_string;')
        # fik_number_creditor -> payment_fik_number_creditor
        _logger.info('Renaming account.invoice.fik_number_creditor to account.invoice.payment_fik_number_creditor')
        cr.execute('UPDATE ir_model_fields SET name = \'payment_fik_number_creditor\' FROM ir_model WHERE ir_model_fields.name = \'fik_number_creditor\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
        cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__payment_fik_number_creditor\' WHERE name = \'field_account_invoice__fik_number_creditor\' AND module = \'oh_bankintegration\';')
        cr.execute('ALTER TABLE account_invoice RENAME fik_number_creditor TO payment_fik_number_creditor;')
    # fik_number -> payment_fik_number
    _logger.info('Renaming account.invoice.fik_number to account.invoice.payment_fik_number')
    cr.execute('UPDATE ir_model_fields SET name = \'payment_fik_number\' FROM ir_model WHERE ir_model_fields.name = \'fik_number\' AND ir_model.model = \'account.invoice\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_invoice__payment_fik_number\' WHERE name = \'field_account_invoice__fik_number\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_invoice RENAME fik_number TO payment_fik_number;')
    #
    # account.journal:
    # customer_code -> bankintegration_integration_code
    _logger.info('Renaming account.journal.customer_code to account.journal.bankintegration_integration_code')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_integration_code\' FROM ir_model WHERE ir_model_fields.name = \'customer_code\' AND ir_model.model = \'account.journal\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_account_journal__bankintegration_integration_code\' WHERE name = \'field_account_journal__customer_code\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE account_journal RENAME customer_code TO bankintegration_integration_code;')
    #
    # res.company
    # payment_margin -> bankintegration_payment_margin
    _logger.info('Renaming res.company.payment_margin to res.company.bankintegration_payment_margin')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_margin\' FROM ir_model WHERE ir_model_fields.name = \'payment_margin\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_payment_margin\' WHERE name = \'field_res_company__payment_margin\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME payment_margin TO bankintegration_payment_margin;')
    # autopay -> bankintegration_autopay
    _logger.info('Renaming res.company.autopay to res.company.bankintegration_autopay')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_autopay\' FROM ir_model WHERE ir_model_fields.name = \'autopay\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_autopay\' WHERE name = \'field_res_company__autopay\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME autopay TO bankintegration_autopay;')
    # set_validate_payment -> bankintegration_send_on_validate
    _logger.info('Renaming res.company.set_validate_payment to res.company.bankintegration_send_on_validate')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_send_on_validate\' FROM ir_model WHERE ir_model_fields.name = \'set_validate_payment\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_send_on_validate\' WHERE name = \'field_res_company__set_validate_payment\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME set_validate_payment TO bankintegration_send_on_validate;')
    # payment_journal -> bankintegration_payment_journal_id
    _logger.info('Renaming res.company.payment_journal to res.company.bankintegration_payment_journal_id')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_journal_id\' FROM ir_model WHERE ir_model_fields.name = \'payment_journal\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_payment_journal_id\' WHERE name = \'field_res_company__payment_journal\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME payment_journal TO bankintegration_payment_journal_id;')
    # erp_provider -> bankintegration_erp_provider
    _logger.info('Renaming res.company.erp_provider to res.company.bankintegration_erp_provider')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_erp_provider\' FROM ir_model WHERE ir_model_fields.name = \'erp_provider\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_erp_provider\' WHERE name = \'field_res_company__erp_provider\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME erp_provider TO bankintegration_erp_provider;')
    # bi_api_key -> bankintegration_provider_api_key
    _logger.info('Renaming res.company.bi_api_key to res.company.bankintegration_provider_api_key')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_provider_api_key\' FROM ir_model WHERE ir_model_fields.name = \'bi_api_key\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_provider_api_key\' WHERE name = \'field_res_company__bi_api_key\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME bi_api_key TO bankintegration_provider_api_key;')
    # use_note_msg -> bankintegration_statement_note_as_label 
    _logger.info('Renaming res.company.use_note_msg to res.company.bankintegration_statement_note_as_label ')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_statement_note_as_label\' FROM ir_model WHERE ir_model_fields.name = \'use_note_msg\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_statement_note_as_label \' WHERE name = \'field_res_company__use_note_msg\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME use_note_msg TO bankintegration_statement_note_as_label;')
    # check_payment_status -> bankintegration_check_payment_status
    _logger.info('Renaming res.company.check_payment_status to res.company.bankintegration_check_payment_status')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_check_payment_status\' FROM ir_model WHERE ir_model_fields.name = \'check_payment_status\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_check_payment_status\' WHERE name = \'field_res_company__check_payment_status\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME check_payment_status TO bankintegration_check_payment_status;')
    # use_bban -> bankintegration_use_odoo_bban
    _logger.info('Renaming res.company.use_bban to res.company.bankintegration_use_odoo_bban')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_use_odoo_bban\' FROM ir_model WHERE ir_model_fields.name = \'use_bban\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_use_odoo_bban\' WHERE name = \'field_res_company__use_bban\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME use_bban TO bankintegration_use_odoo_bban;')
    # use_extended_import -> bankintegration_extended_import_format
    _logger.info('Renaming res.company.use_extended_import to res.company.bankintegration_extended_import_format')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_extended_import_format\' FROM ir_model WHERE ir_model_fields.name = \'use_extended_import\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_extended_import_format\' WHERE name = \'field_res_company__use_extended_import\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME use_extended_import TO bankintegration_extended_import_format;')
    # use_last_entry_date_as_statement_date -> bankintegration_last_entry_date_as_statement_date
    _logger.info('Renaming res.company.use_last_entry_date_as_statement_date to res.company.bankintegration_last_entry_date_as_statement_date')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_last_entry_date_as_statement_date\' FROM ir_model WHERE ir_model_fields.name = \'use_last_entry_date_as_statement_date\' AND ir_model.model = \'res.company\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_company__bankintegration_last_entry_date_as_statement_date\' WHERE name = \'field_res_company__use_last_entry_date_as_statement_date\' AND module = \'oh_bankintegration\';')
    cr.execute('ALTER TABLE res_company RENAME use_last_entry_date_as_statement_date TO bankintegration_last_entry_date_as_statement_date;')
    #
    # res.config.settings
    # payment_margin -> bankintegration_payment_margin
    _logger.info('Renaming res.config.settings.payment_margin to res.config.settings.bankintegration_payment_margin')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_margin\' FROM ir_model WHERE ir_model_fields.name = \'payment_margin\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_payment_margin\' WHERE name = \'field_res_config_settings__payment_margin\' AND module = \'oh_bankintegration\';')
    # autopay -> bankintegration_autopay
    _logger.info('Renaming res.config.settings.autopay to res.config.settings.bankintegration_autopay')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_autopay\' FROM ir_model WHERE ir_model_fields.name = \'autopay\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_autopay\' WHERE name = \'field_res_config_settings__autopay\' AND module = \'oh_bankintegration\';')
    # set_validate_payment -> bankintegration_send_on_validate
    _logger.info('Renaming res.config.settings.set_validate_payment to res.config.settings.bankintegration_send_on_validate')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_send_on_validate\' FROM ir_model WHERE ir_model_fields.name = \'set_validate_payment\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_send_on_validate\' WHERE name = \'field_res_config_settings__set_validate_payment\' AND module = \'oh_bankintegration\';')
    # payment_journal -> bankintegration_payment_journal_id
    _logger.info('Renaming res.config.settings.payment_journal to res.config.settings.bankintegration_payment_journal_id')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_payment_journal_id\' FROM ir_model WHERE ir_model_fields.name = \'payment_journal\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_payment_journal_id\' WHERE name = \'field_res_config_settings__payment_journal\' AND module = \'oh_bankintegration\';')
    # erp_provider -> bankintegration_erp_provider
    _logger.info('Renaming res.config.settings.erp_provider to res.config.settings.bankintegration_erp_provider')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_erp_provider\' FROM ir_model WHERE ir_model_fields.name = \'erp_provider\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_erp_provider\' WHERE name = \'field_res_config_settings__erp_provider\' AND module = \'oh_bankintegration\';')
    # bi_api_key -> bankintegration_provider_api_key
    _logger.info('Renaming res.config.settings.bi_api_key to res.config.settings.bankintegration_provider_api_key')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_provider_api_key\' FROM ir_model WHERE ir_model_fields.name = \'bi_api_key\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_provider_api_key\' WHERE name = \'field_res_config_settings__bi_api_key\' AND module = \'oh_bankintegration\';')
    # use_note_msg -> bankintegration_statement_note_as_label 
    _logger.info('Renaming res.config.settings.use_note_msg to res.config.settings.bankintegration_statement_note_as_label ')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_statement_note_as_label\' FROM ir_model WHERE ir_model_fields.name = \'use_note_msg\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_statement_note_as_label \' WHERE name = \'field_res_config_settings__use_note_msg\' AND module = \'oh_bankintegration\';')
    # check_payment_status -> bankintegration_check_payment_status
    _logger.info('Renaming res.config.settings.check_payment_status to res.config.settings.bankintegration_check_payment_status')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_check_payment_status\' FROM ir_model WHERE ir_model_fields.name = \'check_payment_status\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_check_payment_status\' WHERE name = \'field_res_config_settings__check_payment_status\' AND module = \'oh_bankintegration\';')
    # use_bban -> bankintegration_use_odoo_bban
    _logger.info('Renaming res.config.settings.use_bban to res.config.settings.bankintegration_use_odoo_bban')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_use_odoo_bban\' FROM ir_model WHERE ir_model_fields.name = \'use_bban\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_use_odoo_bban\' WHERE name = \'field_res_config_settings__use_bban\' AND module = \'oh_bankintegration\';')
    # use_extended_import -> bankintegration_extended_import_format
    _logger.info('Renaming res.config.settings.use_extended_import to res.config.settings.bankintegration_extended_import_format')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_extended_import_format\' FROM ir_model WHERE ir_model_fields.name = \'use_extended_import\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_extended_import_format\' WHERE name = \'field_res_config_settings__use_extended_import\' AND module = \'oh_bankintegration\';')
    # use_last_entry_date_as_statement_date -> bankintegration_last_entry_date_as_statement_date
    _logger.info('Renaming res.config.settings.use_last_entry_date_as_statement_date to res.config.settings.bankintegration_last_entry_date_as_statement_date')
    cr.execute('UPDATE ir_model_fields SET name = \'bankintegration_last_entry_date_as_statement_date\' FROM ir_model WHERE ir_model_fields.name = \'use_last_entry_date_as_statement_date\' AND ir_model.model = \'res.config.settings\' AND ir_model_fields.model_id = ir_model.id;')
    cr.execute('UPDATE ir_model_data SET name = \'field_res_config_settings__bankintegration_last_entry_date_as_statement_date\' WHERE name = \'field_res_config_settings__use_last_entry_date_as_statement_date\' AND module = \'oh_bankintegration\';')
    #
    # First rename the database field

    # Next rename the ir.model.fields record