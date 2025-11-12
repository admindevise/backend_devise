"""
Servicio de creación de Assets
Maneja la lógica de negocio para la gestión de activos inmobiliarios
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.asset.models.core import Asset, AssetType
from apps.fund.models.core import Fund
from apps.audit.audit_service import AuditService


class AssetServiceError(Exception):
    """Excepción personalizada para errores del servicio de assets"""
    pass


class AssetCreationService:
    """
    Servicio de Creación de Assets - Maneja toda la lógica de negocio
    
    Responsabilidades:
    - Crear assets con validaciones de negocio
    - Vincular assets a fondos
    - Gestionar estados y transiciones
    - Integración con auditoría
    """
    
    @staticmethod
    @transaction.atomic
    def create_asset(user, asset_data: Dict[str, Any], request=None) -> Asset:
        """
        Crea un nuevo asset con todas las validaciones necesarias
        
        Args:
            user: Usuario creador del asset (debe estar vinculado al fund.created_by o ser staff)
            asset_data: Datos del asset a crear
            request: Request HTTP para auditoría (opcional)
            
        Returns:
            Asset: Nuevo asset creado
            
        Raises:
            ValidationError: Si las validaciones de negocio fallan
            AssetServiceError: Si falla la creación del asset
            
        Example:
            >>> asset_data = {
            ...     'fund_id': 1,
            ...     'asset_type_id': 2,
            ...     'name': 'Edificio Plaza Central',
            ...     'description': 'Edificio comercial en el centro',
            ...     'address': 'Calle 100 #15-20',
            ...     'city': 'Bogotá',
            ...     'state': 'Cundinamarca',
            ...     'total_area_m2': Decimal('1500.00'),
            ...     'acquisition_value': Decimal('5000000000'),
            ...     'acquisition_date': '2024-01-15'
            ... }
            >>> asset = AssetCreationService.create_asset(user, asset_data, request)
        """
        initial_audit = None
        
        try:
            # 1. Validaciones de negocio
            AssetCreationService._validate_asset_data(asset_data)
            
            # 2. Validar que el usuario tenga permisos
            fund = Fund.objects.get(id=asset_data['fund_id'])
            
            # 3. Crear auditoría inicial si tenemos request
            if request:
                initial_audit = AuditService.log_action(
                    request=request,
                    action_code="ASSET_CREATE",
                    obj=user,
                    details={
                        'fund_id': asset_data.get('fund_id'),
                        'asset_name': asset_data.get('name'),
                        'asset_type_id': asset_data.get('asset_type_id'),
                        'acquisition_value': str(asset_data.get('acquisition_value', 0)),
                        'operation': 'create_asset'
                    },
                    status='PENDING'
                )
            
            # 4. Crear el asset
            asset = AssetCreationService._create_asset_base(user, fund, asset_data)
            
            # 5. Actualizar auditoría a SUCCESS
            if initial_audit:
                initial_audit.object_id = asset.id
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({
                    'asset_id': asset.id,
                    'asset_code': asset.asset_code,
                    'status': asset.status
                })
                initial_audit.save(update_fields=['status', 'details', 'object_id'])
            
            return asset
                
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
                raise AssetServiceError(f"Error creando activo: {str(e)}")
    
    # ========================================
    # Métodos privados de validación
    # ========================================
    
    @staticmethod
    def _validate_asset_data(asset_data: Dict[str, Any]):
        """Validar lógica de negocio del asset"""
        
        # Validar campos requeridos
        required_fields = [
            'fund_id', 'asset_type_id', 'name', 'description',
            'address', 'city', 'state', 'total_area_m2',
            'acquisition_value', 'acquisition_date'
        ]
        
        missing_fields = [field for field in required_fields if not asset_data.get(field)]
        if missing_fields:
            raise ValidationError({
                'missing_fields': f"Campos requeridos faltantes: {', '.join(missing_fields)}"
            })
        
        # Validar que el fondo exista
        try:
            Fund.objects.get(id=asset_data['fund_id'])
        except Fund.DoesNotExist:
            raise ValidationError({
                'fund_id': 'El fondo especificado no existe'
            })
        
        # Validar que el tipo de asset exista
        try:
            AssetType.objects.get(id=asset_data['asset_type_id'])
        except AssetType.DoesNotExist:
            raise ValidationError({
                'asset_type_id': 'El tipo de activo especificado no existe'
            })
        
        # Validar valores numéricos
        if asset_data.get('total_area_m2'):
            if asset_data['total_area_m2'] <= 0:
                raise ValidationError({
                    'total_area_m2': 'El área total debe ser mayor a cero'
                })
        
        if asset_data.get('acquisition_value'):
            if asset_data['acquisition_value'] <= 0:
                raise ValidationError({
                    'acquisition_value': 'El valor de adquisición debe ser mayor a cero'
                })
        
        # Validar coherencia de áreas
        if asset_data.get('built_area_m2') and asset_data.get('total_area_m2'):
            if asset_data['built_area_m2'] > asset_data['total_area_m2']:
                raise ValidationError({
                    'built_area_m2': 'El área construida no puede ser mayor al área total'
                })
        
        # Validar fechas de arrendamiento si aplica
        if asset_data.get('is_leased'):
            if not asset_data.get('monthly_rent'):
                raise ValidationError({
                    'monthly_rent': 'Debe especificar la renta mensual si el activo está arrendado'
                })
            
            if asset_data.get('lease_start_date') and asset_data.get('lease_end_date'):
                if asset_data['lease_end_date'] <= asset_data['lease_start_date']:
                    raise ValidationError({
                        'lease_end_date': 'La fecha de fin debe ser posterior a la fecha de inicio'
                    })
    
    # ========================================
    # Métodos privados de creación
    # ========================================
    
    @staticmethod
    def _create_asset_base(user, fund: Fund, asset_data: Dict[str, Any]) -> Asset:
        """Crear el objeto Asset base"""
        
        # Extraer IDs para obtener objetos relacionados
        asset_type = AssetType.objects.get(id=asset_data.pop('asset_type_id'))
        asset_data.pop('fund_id')  # Ya tenemos el objeto fund
        
        # Generar código único del asset si no se proporciona
        if not asset_data.get('asset_code'):
            asset_data['asset_code'] = AssetCreationService._generate_asset_code()
        
        # Crear el asset
        asset = Asset.objects.create(
            fund=fund,
            asset_type=asset_type,
            created_by=user,
            **asset_data
        )
        
        return asset
    
    @staticmethod
    def _generate_asset_code() -> str:
        """Genera un código único para el asset"""
        from django.utils.crypto import get_random_string
        
        # Obtener el último asset para incrementar el código
        last_asset = Asset.objects.order_by('-id').first()
        
        if last_asset:
            # Extraer número del último código (ej: AST-00001 -> 1)
            try:
                last_number = int(last_asset.asset_code.split('-')[1])
                new_number = last_number + 1
            except (IndexError, ValueError):
                new_number = 1
        else:
            new_number = 1
        
        # Generar código con formato AST-00001
        return f"AST-{new_number:05d}"
    
    # ========================================
    # Métodos públicos auxiliares
    # ========================================
    
    @staticmethod
    def get_assets_by_fund(fund_id: int, status: Optional[str] = None):
        """
        Obtiene todos los assets de un fondo específico
        
        Args:
            fund_id: ID del fondo
            status: Filtrar por estado (opcional)
            
        Returns:
            QuerySet de Assets
        """
        queryset = Asset.objects.filter(fund_id=fund_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('fund', 'asset_type', 'created_by')
    
    @staticmethod
    def get_user_assets(user):
        """
        Obtiene todos los assets creados por un usuario
        
        Args:
            user: Usuario
            
        Returns:
            QuerySet de Assets
        """
        return Asset.objects.filter(created_by=user).select_related(
            'fund', 'asset_type'
        )
    
    @staticmethod
    def update_asset_status(asset: Asset, new_status: str, request=None) -> Asset:
        """
        Actualiza el estado de un asset con auditoría
        
        Args:
            asset: Instancia del asset
            new_status: Nuevo estado
            request: Request HTTP para auditoría
            
        Returns:
            Asset actualizado
        """
        old_status = asset.status
        
        # Validar que el nuevo estado sea válido
        valid_statuses = [choice[0] for choice in Asset.AssetStatus.choices]
        if new_status not in valid_statuses:
            raise ValidationError({
                'status': f'Estado inválido. Debe ser uno de: {", ".join(valid_statuses)}'
            })
        
        asset.status = new_status
        asset.save(update_fields=['status'])
        
        # Auditar el cambio
        if request:
            AuditService.log_action(
                request=request,
                action_code="ASSET_STATUS_CHANGE",
                obj=asset,
                details={
                    'asset_id': asset.id,
                    'asset_code': asset.asset_code,
                    'old_status': old_status,
                    'new_status': new_status
                },
                status='SUCCESS'
            )
        
        return asset
    
    @staticmethod
    def validate_asset_code_availability(asset_code: str, exclude_id: Optional[int] = None) -> bool:
        """
        Verifica si un código de asset está disponible
        
        Args:
            asset_code: Código a verificar
            exclude_id: ID de asset a excluir (para updates)
            
        Returns:
            True si está disponible, False si ya existe
        """
        queryset = Asset.objects.filter(asset_code=asset_code)
        
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        
        return not queryset.exists()