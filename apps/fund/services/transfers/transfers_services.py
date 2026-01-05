"""
Servicio para gestión de Cesiones (Transfers)
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import date
from django.db import transaction
from django.db.models import QuerySet, Sum, Count, Q
from django.core.exceptions import ValidationError

from apps.fund.models.core import Fund
from apps.fund.models.commissions import Transfers
from .validators import TransferValidator


class TransferServiceError(Exception):
    """Excepción personalizada para errores del servicio de cesiones"""
    pass


class TransferService:
    """
    Servicio para gestionar cesiones de participaciones en fondos.
    Maneja la lógica de negocio para crear, consultar y gestionar cesiones.
    """
    
    def __init__(self, fund: Optional[Fund] = None):
        """
        Inicializa el servicio.
        
        Args:
            fund: Fondo específico (opcional, para operaciones por fondo)
        """
        self.fund = fund
        self.validator = TransferValidator()
    
    # ========================================
    # MÉTODOS DE CREACIÓN
    # ========================================
    
    @transaction.atomic
    def create_transfer(
        self,
        fund: Fund,
        effective_date: date,
        class_transfer: str,
        settlor: str,
        assignee: str,
        assigned_amount: Decimal,
        # Datos del cedente
        actor_settlor: str,
        nit_settlor: int,
        type_doc_settlor: str,
        id_doc_settlor: int,
        # Datos del cesionario
        actor_assignee: str,
        nit_assignee: int,
        type_doc_assignee: str,
        id_doc_assignee: int,
        # Opcionales
        doc_transfer=None,
        created_by=None,
    ) -> Transfers:
        """
        Crea una nueva cesión de participación.
        
        Args:
            fund: Fondo asociado a la cesión
            effective_date: Fecha de vigencia de la cesión
            class_transfer: Clase de cesión que se adquirió
            settlor: Actor que cede su participación
            assignee: Actor que recibe la participación
            assigned_amount: Monto acordado entre las partes
            actor_settlor: Representante legal del cedente
            nit_settlor: NIT del cedente
            type_doc_settlor: Tipo de documento del representante del cedente
            id_doc_settlor: Número de documento del representante del cedente
            actor_assignee: Representante legal del cesionario
            nit_assignee: NIT del cesionario
            type_doc_assignee: Tipo de documento del representante del cesionario
            id_doc_assignee: Número de documento del representante del cesionario
            doc_transfer: Documento de cesión (opcional)
            created_by: Usuario que crea el registro
            
        Returns:
            Transfers: La cesión creada
            
        Raises:
            TransferServiceError: Si hay errores de validación
        """
        # Preparar datos para validación
        transfer_data = {
            'fund': fund,
            'effective_date': effective_date,
            'class_transfer': class_transfer,
            'settlor': settlor,
            'assignee': assignee,
            'assigned_amount': assigned_amount,
            'actor_settlor': actor_settlor,
            'nit_settlor': nit_settlor,
            'type_doc_settlor': type_doc_settlor,
            'id_doc_settlor': id_doc_settlor,
            'actor_assignee': actor_assignee,
            'nit_assignee': nit_assignee,
            'type_doc_assignee': type_doc_assignee,
            'id_doc_assignee': id_doc_assignee,
        }
        
        # Validar datos
        validation_result = self.validator.validate_transfer_creation(transfer_data)
        if not validation_result['is_valid']:
            raise TransferServiceError(
                f"Error de validación: {validation_result['errors']}"
            )
        
        # Crear la cesión
        try:
            transfer = Transfers.objects.create(
                fund=fund,
                effective_date=effective_date,
                class_transfer=class_transfer,
                settlor=settlor,
                assignee=assignee,
                assigned_amount=assigned_amount,
                actor_settlor=actor_settlor,
                nit_settlor=nit_settlor,
                type_doc_settlor=type_doc_settlor,
                id_doc_settlor=id_doc_settlor,
                actor_assignee=actor_assignee,
                nit_assignee=nit_assignee,
                type_doc_assignee=type_doc_assignee,
                id_doc_assignee=id_doc_assignee,
                doc_transfer=doc_transfer,
            )
            
            return transfer
            
        except ValidationError as e:
            # Error de validación de Django
            raise TransferServiceError(f"Error de validación al crear cesión: {e.message_dict if hasattr(e, 'message_dict') else str(e)}")
        except Exception as e:
            # Cualquier otro error con más detalles
            import traceback
            raise TransferServiceError(f"Error al crear cesión: {str(e)}\nTipo: {type(e).__name__}\nDetalles: {traceback.format_exc()}")
    
    @transaction.atomic
    def update_transfer(
        self,
        transfer_id: int,
        update_data: Dict[str, Any]
    ) -> Transfers:
        """
        Actualiza una cesión existente.
        
        Args:
            transfer_id: ID de la cesión a actualizar
            update_data: Diccionario con los campos a actualizar
            
        Returns:
            Transfers: La cesión actualizada
            
        Raises:
            TransferServiceError: Si hay errores
        """
        try:
            transfer = Transfers.objects.get(id=transfer_id)
        except Transfers.DoesNotExist:
            raise TransferServiceError(f"Cesión con ID {transfer_id} no encontrada")
        
        # Validar campos actualizables
        allowed_fields = {
            'effective_date', 'class_transfer', 'settlor', 'assignee',
            'assigned_amount', 'actor_settlor', 'nit_settlor', 
            'type_doc_settlor', 'id_doc_settlor', 'actor_assignee',
            'nit_assignee', 'type_doc_assignee', 'id_doc_assignee',
            'doc_transfer'
        }
        
        # Filtrar solo campos permitidos
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            raise TransferServiceError("No hay campos válidos para actualizar")
        
        # Validar si se actualiza el monto
        if 'assigned_amount' in filtered_data:
            validation = self.validator.validate_amount(filtered_data['assigned_amount'])
            if not validation['is_valid']:
                raise TransferServiceError(validation['errors'][0])
        
        # Actualizar campos
        for field, value in filtered_data.items():
            setattr(transfer, field, value)
        
        transfer.save()
        return transfer
    
    # ========================================
    # MÉTODOS DE ESTADÍSTICAS Y REPORTES
    # ========================================
    
    def get_fund_transfer_summary(self, fund: Fund) -> Dict[str, Any]:
        """
        Obtiene un resumen de cesiones para un fondo.
        
        Args:
            fund: Fondo a consultar
            
        Returns:
            Diccionario con estadísticas del fondo
        """
        transfers = Transfers.objects.filter(fund=fund)
        
        aggregates = transfers.aggregate(
            total_amount=Sum('assigned_amount'),
            total_count=Count('id')
        )
        
        # Obtener cesiones por año
        from django.db.models.functions import ExtractYear
        by_year = transfers.annotate(
            year=ExtractYear('effective_date')
        ).values('year').annotate(
            count=Count('id'),
            amount=Sum('assigned_amount')
        ).order_by('-year')
        
        return {
            'fund_id': fund.id,
            'fund_name': fund.name,
            'total_transfers': aggregates['total_count'] or 0,
            'total_amount': aggregates['total_amount'] or Decimal('0.00'),
            'transfers_by_year': list(by_year),
            'last_transfer': transfers.order_by('-effective_date').first(),
        }
    
    
    # ========================================
    # MÉTODOS DE ELIMINACIÓN
    # ========================================
    
    @transaction.atomic
    def delete_transfer(self, transfer_id: int) -> bool:
        """
        Elimina una cesión.
        
        Args:
            transfer_id: ID de la cesión a eliminar
            
        Returns:
            True si se eliminó correctamente
            
        Raises:
            TransferServiceError: Si hay errores
        """
        try:
            transfer = Transfers.objects.get(id=transfer_id)
            transfer.delete()
            return True
        except Transfers.DoesNotExist:
            raise TransferServiceError(f"Cesión con ID {transfer_id} no encontrada")
        except Exception as e:
            raise TransferServiceError(f"Error al eliminar cesión: {str(e)}")
