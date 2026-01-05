"""
Servicio para gestión de Comisiones (Commissions)
"""

from typing import Dict, Optional, Any
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.fund.models.core import Fund
from apps.fund.models.commissions import Commissions
from .validators import CommissionValidator


class CommissionServiceError(Exception):
    """Excepción personalizada para errores del servicio de comisiones"""
    pass


class CommissionService:
    """
    Servicio para gestionar comisiones de fondos.
    Maneja la lógica de negocio para crear y gestionar comisiones.
    """
    
    def __init__(self, fund: Optional[Fund] = None):
        """
        Inicializa el servicio.
        
        Args:
            fund: Fondo específico (opcional, para operaciones por fondo)
        """
        self.fund = fund
        self.validator = CommissionValidator()
    
    # ========================================
    # MÉTODOS DE CREACIÓN
    # ========================================
    
    @transaction.atomic
    def create_commission(
        self,
        fund: Fund,
        contract_num: str,
        name: str,
        description: str,
        amount: str,
    ) -> Commissions:
        """
        Crea una nueva comisión.
        
        Args:
            fund: Fondo asociado a la comisión
            contract_num: Sección del contrato que especifica la comisión
            name: Nombre de la comisión
            description: Detalle de la comisión
            amount: Monto acordado en el contrato
            
        Returns:
            Commissions: La comisión creada
            
        Raises:
            CommissionServiceError: Si hay errores de validación
        """
        # Preparar datos para validación
        commission_data = {
            'fund': fund,
            'contract_num': contract_num,
            'name': name,
            'description': description,
            'amount': amount,
        }
        
        # Validar datos
        validation_result = self.validator.validate_commission_creation(commission_data)
        if not validation_result['is_valid']:
            raise CommissionServiceError(
                f"Error de validación: {validation_result['errors']}"
            )
        
        # Crear la comisión
        try:
            commission = Commissions.objects.create(
                fund=fund,
                contract_num=contract_num,
                name=name,
                description=description,
                amount=amount,
            )
            
            return commission
            
        except ValidationError as e:
            raise CommissionServiceError(
                f"Error de validación al crear comisión: {e.message_dict if hasattr(e, 'message_dict') else str(e)}"
            )
        except Exception as e:
            import traceback
            raise CommissionServiceError(
                f"Error al crear comisión: {str(e)}\nTipo: {type(e).__name__}\nDetalles: {traceback.format_exc()}"
            )
    
    # ========================================
    # MÉTODOS DE ACTUALIZACIÓN
    # ========================================
    
    @transaction.atomic
    def update_commission(
        self,
        commission_id: int,
        update_data: Dict[str, Any]
    ) -> Commissions:
        """
        Actualiza una comisión existente.
        
        Args:
            commission_id: ID de la comisión a actualizar
            update_data: Diccionario con los campos a actualizar
            
        Returns:
            Commissions: La comisión actualizada
            
        Raises:
            CommissionServiceError: Si hay errores
        """
        try:
            commission = Commissions.objects.get(id=commission_id)
        except Commissions.DoesNotExist:
            raise CommissionServiceError(f"Comisión con ID {commission_id} no encontrada")
        
        # Campos actualizables
        allowed_fields = {'contract_num', 'name', 'description', 'amount'}
        
        # Filtrar solo campos permitidos
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            raise CommissionServiceError("No hay campos válidos para actualizar")
        
        # Validar datos de actualización
        validation_result = self.validator.validate_update_data(filtered_data)
        if not validation_result['is_valid']:
            raise CommissionServiceError(
                f"Error de validación: {validation_result['errors']}"
            )
        
        # Actualizar campos
        for field, value in filtered_data.items():
            setattr(commission, field, value)
        
        try:
            commission.save()
            return commission
        except Exception as e:
            raise CommissionServiceError(f"Error al actualizar comisión: {str(e)}")
    
    # ========================================
    # MÉTODOS DE ELIMINACIÓN
    # ========================================
    
    @transaction.atomic
    def delete_commission(self, commission_id: int) -> bool:
        """
        Elimina una comisión.
        
        Args:
            commission_id: ID de la comisión a eliminar
            
        Returns:
            True si se eliminó correctamente
            
        Raises:
            CommissionServiceError: Si hay errores
        """
        try:
            commission = Commissions.objects.get(id=commission_id)
            commission.delete()
            return True
        except Commissions.DoesNotExist:
            raise CommissionServiceError(f"Comisión con ID {commission_id} no encontrada")
        except Exception as e:
            raise CommissionServiceError(f"Error al eliminar comisión: {str(e)}")
