from decimal import Decimal
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.fund.models.core import Fund
from apps.audit.audit_service import AuditService
from apps.kaleido.utils import create_wallet_for_fund, create_instance_token_contract_721
from apps.kaleido.models import PromoteContract


class FundServiceError(Exception):
    """Excepción personalizada para errores del servicio de fondos"""
    pass


class FundCreationService:
    """
    Servicio de Creación de Fondos - Maneja toda la lógica de negocio
    
    Responsabilidades:
    - Crear fondos con validaciones de negocio
    - Integración con Kaleido (wallet + contrato de tokens)
    - Gestionar estados y transiciones
    - Integración con auditoría
    """
    
    @staticmethod
    def create_fund(user, fund_data: Dict[str, Any], request=None) -> Fund:
        """
        Crear un nuevo fondo con toda la infraestructura necesaria
        
        Args:
            user: Usuario creador del fondo
            fund_data: Datos del fondo a crear
            request: Request HTTP para auditoría (opcional)
            
        Returns:
            Fund: Nuevo fondo creado con wallet y contrato
            
        Raises:
            ValidationError: Si las validaciones de negocio fallan
            FundServiceError: Si falla la creación de infraestructura
        """
        initial_audit = None
        
        try:
            # 1. Validaciones de negocio
            FundCreationService._validate_fund_data(fund_data)
            
            # 2. Crear auditoría inicial si tenemos request
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="FUND_CREATE",
                    obj=user,  # Usamos el usuario como referencia hasta crear el fondo
                    details={
                        'name': fund_data.get('name'),
                        'amount': str(fund_data.get('amount', 0)),
                        'operation': 'create_fund'
                    },
                    status='PENDING'
                )
                
            with transaction.atomic():
                # 3. Crear el fondo base
                fund = FundCreationService._create_fund_base(user, fund_data)
                
                # 4. Crear infraestructura Kaleido
                FundCreationService._setup_kaleido_infrastructure(fund, user, initial_audit)
                
            # 5. Actualizar auditoría a SUCCESS
            if initial_audit:
                # Actualizar el objeto de referencia al fondo creado
                from django.contrib.contenttypes.models import ContentType
                fund_content_type = ContentType.objects.get_for_model(Fund)
                initial_audit.content_type = fund_content_type
                initial_audit.object_id = fund.id
                
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({
                    'fund_id': fund.id,
                    'wallet_created': bool(fund.hd_wallet),
                    'contract_created': bool(fund.token_contract_721)
                })
                initial_audit.save(update_fields=['status', 'details', 'content_type', 'object_id'])
            
            return fund
                
        except Exception as e:
            # Auditar error
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                initial_audit.save(update_fields=['status', 'details'])
            
            # Re-lanzar la excepción
            if isinstance(e, ValidationError):
                raise e
            else:
                raise FundServiceError(f"Error creando vehiculo de inversion: {str(e)}")
    
    # ========================================
    # Métodos privados de validación
    # ========================================
    
    @staticmethod
    def _validate_fund_data(fund_data: Dict[str, Any]):
        """Validar lógica de negocio del fondo"""
        
        # Validar nombre único (lógica de negocio)
        if Fund.objects.filter(name=fund_data['name']).exists():
            raise ValidationError("Ya existe un fondo con este nombre")
        
        # Validar contrato promocional existe (lógica de negocio)
        promote_contract_id = fund_data.get('promote_contract_id')
        if promote_contract_id:
            try:
                PromoteContract.objects.get(id=promote_contract_id)
            except PromoteContract.DoesNotExist:
                raise ValidationError("El contrato promocional especificado no existe")
        
    
    # ========================================
    # Métodos privados de creación
    # ========================================
    
    @staticmethod
    def _create_fund_base(user, fund_data: Dict[str, Any]) -> Fund:
        """Crear el objeto Fund base sin infraestructura externa"""
        # Extraer promote_contract_id antes de crear el fondo
        promote_contract_id = fund_data.pop('promote_contract_id', None)
        
        # Crear el fondo
        fund = Fund.objects.create(
            user=user,
            **fund_data
        )
        
        # Guardar el promote_contract_id para uso posterior si existe
        if promote_contract_id:
            fund._promote_contract_id = promote_contract_id
        
        return fund
    
    @staticmethod
    def _setup_kaleido_infrastructure(fund: Fund, user, audit=None):
        """Configurar infraestructura de Kaleido (wallet + contrato)"""
        try:
            # 1. Crear wallet para el fondo
            wallet, wallet_error = create_wallet_for_fund(user, fund.secret)
            if not wallet:
                if audit:
                    audit.details.update({
                        'kaleido_error': f"Error al crear la wallet: {wallet_error}",
                        'step': 'wallet_creation'
                    })
                raise FundServiceError(f"Error creando la wallet: {wallet_error}")
            
            fund.hd_wallet = wallet
            fund.save(update_fields=['hd_wallet'])
            
            # 2. Obtener promote_contract si se especificó
            promote_contract = None
            if hasattr(fund, '_promote_contract_id'):
                promote_contract = PromoteContract.objects.get(id=fund._promote_contract_id)
            
            # 3. Crear instancia del contrato de tokens
            token_instance, token_error = create_instance_token_contract_721(
                user,
                fund.name,
                fund.name[:3].upper(),  # Símbolo basado en las primeras 3 letras
                promote_contract=promote_contract
            )
            if not token_instance:
                if audit:
                    audit.details.update({
                        'kaleido_error': f"Error en la creacion de token_instance: {token_error}",
                        'step': 'token_contract_creation'
                    })
                raise FundServiceError(f"Error creando contrato del token: {token_error}")
            
            fund.token_contract_721 = token_instance
            fund.save(update_fields=['token_contract_721'])
            
        except Exception as e:
            # Si falla la infraestructura de Kaleido, el fondo ya fue creado
            # pero sin la infraestructura completa
            if audit:
                audit.details.update({
                    'kaleido_error': str(e),
                    'fund_created_but_incomplete': True
                })
            raise FundServiceError(f"Ha ocurrido un error en la blockchain: {str(e)}")
    
    # ========================================
    # Métodos públicos auxiliares
    # ========================================
    
    @staticmethod
    def get_user_funds(user, status: Optional[str] = None):
        """
        Obtener fondos del usuario
        
        Args:
            user: Usuario propietario
            status: Filtro por estado (opcional)
            
        Returns:
            QuerySet: Fondos del usuario
        """
        queryset = Fund.objects.filter(user=user)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('hd_wallet', 'token_contract_721').order_by('-created_at')
    
    @staticmethod
    def validate_fund_name_availability(name: str, exclude_id: Optional[int] = None) -> bool:
        """
        Validar disponibilidad de nombre de fondo
        
        Args:
            name: Nombre a validar
            exclude_id: ID de fondo a excluir (para actualizaciones)
            
        Returns:
            bool: True si está disponible
        """
        queryset = Fund.objects.filter(name=name)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        return not queryset.exists()
    
    @staticmethod
    def update_fund_status(fund: Fund, new_status: str, request=None) -> Fund:
        """
        Actualizar estado del fondo con auditoría
        
        Args:
            fund: Fondo a actualizar
            new_status: Nuevo estado
            request: Request HTTP para auditoría (opcional)
            
        Returns:
            Fund: Fondo actualizado
        """
        old_status = fund.status
        
        if request:
            AuditService.log_action(
                request=request,
                action_code="FUND_STATUS_UPDATE",
                obj=fund,
                details={
                    'old_status': old_status,
                    'new_status': new_status,
                    'operation': 'update_status'
                },
                status='SUCCESS'
            )
        
        fund.status = new_status
        fund.save(update_fields=['status'])
        
        return fund