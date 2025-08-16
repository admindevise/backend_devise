"""
Ejemplo de uso del nuevo sistema de permisos con decorators
"""
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.user.services.permission_service import TradingPermissionService
from apps.fund.models import Fund

User = get_user_model()

class TestNewPermissionSystem(APITestCase):
    
    def setUp(self):
        # Crear usuarios
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            is_staff=True
        )
        self.client_user = User.objects.create_user(
            email='client@test.com', 
            password='test123'
        )
        
        # Crear fund de prueba
        self.fund = Fund.objects.create(
            name='Test Fund',
            active=True
        )
    
    def test_permission_decorator_success(self):
        """Test que el decorator permite acceso con permisos válidos"""
        
        # 1. Otorgar permiso al admin
        permission = TradingPermissionService.grant_trading_permission(
            user=self.client_user,
            admin_user=self.admin,
            permission_type='SALES_ORDERS',
            duration_hours=24,
            max_order_amount=Decimal('100000'),
            reason="Test permission"
        )
        
        # 2. Login como admin
        self.client.force_authenticate(user=self.admin)
        
        # 3. Crear orden para el cliente
        data = {
            'seller_user': self.client_user.id,
            'fund': self.fund.id,
            'units': 5,
            'price_per_unit': '1000.00',
            'margin': '2.5',
            'expiration_date': '2025-12-31'
        }
        
        # 4. El decorator automáticamente valida permisos
        response = self.client.post('/api/sales-orders/', data)
        
        # 5. Verificar éxito
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_number', response.data)
        
        # 6. Verificar que se registró el uso del permiso
        permission.refresh_from_db()
        self.assertEqual(permission.usage_count, 1)
    
    def test_permission_decorator_denied(self):
        """Test que el decorator bloquea acceso sin permisos"""
        
        # 1. Login como admin (sin permisos)
        self.client.force_authenticate(user=self.admin)
        
        # 2. Intentar crear orden sin permisos
        data = {
            'seller_user': self.client_user.id,
            'fund': self.fund.id,
            'units': 5,
            'price_per_unit': '1000.00',
            'margin': '2.5',
            'expiration_date': '2025-12-31'
        }
        
        # 3. El decorator automáticamente rechaza
        response = self.client.post('/api/sales-orders/', data)
        
        # 4. Verificar rechazo
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('requires_permission', response.data)
        self.assertEqual(response.data['action_type'], 'CREATE_SALES_ORDER')
    
    def test_normal_user_self_order(self):
        """Test que usuarios normales pueden crear órdenes para sí mismos"""
        
        # 1. Login como cliente
        self.client.force_authenticate(user=self.client_user)
        
        # 2. Crear orden para sí mismo (seller_user = usuario logueado)
        data = {
            'fund': self.fund.id,
            'units': 3,
            'price_per_unit': '800.00',
            'margin': '1.5',
            'expiration_date': '2025-12-31'
            # Sin seller_user → se asigna automáticamente
        }
        
        # 3. No requiere permisos especiales
        response = self.client.post('/api/sales-orders/', data)
        
        # 4. Verificar éxito
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['seller_user'], self.client_user.id)


class TestPermissionService(APITestCase):
    """Tests para el servicio simplificado de permisos"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            is_staff=True
        )
        self.client_user = User.objects.create_user(
            email='client@test.com'
        )
    
    def test_grant_permission(self):
        """Test crear permiso"""
        permission = TradingPermissionService.grant_trading_permission(
            user=self.client_user,
            admin_user=self.admin,
            permission_type='SALES_ORDERS',
            duration_hours=48,
            max_order_amount=Decimal('50000'),
            reason="Test creation"
        )
        
        self.assertIsNotNone(permission.id)
        self.assertEqual(permission.user, self.client_user)
        self.assertEqual(permission.admin_user, self.admin)
        self.assertEqual(permission.permission_type, 'SALES_ORDERS')
        self.assertEqual(permission.max_order_amount, Decimal('50000'))
    
    def test_check_permission_valid(self):
        """Test validación de permisos exitosa"""
        # Crear permiso
        TradingPermissionService.grant_trading_permission(
            user=self.client_user,
            admin_user=self.admin,
            permission_type='SALES_ORDERS',
            max_order_amount=Decimal('10000')
        )
        
        # Verificar permiso
        result = TradingPermissionService.check_permission(
            admin_user=self.admin,
            target_user=self.client_user,
            action_type='CREATE_SALES_ORDER',
            amount=Decimal('5000')
        )
        
        self.assertTrue(result['allowed'])
        self.assertIsNotNone(result['permission'])
    
    def test_check_permission_amount_exceeded(self):
        """Test validación con monto excedido"""
        # Crear permiso con límite bajo
        TradingPermissionService.grant_trading_permission(
            user=self.client_user,
            admin_user=self.admin,
            permission_type='SALES_ORDERS',
            max_order_amount=Decimal('1000')
        )
        
        # Verificar con monto mayor al límite
        result = TradingPermissionService.check_permission(
            admin_user=self.admin,
            target_user=self.client_user,
            action_type='CREATE_SALES_ORDER',
            amount=Decimal('5000')
        )
        
        self.assertFalse(result['allowed'])
        self.assertIn('excede el límite', result['reason'])
