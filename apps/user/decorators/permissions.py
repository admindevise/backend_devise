from functools import wraps
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from rest_framework.response import Response
from rest_framework import status

from apps.user.services.permission_service import TradingPermissionService


def require_trading_permission(action_type, extract_target_user=None, extract_amount=None):
    """
    Decorator para validar permisos de trading antes de ejecutar una vista
    
    Args:
        action_type: Tipo de acción ('CREATE_SALES_ORDER', 'CREATE_PURCHASE_ORDER', etc.)
        extract_target_user: Función para extraer el usuario objetivo de la request
        extract_amount: Función para extraer el monto de la request
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Verificar que el usuario esté autenticado
            if isinstance(request.user, AnonymousUser):
                return Response({
                    'error': 'Usuario no autenticado'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Extraer datos necesarios para la validación
            try:
                # Usuario objetivo (por defecto el mismo usuario)
                if extract_target_user:
                    target_user = extract_target_user(request, self, *args, **kwargs)
                else:
                    target_user = getattr(request, 'target_user', request.user)
                
                # Monto (si es relevante)
                amount = None
                if extract_amount:
                    amount = extract_amount(request, self, *args, **kwargs)
                elif hasattr(request, 'data') and 'total_amount' in request.data:
                    amount = Decimal(str(request.data.get('total_amount', 0)))
                
                # Fund ID (si está disponible)
                fund_id = None
                if hasattr(request, 'data') and 'fund' in request.data:
                    fund_id = request.data.get('fund')
                
            except Exception as e:
                return Response({
                    'error': f'Error extrayendo datos para validación: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar permisos
            permission_check = TradingPermissionService.check_permission(
                admin_user=request.user,
                target_user=target_user,
                action_type=action_type,
                fund_id=fund_id,
                amount=amount
            )
            
            if not permission_check['allowed']:
                return Response({
                    'error': permission_check['reason'],
                    'requires_permission': True,
                    'action_type': action_type
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Agregar el permiso al request para uso posterior
            request.permission_used = permission_check['permission']
            
            try:
                # Ejecutar la vista original
                response = view_func(self, request, *args, **kwargs)
                
                # Log exitoso después de ejecutar
                TradingPermissionService.log_permission_usage(
                    permission=permission_check['permission'],
                    action_type=action_type,
                    action_data={
                        'amount': amount,
                        'fund_id': fund_id,
                        'target_user_id': target_user.id,
                        'request_data': getattr(request, 'data', {})
                    },
                    success=True
                )
                
                return response
                
            except Exception as e:
                # Log error
                TradingPermissionService.log_permission_usage(
                    permission=permission_check['permission'],
                    action_type=action_type,
                    action_data={
                        'amount': amount,
                        'fund_id': fund_id,
                        'target_user_id': target_user.id,
                        'error': str(e)
                    },
                    success=False
                )
                raise  # Re-raise la excepción original
            
        return wrapper
    return decorator


def extract_target_user_from_data(request, view, *args, **kwargs):
    """Función helper para extraer usuario objetivo desde request.data"""
    user_id = None
    
    # Buscar en diferentes campos comunes
    for field in ['seller_user', 'supplier_user', 'user_id', 'target_user']:
        if hasattr(request, 'data') and field in request.data:
            user_id = request.data[field]
            break
    
    if user_id:
        from apps.user.models import User
        return User.objects.get(id=user_id)
    
    return request.user


def extract_amount_from_data(request, view, *args, **kwargs):
    """Función helper para extraer monto desde request.data"""
    if hasattr(request, 'data'):
        # Intentar varios campos de monto
        for field in ['total_amount', 'amount', 'price_per_unit']:
            if field in request.data:
                return Decimal(str(request.data[field]))
    
    return None


class TradingPermissionMixin:
    """Mixin para vistas que requieren permisos de trading"""
    permission_action_type = None
    
    def initial(self, request, *args, **kwargs):
        """Validar permisos antes de procesar la request"""
        
        # ✅ AGREGAR: Debug completo
        print(f"\n🔍 TradingPermissionMixin DEBUG:")
        print(f"  - Action: {getattr(self, 'action', 'NO_ACTION')}")
        print(f"  - Permission Type: {getattr(self, 'permission_action_type', 'NO_PERMISSION_TYPE')}")
        print(f"  - User: {request.user.email if hasattr(request.user, 'email') else 'ANONYMOUS'}")
        print(f"  - Is Staff: {getattr(request.user, 'is_staff', False)}")
        print(f"  - Request Data: {getattr(request, 'data', 'NO_DATA')}")
        
        # Ejecutar inicialización del padre PRIMERO
        super().initial(request, *args, **kwargs)
        
        # Solo validar en CREATE con permission_action_type configurado
        if (hasattr(self, 'permission_action_type') and 
            self.permission_action_type and 
            hasattr(self, 'action') and
            self.action == 'create' and 
            hasattr(request.user, 'is_authenticated') and
            request.user.is_authenticated):
            
            print(f"🎯 Validando permisos para acción: {self.action}")
            
            # Extraer datos
            target_user = self.get_target_user(request)
            amount = self.get_amount(request)
            fund_id = self.get_fund_id(request)
            
            print(f"  - Target User: {target_user.email if target_user else 'None'}")
            print(f"  - Amount: {amount}")
            print(f"  - Fund ID: {fund_id}")
            
            # CASO 1: Usuario creando para sí mismo
            if target_user == request.user:
                print("✅ Usuario creando orden para sí mismo - PERMITIDO")
                return
            
            # CASO 2: Admin creando para otro usuario
            if not request.user.is_staff:
                print("❌ Usuario no-admin intentando crear para otro")
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Solo administradores pueden crear órdenes para otros usuarios')
            
            print("🔍 Verificando permisos de admin...")
            
            # Importar el servicio
            from apps.user.services.permission_service import TradingPermissionService
            
            # Verificar permisos
            permission_check = TradingPermissionService.check_permission(
                admin_user=request.user,
                target_user=target_user,
                action_type=self.permission_action_type,
                fund_id=fund_id,
                amount=amount
            )
            
            print(f"📊 Resultado de check_permission: {permission_check}")
            
            if not permission_check['allowed']:
                print(f"❌ Permiso DENEGADO: {permission_check['reason']}")
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(permission_check['reason'])
            
            print("✅ Permiso APROBADO")
            request.permission_used = permission_check['permission']
        else:
            print("⏭️ No se requiere validación de permisos")
    
    def get_target_user(self, request):
        """Extrae el usuario objetivo"""
        if hasattr(request, 'data'):
            if 'supplier_user' in request.data:
                from apps.user.models import User
                return User.objects.get(id=request.data['supplier_user'])
            elif 'seller_user' in request.data:
                from apps.user.models import User  
                return User.objects.get(id=request.data['seller_user'])
        return request.user
    
    def get_amount(self, request):
        """Extrae el monto calculado correctamente"""
        if hasattr(request, 'data'):
            # Si existe total_amount, usarlo
            if 'total_amount' in request.data:
                from decimal import Decimal
                return Decimal(str(request.data['total_amount']))
            
            # ✅ CALCULAR: units * price_per_unit
            elif 'units' in request.data and 'price_per_unit' in request.data:
                from decimal import Decimal
                units = Decimal(str(request.data['units']))
                price = Decimal(str(request.data['price_per_unit']))
                total = units * price
                print(f"🧮 Calculated amount: {units} × {price} = {total}")
                return total
        
        return None
    
    def get_fund_id(self, request):
        """Extrae el fund_id"""
        if hasattr(request, 'data') and 'fund' in request.data:
            return request.data['fund']
        return None