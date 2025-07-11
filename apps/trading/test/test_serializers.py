import uuid
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError
from apps.trading.models import PurchaseOrder, SalesOrder, Transaction, OrderBook
from apps.fund.models import Fund
from apps.user.models import User

from apps.trading.serializers.core_serializer import (
    PurchaseOrderSerializer,
    SalesOrderSerializer,
    TransactionSerializer,
    OrderBookSerializer
)


class BaseOrderSerializerTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword',
            username='testuser'
        )
        
        # Create test fund
        self.fund = Fund.objects.create(
            name='Test Fund',
            price_per_unit=100.0,
        )
        
        # Request context
        self.context = {'request': type('obj', (object,), {'user': self.user})}
        
        # Base order data
        self.valid_order_data = {
            'units': 10,
            'price_per_unit': 110.0,
            'expiration_date': timezone.now() + timedelta(days=30),
            'fund': self.fund.id,
            'margin': 5.0,
            'status': 'PENDING',
        }


class PurchaseOrderSerializerTestCase(BaseOrderSerializerTestCase):
    def test_serialize_purchase_order(self):
        """Test serializing an existing purchase order"""
        purchase_order = PurchaseOrder.objects.create(
            units=10,
            price_per_unit=110.0,
            total_amount=1100.0,
            expiration_date=timezone.now() + timedelta(days=30),
            fund=self.fund,
            margin=5.0,
            status='PENDING',
            created_by=self.user,
            order_number='PO-12345678'
        )
        
        serializer = PurchaseOrderSerializer(purchase_order)
        data = serializer.data
        
        self.assertEqual(data['order_number'], 'PO-12345678')
        self.assertEqual(data['fund_name'], 'Test Fund')
        self.assertEqual(data['units'], 10)
        self.assertEqual(data['price_per_unit'], 110.0)
        self.assertEqual(data['total_amount'], 1100.0)
        
    def test_create_purchase_order(self):
        """Test creating a purchase order from serialized data"""
        serializer = PurchaseOrderSerializer(
            data=self.valid_order_data, 
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        purchase_order = serializer.save()
        
        self.assertIsNotNone(purchase_order.id)
        self.assertTrue(purchase_order.order_number.startswith('PO-'))
        self.assertEqual(purchase_order.total_amount, 1100.0)
        self.assertEqual(purchase_order.created_by, self.user)
        
    def test_validate_price_per_unit(self):
        """Test that price_per_unit must be >= fund's price_per_unit"""
        invalid_data = self.valid_order_data.copy()
        invalid_data['price_per_unit'] = 90.0  # Less than fund's price
        
        serializer = PurchaseOrderSerializer(
            data=invalid_data, 
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('Price per unit must be greater than or equal', 
                    str(serializer.errors))


class SalesOrderSerializerTestCase(BaseOrderSerializerTestCase):
    def test_serialize_sales_order(self):
        """Test serializing an existing sales order"""
        sales_order = SalesOrder.objects.create(
            units=10,
            price_per_unit=110.0,
            total_amount=1100.0,
            expiration_date=timezone.now() + timedelta(days=30),
            fund=self.fund,
            margin=5.0,
            status='PENDING',
            created_by=self.user,
            order_number='SO-12345678'
        )
        
        serializer = SalesOrderSerializer(sales_order)
        data = serializer.data
        
        self.assertEqual(data['order_number'], 'SO-12345678')
        self.assertEqual(data['units'], 10)
        self.assertEqual(data['total_amount'], 1100.0)
        
    def test_create_sales_order(self):
        """Test creating a sales order from serialized data"""
        serializer = SalesOrderSerializer(
            data=self.valid_order_data, 
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        sales_order = serializer.save()
        
        self.assertIsNotNone(sales_order.id)
        self.assertTrue(sales_order.order_number.startswith('SO-'))
        self.assertEqual(sales_order.total_amount, 1100.0)


class TransactionSerializerTestCase(BaseOrderSerializerTestCase):
    def setUp(self):
        super().setUp()
        
        # Create purchase and sales orders for transactions
        self.purchase_order = PurchaseOrder.objects.create(
            units=10,
            price_per_unit=110.0,
            total_amount=1100.0,
            expiration_date=timezone.now() + timedelta(days=30),
            fund=self.fund,
            margin=5.0,
            status='PENDING',
            created_by=self.user,
            order_number='PO-12345678'
        )
        
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='sellerpass',
            username='selleruser'
        )
        
        self.sales_order = SalesOrder.objects.create(
            units=10,
            price_per_unit=110.0,
            total_amount=1100.0,
            expiration_date=timezone.now() + timedelta(days=30),
            fund=self.fund,
            margin=5.0,
            status='PENDING',
            created_by=self.seller,
            order_number='SO-12345678'
        )
        
    def test_create_transaction(self):
        """Test creating a transaction with purchase and sales orders"""
        transaction_data = {
            'purchase_order': self.purchase_order.id,
            'sales_order': self.sales_order.id,
            'buyer': self.user.id,
            'seller': self.seller.id,
            'fund': self.fund.id,
            'units': 10,
            'price_per_unit': 110.0,
            'total_amount': 1100.0
        }
        
        serializer = TransactionSerializer(data=transaction_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        with patch('apps.trading.models.PurchaseOrder.update_status') as mock_po_update, \
             patch('apps.trading.models.SalesOrder.update_status') as mock_so_update:
            transaction = serializer.save()
            
            # Check that update_status was called for both orders
            mock_po_update.assert_called_once_with('COMPLETED')
            mock_so_update.assert_called_once_with('COMPLETED')
        
        self.assertEqual(transaction.units, 10)
        self.assertEqual(transaction.total_amount, 1100.0)
        self.assertEqual(transaction.buyer, self.user)
        self.assertEqual(transaction.seller, self.seller)


class OrderBookSerializerTestCase(BaseOrderSerializerTestCase):
    def setUp(self):
        super().setUp()
        
        # Create order book
        self.order_book = OrderBook.objects.create(
            fund=self.fund,
            last_price=105.0,
            daily_high=110.0,
            daily_low=100.0,
            daily_volume=1000
        )
        
        # Create some purchase and sales orders
        self.po1 = PurchaseOrder.objects.create(
            units=10,
            price_per_unit=105.0,
            total_amount=1050.0,
            fund=self.fund,
            status='PENDING',
            created_by=self.user,
            order_number='PO-11111111'
        )
        
        self.po2 = PurchaseOrder.objects.create(
            units=5,
            price_per_unit=104.0,
            total_amount=520.0,
            fund=self.fund,
            status='PENDING',
            created_by=self.user,
            order_number='PO-22222222'
        )
        
        self.so1 = SalesOrder.objects.create(
            units=8,
            price_per_unit=106.0,
            total_amount=848.0,
            fund=self.fund,
            status='PENDING',
            created_by=self.user,
            order_number='SO-11111111'
        )
        
        self.so2 = SalesOrder.objects.create(
            units=12,
            price_per_unit=107.0,
            total_amount=1284.0,
            fund=self.fund,
            status='PENDING',
            created_by=self.user,
            order_number='SO-22222222'
        )
        
    def test_order_book_representation(self):
        """Test that order book includes buy and sell orders in proper order"""
        serializer = OrderBookSerializer(self.order_book)
        data = serializer.data
        
        self.assertEqual(data['fund_name'], 'Test Fund')
        self.assertEqual(data['last_price'], 105.0)
        self.assertEqual(data['daily_high'], 110.0)
        self.assertEqual(data['daily_low'], 100.0)
        self.assertEqual(data['daily_volume'], 1000)
        
        # Check that buy orders are ordered by price descending
        buy_orders = data['buy_orders']
        self.assertEqual(len(buy_orders), 2)
        self.assertEqual(buy_orders[0]['price_per_unit'], 105.0)
        self.assertEqual(buy_orders[1]['price_per_unit'], 104.0)
        
        # Check that sell orders are ordered by price ascending
        sell_orders = data['sell_orders']
        self.assertEqual(len(sell_orders), 2)
        self.assertEqual(sell_orders[0]['price_per_unit'], 106.0)
        self.assertEqual(sell_orders[1]['price_per_unit'], 107.0)