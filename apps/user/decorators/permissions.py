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
    """
    Mixin para vistas que requieren permisos de trading
    Uso: class MyView(TradingPermissionMixin, CreateAPIView):
            permission_action_type = 'CREATE_SALES_ORDER'
    """
    permission_action_type = None
    
    def dispatch(self, request, *args, **kwargs):
        """Intercepta la request para validar permisos antes de procesarla"""
        
        if self.permission_action_type and not isinstance(request.user, AnonymousUser):
            # Extraer datos para validación
            target_user = self.get_target_user(request)
            amount = self.get_amount(request)
            fund_id = self.get_fund_id(request)
            
            # Verificar permisos
            permission_check = TradingPermissionService.check_permission(
                admin_user=request.user,
                target_user=target_user,
                action_type=self.permission_action_type,
                fund_id=fund_id,
                amount=amount
            )
            
            if not permission_check['allowed']:
                return Response({
                    'error': permission_check['reason'],
                    'requires_permission': True,
                    'action_type': self.permission_action_type
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Guardar permiso en request
            request.permission_used = permission_check['permission']
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_target_user(self, request):
        """Override en subclases para extraer usuario objetivo"""
        return getattr(request, 'target_user', request.user)
    
    def get_amount(self, request):
        """Override en subclases para extraer monto"""
        if hasattr(request, 'data') and 'total_amount' in request.data:
            return Decimal(str(request.data['total_amount']))
        return None
    
    def get_fund_id(self, request):
        """Override en subclases para extraer fund_id"""
        if hasattr(request, 'data') and 'fund' in request.data:
            return request.data['fund']
        return None
    
    def perform_create(self, serializer):
        """Hook para log después de crear exitosamente"""
        result = super().perform_create(serializer)
        
        # Log uso exitoso del permiso
        if hasattr(self.request, 'permission_used'):
            TradingPermissionService.log_permission_usage(
                permission=self.request.permission_used,
                action_type=self.permission_action_type,
                action_data={
                    'created_object_id': str(serializer.instance.id),
                    'amount': self.get_amount(self.request),
                    'fund_id': self.get_fund_id(self.request),
                },
                success=True
            )
        
        return result
