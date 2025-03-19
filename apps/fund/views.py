from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user

import time

from django.utils import timezone
from datetime import timedelta

from apps.audit.audit_service import AuditService
from apps.fund.models import Fund, FundPrice, FundInvestment, TransferReceipt
from apps.kaleido.models import Wallet
from apps.fund.serializers import FundPriceSerializer, FundSerializer, FundInvestmentSerializer, TransferReceiptSerializer

import requests
from requests.auth import HTTPBasicAuth
import json
from rest_framework.views import APIView
from rest_framework import status

""" Funds """    
class FundPriceViewSet(viewsets.ViewSet):
    def list(self, request, fund_id, interval):
        now = timezone.now()
        if interval == 'hourly':
            start_time = now - timedelta(hours=1)
        elif interval == 'weekly':
            start_time = now - timedelta(weeks=1)
        elif interval == 'monthly':
            start_time = now - timedelta(days=30)
        elif interval == 'quarterly':
            start_time = now - timedelta(days=90)
        elif interval == 'semiannually':
            start_time = now - timedelta(days=180)
        elif interval == 'annually':
            start_time = now - timedelta(days=365)
        elif interval == '5years':
            start_time = now - timedelta(days=5*365)
        elif interval == '10years':
            start_time = now - timedelta(days=10*365)
        else:
            return Response({'error': 'Invalid interval'}, status=400)

        prices = FundPrice.objects.filter(fund_id=fund_id, timestamp__gte=start_time).order_by('timestamp')
        serializer = FundPriceSerializer(prices, many=True)
        return Response(serializer.data)

class FundViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Fund to be viewed or edited.
    
    Este ViewSet proporciona automáticamente acciones `list`, `create`, `retrieve`,
    `update` y `destroy`.
    
    Cada operación genera registros de auditoría para seguimiento completo.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundSerializer
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        """
        Filtra los fondos para mostrar solo los del usuario autenticado,
        a menos que el usuario sea admin (en cuyo caso muestra todos).
        """
        user = self.request.user
        if user.is_staff:
            return Fund.objects.all()
        return Fund.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Asigna el usuario autenticado al fondo y crea registro de auditoría.
        """
        user = self.request.user
        
        # Registrar inicio de creación
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_CREATE",
            obj=user,  # Usamos el usuario como referencia hasta crear el fondo
            details={
                'name': serializer.validated_data.get('name'),
                'amount': serializer.validated_data.get('amount'),
                'operation': 'create_fund'
            },
            status='PENDING'
        )
        
        try:
            # Crear el fondo
            fund = serializer.save(user=user)
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.save(update_fields=['status'])
                
                # Actualizar también el objeto de referencia para que quede asociado al fondo
                if hasattr(initial_audit, 'content_type'):
                    fund_content_type = ContentType.objects.get_for_model(Fund)
                    initial_audit.content_type = fund_content_type
                    initial_audit.object_id = fund.id
                    initial_audit.save(update_fields=['content_type', 'object_id'])
            
            return fund
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje

    def perform_update(self, serializer):
        """
        Actualiza un fondo y crea registro de auditoría.
        """
        # Obtener el fondo antes de la actualización
        fund = self.get_object()
        old_data = {
            'name': fund.name,
            'description': fund.description,
            'amount': str(fund.amount)
        }
        
        # Registrar inicio de actualización
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_UPDATE",
            obj=fund,
            details={
                'old_data': old_data,
                'operation': 'update_fund'
            },
            status='PENDING'
        )
        
        try:
            # Actualizar el fondo
            updated_fund = serializer.save()
            
            # Datos después de la actualización
            new_data = {
                'name': updated_fund.name,
                'description': updated_fund.description,
                'amount': str(updated_fund.amount)
            }
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({'new_data': new_data})
                initial_audit.save(update_fields=['status', 'details'])
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje
            
    def perform_destroy(self, instance):
        """
        Elimina un fondo y crea registro de auditoría.
        """
        # Registrar inicio de eliminación
        fund_data = {
            'id': instance.id,
            'name': instance.name,
            'description': instance.description,
            'amount': str(instance.amount)
        }
        
        # Para eliminar, creamos un único registro directamente como SUCCESS
        # ya que no hay un estado intermedio significativo
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="FUND_DELETE",
            obj=self.request.user,  # Referencia al usuario ya que el fondo será eliminado
            details={
                'fund_data': fund_data,
                'operation': 'delete_fund'
            },
            status='PENDING'
        )
        
        try:
            # Eliminar el fondo
            result = super().perform_destroy(instance)
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.save(update_fields=['status'])
                
            return result
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje
        
class FundInvestmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar inversiones en fondos.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FundInvestmentSerializer

    def get_queryset(self):
        return FundInvestment.objects.filter(investor=self.request.user)

    def perform_create(self, serializer):
        """
        Crea una nueva inversión y registra la operación en la auditoría.
        """
        user = self.request.user
        fund = serializer.validated_data.get('fund')
        amount = serializer.validated_data.get('invested_amount')
        
        # Auditar inicio del proceso de inversión
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="INVESTMENT_CREATE",
            obj=fund,  # Usamos el fondo como referencia inicial
            details={
                'fund_id': fund.id,
                'fund_name': fund.name,
                'amount': str(amount),
                'investor': user.username,
                'operation': 'create_investment'
            },
            status='PENDING'
        )
        
        try:
            # Crear la inversión
            investment = serializer.save(investor=user)
            
            # En lugar de actualizar el registro inicial, crear uno nuevo con el objeto correcto
            AuditService.log_action(
                request=self.request,
                action_code="INVESTMENT_CREATE",
                obj=investment,  # Usar directamente el objeto investment
                details={
                    'fund_id': fund.id,
                    'fund_name': fund.name,
                    'amount': str(amount),
                    'investor': user.username,
                    'operation': 'create_investment'
                },
                status='SUCCESS'
            )
            
            # Eliminar el registro inicial para evitar duplicados
            if initial_audit:
                initial_audit.delete()
            
            return investment
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise  # Re-lanzar la excepción para que DRF la maneje

    def perform_update(self, serializer):
        """
        Actualiza una inversión existente y registra la operación en la auditoría.
        """
        # Obtener la inversión antes de la actualización
        investment = self.get_object()
        old_data = {
            'fund_id': investment.fund.id,
            'fund_name': investment.fund.name,
            'invested_amount': str(investment.invested_amount)
        }
        
        # Auditar inicio de actualización
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="INVESTMENT_UPDATE",
            obj=investment,
            details={
                'old_data': old_data,
                'investor': investment.investor.username,
                'operation': 'update_investment'
            },
            status='PENDING'
        )
        
        try:
            # Actualizar la inversión
            updated_investment = serializer.save()
            
            # Datos después de la actualización
            new_data = {
                'fund_id': updated_investment.fund.id,
                'fund_name': updated_investment.fund.name,
                'invested_amount': str(updated_investment.invested_amount)
            }
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.details.update({'new_data': new_data})
                initial_audit.save(update_fields=['status', 'details'])
            
            return updated_investment
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise

    def perform_destroy(self, instance):
        """
        Elimina una inversión y registra la operación en la auditoría.
        """
        investment_data = {
            'id': instance.id,
            'fund_id': instance.fund.id,
            'fund_name': instance.fund.name,
            'investor': instance.investor.username,
            'invested_amount': str(instance.invested_amount),
            'joined_at': instance.joined_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Auditar inicio de eliminación
        initial_audit = AuditService.log_action(
            request=self.request,
            action_code="INVESTMENT_DELETE",
            obj=instance,
            details={
                'investment_data': investment_data,
                'operation': 'delete_investment'
            },
            status='PENDING'
        )
        
        try:
            # Eliminar la inversión
            result = super().perform_destroy(instance)
            
            # Actualizar estado de auditoría a SUCCESS
            if initial_audit:
                initial_audit.status = 'SUCCESS'
                initial_audit.save(update_fields=['status'])
            
            return result
            
        except Exception as e:
            # Actualizar estado de auditoría a ERROR
            if initial_audit:
                initial_audit.status = 'ERROR'
                initial_audit.details.update({'error': str(e)})
                initial_audit.save(update_fields=['status', 'details'])
            
            raise

class TransferReceiptViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows TransferReceipt to be viewed or edited.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransferReceiptSerializer

    def get_queryset(self):
        # Listamos los recibos de transferencia del usuario autenticado
        return TransferReceipt.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Asigna el usuario autenticado al recibo de transferencia
        serializer.save(user=self.request.user)