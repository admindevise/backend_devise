from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.fund.models import Fund, FundToken

from apps.audit.audit_service import AuditService
from apps.kaleido.utils import mint_721_token, get_owner_of, burn_721_token

from django.db import transaction
from datetime import datetime

class TokenMintSerializer(serializers.Serializer):
    fund_id = serializers.IntegerField(required=True, help_text="ID del fondo para el cual crear un token")

    def validate_fund_id(self, value):
        """Valida que el fondo exista"""
        try:
            fund = Fund.objects.get(id=value)
            return value
        except Fund.DoesNotExist:
            raise serializers.ValidationError("No existe un fondo con este ID")

    def create(self, validated_data):
        """
        Ejecuta el proceso de mint de un solo token con ID generado como datetime + fund_id + counter.
        """
        fund_id = validated_data.get('fund_id')
        fund = Fund.objects.get(id=fund_id)
        
        # Datos para auditoria
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        initial_audit = None
        if request:
            initial_audit = AuditService.log_action(
                request=request,
                action_code='TOKEN_CREATE',
                obj=fund,
                details={
                    'fund_id': fund.id,
                    'operation': 'mint_token'
                },
                status='PENDING'
            )
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_mint': 1,
            'minted': 0,
            'failures': 0,
            'details': []
        }
        
        # Verificar si el fondo tiene un contrato de token
        if not fund.contract_address:
            if initial_audit:
                self._update_audit(initial_audit, 'ERROR', {'error': "El fondo no tiene un contrato de token asociado."})
            raise ValidationError("El fondo no tiene un contrato de token asociado.")        
    
        # Usar transacción atómica para todo el proceso
        with transaction.atomic():
            # Usar select_for_update para bloquear la fila durante la transacción
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:       
                token_id, next_token_count = self._generate_token_id(fund, initial_audit)
                
                # Ejecutar mint
                result_data, error = mint_721_token(token_id, fund.id, fund.contract_address)
                
                if error:
                    self._handle_mint_error(results, initial_audit, token_id, error)
                else:
                    self._handle_mint_success(results, initial_audit, fund, next_token_count, token_id, result_data, user)
                    
            except Exception as e:
                self._handle_exception(results, initial_audit, token_id, e)
            
            return results
        
    def _generate_token_id(self, fund, initial_audit):
        """ Manejar la creación de token_id """
        now = datetime.now()
        next_token_count = fund.amount_tokens + 1
        
        date_part = int(now.strftime('%Y%m%d%H%M'))
        fund_id_part = int(fund.id) % 1000  # Limitar a 4 dígitos
        
        # Combinar: YYYYMMDDHHMMSS + XXXXX + XXXX (fecha + id_fondo + contador)
        token_id = (date_part * 1000000) + (fund_id_part * 1000) + next_token_count
        
        if initial_audit:
            self._update_audit(initial_audit, 'PENDING', {'token_id': token_id})
        
        return token_id, next_token_count
    
    def _handle_mint_error(self, results, initial_audit, token_id, error):
        """
        Maneja los errores durante el proceso de mint.
        """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if initial_audit:
            self._update_audit(initial_audit, 'ERROR', {'error': str(error)})

    def _handle_mint_success(self, results, initial_audit, fund, next_token_count, token_id, result_data, user):
        """ Maneja el éxito durante el proceso de mint. """
        fund.amount_tokens = next_token_count
        fund.save(update_fields=['amount_tokens'])
        
        FundToken.objects.create(
            fund=fund,
            token_id=token_id,
            created_by=user
            )
        
        results['minted'] += 1
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id'),
            'new_token_count': fund.amount_tokens
        })
        
        if initial_audit:
            audit_details = {
                'transaction_id': result_data.get('id'),
                'new_token_count': fund.amount_tokens
                }
            self._update_audit(initial_audit, 'SUCCESS', audit_details, transaction_id=result_data.get('id') if 'id' in result_data else None)
    
    def _handle_exception(self, results, initial_audit, token_id, exception):
        """ Maneja las excepciones durante el proceso de mint. """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id if 'token_id' in locals() else None,
            'success': False,
            'error': str(exception)
        })
        
        if initial_audit:
            self._update_audit(initial_audit, 'ERROR', {'error': str(exception)})
    
    def _update_audit(self, audit, status, details, transaction_id=None):
        """Actualiza un registro de auditoría con los valores proporcionados"""
        audit.status = status
        audit.details.update(details)
        
        if transaction_id:
            audit.transaction_id = transaction_id
        
        # Especificar los campos a actualizar
        update_fields = ['status', 'details']
        if transaction_id:
            update_fields.append('transaction_id')
            
        audit.save(update_fields=update_fields)
     
     
class TokenBurnSerializer(serializers.Serializer):
    fund_id = serializers.IntegerField(required=True, help_text="ID del fondo para el cual quemar un token")
    token_id = serializers.IntegerField(required=True, help_text="ID del token a quemar")

    def validate_fund_id(self, value):
        """Valida que el fondo exista"""
        try:
            fund = Fund.objects.get(id=value)
            return value
        except Fund.DoesNotExist:
            raise serializers.ValidationError("No existe un fondo con este ID")

    def create(self, validated_data):
        """Quemar tokens con el metodo burn_721_token"""
        fund_id = validated_data['fund_id']
        token_id = validated_data['token_id']
        
        fund = Fund.objects.get(id=fund_id)
        
        # Datos para auditoria
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        init_audit = None
        if request:
            init_audit = AuditService.log_action(
                request=request,
                action_code='TOKEN_BURN',
                obj=fund,
                details={
                    'fund_id': fund.id,
                    'operation': 'burn_token'
                },
                status='PENDING'
            )
        
        results = {
            'success': True,
            'total_to_burn': 1,
            'burned': 0,
            'failures': 0,
            'details': []
        }
        
        if not fund.contract_address:
            if init_audit:
                self._update_audit(init_audit, 'ERROR', {'error': "El fondo no tiene una dirección de contrato"})
            raise serializers.ValidationError("El fondo no tiene una dirección de contrato")        
    
        with transaction.atomic():
            # Usar select_for_update para bloquear la fila durante la transacción
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                # Ejecutar burn
                result_data, error = burn_721_token(token_id, fund.id, fund.contract_address)
                
                if error:
                    self._handle_burn_error(results, init_audit, token_id, error)
                else:
                    self._handle_burn_success(results, init_audit, fund, token_id, result_data, user)
                    
            except Exception as e:
                self._handle_exception(results, init_audit, token_id, e)
            
            return results
    
    def _handle_burn_error(self, results, init_audit, token_id, error):
        """
        Maneja los errores durante el proceso de burn.
        """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if init_audit:
            self._update_audit(init_audit, 'ERROR', {'error': str(error)})
    
    def _handle_burn_success(self, results, init_audit, fund, token_id, result_data, user):
        """ Maneja el éxito durante el proceso de burn. """
        fund.save(update_fields=['amount_tokens'])
        
        FundToken.objects.filter(fund=fund, token_id=token_id).delete()
        
        results['burned'] += 1
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id')
        })
        
        if init_audit:
            audit_details = {
                'transaction_id': result_data.get('id')
                }
            self._update_audit(init_audit, 'SUCCESS', audit_details, transaction_id=result_data.get('id') if 'id' in result_data else None)
            
    def _handle_exception(self, results, init_audit, token_id, exception):
        """ Maneja las excepciones durante el proceso de burn. """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id if 'token_id' in locals() else None,
            'success': False,
            'error': str(exception)
        })
        
        if init_audit:
            self._update_audit(init_audit, 'ERROR', {'error': str(exception)})
        
    def _update_audit(self, audit, status, details, transaction_id=None):
        """Actualiza un registro de auditoría con los valores proporcionados"""
        audit.status = status
        audit.details.update(details)
        
        if transaction_id:
            audit.transaction_id = transaction_id
        
        # Especificar los campos a actualizar
        update_fields = ['status', 'details']
        if transaction_id:
            update_fields.append('transaction_id')
            
        audit.save(update_fields=update_fields)
    
    