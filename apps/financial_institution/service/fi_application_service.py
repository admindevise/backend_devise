from django.db import transaction
from django.utils import timezone

from apps.financial_institution.models import FinancialInstitutionApplication
from apps.audit.audit_service import AuditService

class FIApplicationError(Exception):
    """Custom exception for FI application errors"""
    pass

class FinancialInstitutionApplicationService:
    """
    Servicio para gestionar el flujo completo de solicitudes y aprobaciones
    """
    
    @staticmethod
    @transaction.atomic
    def submit_application(
        user, 
        financial_institution, 
        requested_investor_profile: str,
        request=None,
        **kwargs
    ) -> FinancialInstitutionApplication:
        """Crear nueva solicitud"""
            
        initial_audit = None
        base_filter = {
            'user': user,
            'financial_institution': financial_institution
        }
        
        try:
            # Crear auditoría inicial si tenemos request
            if request:
                print("Creando auditoría inicial para solicitud FI")
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FI_MEMBERSHIP_REQUEST",
                    obj=user,  # Usamos el usuario como referencia hasta crear la aplicación
                    details={
                        'financial_institution_id': financial_institution.id,
                        'financial_institution_name': financial_institution.name,
                        'requested_investor_profile': requested_investor_profile,
                        'requested_investment_amount': str(kwargs.get('requested_investment_amount')),
                        'operation': 'submit_application'
                    },
                    status='PENDING'
                )
        
            # 1. Verificar solicitudes activas (UNA consulta específica)
            active_statuses = ['pending', 'under_review', 'approved', 'additional_info', 'pending_user_signature']
            has_active = FinancialInstitutionApplication.objects.select_for_update().filter(
                **base_filter,
                status__in=active_statuses
            ).exists()
            
            if has_active:
                raise ValueError("Ya tienes una solicitud pendiente con esta institución financiera")
            
            # 2. Verificar rechazos permanentes (UNA consulta específica)
            has_permanent_rejection = FinancialInstitutionApplication.objects.select_for_update().filter(
                **base_filter,
                status='rejected',
                rejection_category__in=['fraud', 'compliance']
            ).exists()
            
            if has_permanent_rejection:
                raise ValueError("Tu solicitud ha sido rechazada permanentemente y no puedes volver a aplicar")
            
            # 3. Verificar restricciones de tiempo (UNA consulta específica)
            latest_rejected = FinancialInstitutionApplication.objects.select_for_update().filter(
                **base_filter,
                status='rejected',
                can_reapply_after__gt=timezone.now().date()  # Solo los que tienen restricción activa
            ).order_by('-reviewed_at').first()
            
            if latest_rejected:
                raise ValueError(
                    f"No puedes volver a aplicar hasta el {latest_rejected.can_reapply_after.strftime('%d/%m/%Y')}"
                )
            
            print(f"terminos y condiciones: {kwargs.get('accepts_terms_and_conditions')}")
            
            # 4. Validar aceptaciones requeridas
            FinancialInstitutionApplicationService._validate_required_acceptances(
                kwargs.get('accepts_terms_and_conditions', False),
                kwargs.get('accepts_risk_disclosure', False),
                kwargs.get('confirms_information_accuracy', False),
                kwargs.get('authorizes_background_check', False)
            )
            
            # 5. Preparar datos de la solicitud
            application_data = {
                'user': user,
                'financial_institution': financial_institution,
                'requested_investor_profile': requested_investor_profile,
            }
            
            # Obtener campos válidos del modelo
            model_fields = [f.name for f in FinancialInstitutionApplication._meta.fields]
            
            # Agregar todos los kwargs que correspondan a campos del modelo
            for key, value in kwargs.items():
                if key in model_fields:  # ← Esta línea filtra campos inválidos
                    application_data[key] = value
            
            # 6. Crear nueva solicitud
            application = FinancialInstitutionApplication.objects.create(**application_data)

            # Actualizar auditoría a SUCCESS
            if initial_audit:
                # Actualizar el objeto de referencia a la aplicación creada
                from django.contrib.contenttypes.models import ContentType
                application_content_type = ContentType.objects.get_for_model(FinancialInstitutionApplication)
                initial_audit.content_type = application_content_type
                initial_audit.object_id = application.id
                
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({
                    'application_id': application.id,
                    'application_status': application.status,
                    'validation_passed': True,
                    'requested_investor_profile': requested_investor_profile
                })
                initial_audit.save(update_fields=['status', 'details', 'content_type', 'object_id'])
            
            return application
        
        except Exception as e:
            # Auditar error
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'fi_id': financial_institution.id if financial_institution else None
                })
                initial_audit.save(update_fields=['status', 'details'])
            
            # Re-lanzar la excepción apropiada
            if isinstance(e, ValueError):
                raise e
            else:
                raise FIApplicationError(f"Error creando solicitud de ingreso al fondo: {str(e)}")
    
    @staticmethod
    def _validate_required_acceptances(
        accepts_terms: bool,
        accepts_risk: bool,
        confirms_accuracy: bool,
        authorizes_check: bool
    ):
        required_acceptances = {
            'accepts_terms': accepts_terms,
            'accepts_risk': accepts_risk,
            'confirms_accuracy': confirms_accuracy,
            'authorizes_check': authorizes_check
        }
        
        missing = [name for name, accepted in required_acceptances.items() if not accepted]
        
        if missing:
            missing_text = ', '.join(missing)
            raise ValueError(f"Debes aceptar todos los términos requeridos: {missing_text}")
    
    
