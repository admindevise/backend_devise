from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from datetime import timedelta
from django.db import models

from apps.user.models_permission import (
    UserAdminPermission,
    PendingPermissionAction,
    PermissionExecution
)

class TradingPermissionService:
    """Servicio para gestión y verificación de permisos de trading"""
    @staticmethod
    def _make_json_safe(data):
        if isinstance(data, Decimal):
            return str(data)
        if isinstance(data, (date, datetime)):
            return str(data)
        if hasattr(data, 'id'):
            return data.id
        if isinstance(data, dict):
            return {key: TradingPermissionService._make_json_safe(value) for key, value in data.items()}
        if isinstance(data, list):
            return [TradingPermissionService._make_json_safe(value) for value in data]
        return data    
    
    @staticmethod
    def grant_trading_permission(
        user,
        admin_user,
        permission_type: str,
        fund_id: Optional[int] = None,
        duration_hours: int = 24,
        max_order_amount: Optional[Decimal] = None,
        max_daily_amount: Optional[Decimal] = None,
        auto_approve_under: Optional[Decimal] = None,
        require_confirmation: bool = True,
        reason: str = ""
    ) -> UserAdminPermission:
        """Otorga permiso específico de trading"""
        
        expires_at = timezone.now() + timedelta(hours=duration_hours)
        
        # Obtener objeto Fund si fund_id es proporcionado
        fund = None
        if fund_id:
            from apps.fund.models import Fund
            try:
                fund = Fund.objects.get(id=fund_id)
            except Fund.DoesNotExist:
                raise ValueError(f"Fund with id {fund_id} does not exist")
        
        permission = UserAdminPermission.objects.create(
            user=user,
            admin_user=admin_user,
            permission_type=permission_type,
            fund=fund,
            expires_at=expires_at,
            max_order_amount=max_order_amount,
            max_daily_amount=max_daily_amount,
            auto_approve_under_amount=auto_approve_under,
            require_confirmation=require_confirmation,
            reason=reason,
            status='ACTIVE'
        )
        
        print(f"✅ Permission created: ID {permission.id}, Type: {permission.permission_type}")
        return permission
    
    @staticmethod
    def renew_if_exists(
        user,
        admin_user,
        permission_type,
        fund_id,
        duration_hours,
        max_order_amount=None,
        max_daily_amount=None,
        auto_approve_under=None,
        require_confirmation=True,
        reason=""
    ):
        # Busca el último permiso histórico (activo o no)
        qs = UserAdminPermission.objects.filter(
            user=user,
            admin_user=admin_user,
            permission_type=permission_type,
            fund_id=fund_id
        ).order_by('-granted_at')

        permission = qs.first()
        if not permission:
            return None

        now = timezone.now()
        permission.status = 'ACTIVE'
        permission.granted_at = now
        permission.expires_at = now + timedelta(hours=duration_hours)
        permission.max_order_amount = max_order_amount
        permission.max_daily_amount = max_daily_amount
        permission.auto_approve_under_amount = auto_approve_under
        permission.require_confirmation = require_confirmation
        permission.reason = reason
        permission.save()

        return permission    
    
    @staticmethod
    def check_permission(
        admin_user,
        target_user, 
        action_type: str,
        fund_id: Optional[int] = None,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Verifica si el admin tiene permiso para ejecutar una acción"""
        
        print(f"\n🔍 TradingPermissionService.check_permission:")
        print(f"  - Admin: {admin_user.email}")
        print(f"  - Target: {target_user.email}")
        print(f"  - Action: {action_type}")
        print(f"  - Fund ID: {fund_id}")
        print(f"  - Amount: {amount}")
        
        # Buscar permisos válidos
        permissions_query = UserAdminPermission.objects.filter(
            user=target_user,
            admin_user=admin_user,
            status='ACTIVE',
            expires_at__gt=timezone.now()
        )
        
        print(f"📋 Query: {permissions_query.query}")
        print(f"📋 Found {permissions_query.count()} permissions")
        
        for p in permissions_query:
            print(f"  - ID: {p.id}, Type: {p.permission_type}, Fund: {p.fund.id if p.fund else 'ALL'}")
        
        # Filtrar por tipo de acción
        relevant_permissions = []
        for perm in permissions_query:
            matches = TradingPermissionService._action_matches_permission(action_type, perm.permission_type)
            print(f"🔍 Permission {perm.id} ({perm.permission_type}) matches {action_type}: {matches}")
            
            if matches:
                fund_matches = not fund_id or not perm.fund or perm.fund.id == fund_id
                print(f"🔍 Fund matches: {fund_matches} (perm.fund: {perm.fund.id if perm.fund else 'ALL'})")
                
                if fund_matches:
                    relevant_permissions.append(perm)
                    print(f"✅ Permission {perm.id} added to relevant list")
        
        print(f"📊 Relevant permissions: {len(relevant_permissions)}")
        
        if not relevant_permissions:
            return {
                'allowed': False,
                'reason': 'No tienes permisos para esta acción',
                'requires_permission': True
            }
        
        # Verificar límites para cada permiso relevante
        for perm in relevant_permissions:
            validation = TradingPermissionService._validate_limits(perm, amount)
            if validation['allowed']:
                return {
                    'allowed': True,
                    'permission': perm,
                    'requires_confirmation': perm.require_confirmation and (
                        not perm.auto_approve_under_amount or 
                        not amount or 
                        amount > perm.auto_approve_under_amount
                    )
                }
        
        return {
            'allowed': False,
            'reason': 'Acción excede los límites permitidos',
            'limits_exceeded': True
        }
    
    @staticmethod
    def _action_matches_permission(action_type: str, permission_type: str) -> bool:
        """Verifica si un tipo de acción coincide con un tipo de permiso"""
        
        # ✅ MAPEO CORRECTO Y COMPLETO
        action_mapping = {
            'CREATE_PURCHASE_ORDER': [
                'CREATE_PURCHASE_ORDER',  # ✅ Mapeo directo
                'PURCHASE_ORDERS', 
                'ALL_TRADING',
                'TRADING_FULL_ACCESS'
            ],
            'CREATE_SALES_ORDER': [
                'CREATE_SALES_ORDER',     # ✅ Mapeo directo
                'SALES_ORDERS', 
                'ALL_TRADING',
                'TRADING_FULL_ACCESS'
            ],
            'EXECUTE_PAYMENT': [
                'EXECUTE_PAYMENT',
                'EXECUTE_PAYMENTS', 
                'ALL_TRADING',
                'TRADING_FULL_ACCESS'
            ],
            'CANCEL_ORDER': [
                'CANCEL_ORDER',
                'CANCEL_ORDERS', 
                'ALL_TRADING',
                'TRADING_FULL_ACCESS'
            ],
        }
        
        matches = permission_type in action_mapping.get(action_type, [])
        print(f"🔍 _action_matches_permission({action_type}, {permission_type}) = {matches}")
        
        return matches
    
    @staticmethod
    def _validate_limits(permission: UserAdminPermission, amount: Optional[Decimal]) -> Dict[str, Any]:
        """Valida los límites del permiso"""
        
        print(f"🔍 Validating limits for permission {permission.id}")
        print(f"  - Amount: {amount}")
        print(f"  - Max order: {permission.max_order_amount}")
        
        # Verificar límite por orden
        if amount and permission.max_order_amount and amount > permission.max_order_amount:
            return {
                'allowed': False,
                'reason': f'Monto {amount} excede el límite por orden {permission.max_order_amount}'
            }
        
        # Verificar límite diario
        if amount and permission.max_daily_amount:
            today_usage = PermissionExecution.objects.filter(
                permission=permission,
                executed_at__date=timezone.now().date(),
                success=True
            ).aggregate(
                total=models.Sum('action_data__total_amount')
            )['total'] or Decimal('0')
            
            if (today_usage + amount) > permission.max_daily_amount:
                return {
                    'allowed': False,
                    'reason': f'Límite diario excedido. Usado: {today_usage}, Límite: {permission.max_daily_amount}'
                }
        
        # Verificar número máximo de usos
        if permission.max_uses and permission.usage_count >= permission.max_uses:
            return {
                'allowed': False,
                'reason': 'Permiso agotado por número de usos'
            }
        
        print(f"✅ Limits validation passed")
        return {'allowed': True}
    
    @staticmethod
    def log_permission_usage(permission: UserAdminPermission, action_type: str, action_data: Dict[str, Any], success: bool = True):
        """Registra el uso de un permiso para auditoría"""
        from datetime import date, datetime
        # Incrementar contador de uso
        permission.usage_count += 1
        permission.save(update_fields=['usage_count'])
        
        print(f"ACTION DATA: {action_data} y {action_data.get('total_amount')} itemsss {action_data.items()}")
        
        serializable_data = TradingPermissionService._make_json_safe(action_data)
        
        # Crear registro de ejecución
        PermissionExecution.objects.create(
            permission=permission,
            action_type=action_type,
            purchase_order_id=action_data.get('purchase_order_id'),
            sales_order_id=action_data.get('sales_order_id'),
            amount=Decimal(action_data.get('amount')) if action_data.get('amount') else None,
            units=action_data.get('units'),
            success=success,
            result_data=serializable_data,  # ✅ usar datos serializables
            executed_at=timezone.now()
        )
    
    @staticmethod
    def request_approval(
        permission: UserAdminPermission,
        action_type: str,
        action_data: Dict[str, Any],
        amount: Optional[Decimal] = None,
        description: str = ""
    ) -> PendingPermissionAction:
        """Solicita aprobación para una acción específica"""
        
        expires_at = timezone.now() + timedelta(hours=2)  # 2 horas para responder
        
        safe_action_data = TradingPermissionService._make_json_safe(action_data)
        
        pending_action = PendingPermissionAction.objects.create(
            permission=permission,
            admin_user=permission.admin_user,
            action_type=action_type,
            action_description=description,
            action_data=safe_action_data,
            amount=amount,
            fund=permission.fund,
            expires_at=expires_at
        )
        
        return pending_action
    
    @staticmethod
    def get_active_permissions(user, admin_user, permission_type: Optional[str] = None, fund: Optional[Any] = None):
        """Obtiene permisos activos para un usuario y admin específicos"""
        
        query = UserAdminPermission.objects.filter(
            user=user,
            admin_user=admin_user,
            status='ACTIVE',
            fund=fund,
            expires_at__gt=timezone.now()
        )
        
        if permission_type:
            query = query.filter(permission_type=permission_type)
        
        return query

