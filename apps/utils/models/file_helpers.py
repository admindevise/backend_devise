from django.utils import timezone

def generate_upload_path(module_name: str, field_name: str):
    """
    Genera función de upload_to reutilizable para ImageField/FileField
    
    Estructura: media/{module}/{field}/{YYYYMMDD}/{id}_{counter}_{filename}
    
    Ejemplo:
        def fund_image_path(instance, filename):
            return generate_upload_path('fund', 'logo')(instance, filename)
    
    Args:
        module_name: nombre del módulo (fund, user, trading, etc)
        field_name: nombre del campo (logo, document, image, etc)
    
    Returns:
        función compatible con upload_to
    """
    
    def upload_path(instance, filename):
        # Obtener fecha en formato YYYYMMDD
        today = timezone.now().strftime('%Y%m%d')
        
        # Obtener ID de la instancia (crear si es nueva)
        instance_id = instance.id or 'new'
        
        # Contador/secuencia (opcional, para múltiples uploads del mismo campo)
        counter = getattr(instance, '_file_counter', 1)
        
        # Construir nombre: {id}_{counter}_{nombre_original}
        name_parts = filename.rsplit('.', 1)
        ext = name_parts[1] if len(name_parts) > 1 else 'jpg'
        
        clean_filename = f'{field_name}_{instance_id}_{counter}_{today}.{ext}'
        
        # Ruta final: media/{module}/{field}/{archivo}
        return f'{module_name}/{field_name}/{clean_filename}'
    
    return upload_path


# ============================================================================
# Helpers Financial Institution
# ============================================================================
def fi_logo_path(instance, filename):
    """Para FinancialInstitution.logo"""
    return generate_upload_path('financial_institution', 'logo')(instance, filename)

# ============================================================================
# Helpers Fund Core
# ============================================================================
def fund_image_path(instance, filename):
    """Para Fund.image"""
    return generate_upload_path('fund', 'image')(instance, filename)

def fund_image_admin_path(instance, filename):
    """Para Fund.image_admin"""
    return generate_upload_path('fund', 'image_admin')(instance, filename)

def fund_terms_and_conditions_path(instance, filename):
    """Para Fund.terms_and_conditions_file"""
    return generate_upload_path('fund', 'terms')(instance, filename)

def fund_data_processing_policy_path(instance, filename):
    """Para Fund.data_processing_policy_file"""
    return generate_upload_path('fund', 'data_processing_policy')(instance, filename)

def fund_fiduciary_draft_path(instance, filename):
    """Para Fund.fiduciary_draft_file"""
    return generate_upload_path('fund', 'fiduciary_draft')(instance, filename)

def fund_mercantile_trust_agreement_path(instance, filename):
    """Para Fund.mercantile_trust_agreement_file"""
    return generate_upload_path('fund', 'mercantile_trust_agreement')(instance, filename)

def fund_other_documents_path(instance, filename):
    """Para Fund.other_documents_file"""
    return generate_upload_path('fund', 'other_documents')(instance, filename)

def fund_assignment_contract_path(instance, filename):
    """Para Fund.assignment_contract"""
    return generate_upload_path('fund', 'assignment_contract')(instance, filename)

def fund_operating_contract_path(instance, filename):
    """Para Fund.operating_contract"""
    return generate_upload_path('fund', 'operating_contract')(instance, filename)

def fund_semestral_document_path(instance, filename):
    """Para FundSemestralDocument.document"""
    return generate_upload_path('fund_semestral_document', 'document')(instance, filename)

def othersi_document_path(instance, filename):
    """Para Otrosi.document"""
    return generate_upload_path('otrosi', 'document')(instance, filename)

def trust_agreement_signed_document_path(instance, filename):
    """Para TrustAgreement.signed_document_url"""
    return generate_upload_path('trust_agreement', 'signed_document_url')(instance, filename)

def trust_agreement_electronic_envelope_path(instance, filename):
    """Para TrustAgreement.electronic_envelope"""
    return generate_upload_path('trust_agreement', 'electronic_envelope')(instance, filename)


# ============================================================================
# Helpers Fund Accounting
# ============================================================================
def accounting_entry_attachment_path(instance, filename):
    """Para AccountingEntry.attachment"""
    return generate_upload_path('accouning', 'attachment')(instance, filename)

def accountability_document_path(instance, filename):
    """Para Accountability_document"""
    return generate_upload_path('accountability', 'accountability_document')(instance, filename)

def invoice_record_attachment_path(instance, filename):
    """Para InvoiceRecord.attachment"""
    return generate_upload_path('invoice_record', 'invoice_record_attachment')(instance, filename)

def invoice_record_xml_attachment_path(instance, filename):
    """Para InvoiceRecord.xml_attachment"""
    return generate_upload_path('invoice_record', 'xml_attachment')(instance, filename)

def accounting_import_batch_file_path(instance, filename):
    """Para AccountingImportBatch.accounting_file"""
    return generate_upload_path('accounting_import_batch', 'accounting_file')(instance, filename)


# ============================================================================
# Helpers Fund Commissions
# ============================================================================
def commission_transfer_doc_transfer_path(instance, filename):
    """Para CommissionTransfer.doc_transfer"""
    return generate_upload_path('commission_transfer', 'doc_transfer')(instance, filename)


# ============================================================================
# Helpers Fund Membership
# ============================================================================
def fund_investment_payment_receipt_path(instance, filename):
    """Para FundInvestment.payment_receipt"""
    return generate_upload_path('fund_investment', 'payment_receipt')(instance, filename)

# ============================================================================
# Helpers Fund Academy
# ============================================================================
def academy_category_image_path(instance, filename):
    """Para Category.image"""
    return generate_upload_path('academy', 'image')(instance, filename)

def academy_article_image_path(instance, filename):
    """Para Articles.image"""
    return generate_upload_path('academy', 'image')(instance, filename)

# ============================================================================
# Helpers User
# ============================================================================
def user_juridic_xlsx_path(instance, filename):
    """Para User.juridic_xlsx"""
    return generate_upload_path('user', 'juridic_xlsx')(instance, filename)

def user_document_front_path(instance, filename):
    """Para User.document_front_image"""
    return generate_upload_path('user', 'document_front_image')(instance, filename)

def user_document_back_path(instance, filename):
    """Para User.document_back_image"""
    return generate_upload_path('user', 'document_back_image')(instance, filename)

def user_profile_selfie_path(instance, filename):
    """Para User.selfie"""
    return generate_upload_path('user', 'selfie')(instance, filename)

def info_financial_certification_file_path(instance, filename):
    """Para InfoFinancial.certification_file"""
    return generate_upload_path('info_financial', 'certification_file')(instance, filename)

def info_socioeconomic_last_year_income_statement_path(instance, filename):
    """Para InfoSocioeconomic.last_year_income_statement"""
    return generate_upload_path('info_socioeconomic', 'last_year_income_statement')(instance, filename)

def info_socioeconomic_economic_dependency_letter_path(instance, filename):
    """Para InfoSocioeconomic.economic_dependency_letter"""
    return generate_upload_path('info_socioeconomic', 'economic_dependency_letter')(instance, filename)

def info_socioeconomic_certified_public_accountant_path(instance, filename):
    """Para InfoSocioeconomic.certified_public_accountant"""
    return generate_upload_path('info_socioeconomic', 'certified_public_accountant')(instance, filename)

def info_socioeconomic_professional_accountant_card_path(instance, filename):
    """Para InfoSocioeconomic.profesional_accountant_card"""
    return generate_upload_path('info_socioeconomic', 'professional_accountant_card')(instance, filename)

def info_socioeconomic_pension_payment_receipt_path(instance, filename):
    """Para InfoSocioeconomic.pension_payment_receipt"""
    return generate_upload_path('info_socioeconomic', 'pension_payment_receipt')(instance, filename)

def info_socioeconomic_source_funds_support_path(instance, filename):
    """Para InfoSocioeconomic.source_funds_support"""
    return generate_upload_path('info_socioeconomic', 'source_funds_support')(instance, filename)
